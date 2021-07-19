import itertools
import logging
import typing

from semantics.graph_layer import elements
from semantics.kb_layer import schema, evidence
from semantics.kb_layer import schema_registry

from semantics.kb_layer.orm._pattern_schema import Pattern, MatchMapping, \
    PATTERN_RELATED_LABEL_NAMES


if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


@schema_registry.register
class PatternMatch(schema.Schema):
    """A pattern match is a mapping from a pattern structure to a subgraph of the knowledge
    graph. The specific point in the subgraph at which the pattern matched is referred to as
    its image."""

    preimage = schema.attribute('PREIMAGE', Pattern)
    image = schema.attribute('IMAGE')

    selectors: 'schema_attributes.PluralAttribute[PatternMatch]'
    children: 'schema_attributes.PluralAttribute[PatternMatch]'

    @classmethod
    def _from_mapping(cls, root_pattern: 'Pattern', mapping: MatchMapping, context: MatchMapping,
                      result_mapping: typing.Dict['Pattern', typing.Tuple['PatternMatch', float]],
                      match_role: elements.Role) -> typing.Tuple['PatternMatch', float]:
        if root_pattern in result_mapping:
            return result_mapping[root_pattern]
        # Evidence is propagated upward through the pattern. The evidence means for parents is
        # combined multiplicatively with those of children, since the root pattern's applicability
        # to the image is equivalent to the logical AND of all of its components. Thanks to this, we
        # can check the match's evidence, even for a partial match, and reject a statement or ask
        # for clarification if the match's evidence leans negative.
        root_match_vertex = root_pattern.database.add_vertex(match_role)
        root_match = cls(root_match_vertex, root_pattern.database)
        root_match.preimage.set(root_pattern)
        combined_score = 1
        for selector_pattern in root_pattern.selectors:
            selector_match, selector_score = cls._from_mapping(selector_pattern, mapping, context,
                                                               result_mapping, match_role)
            root_match.selectors.add(selector_match)
            combined_score *= selector_score
        for child_pattern in root_pattern.children:
            child_match, child_score = cls._from_mapping(child_pattern, mapping, context,
                                                         result_mapping, match_role)
            root_match.children.add(child_match)
            combined_score *= child_score
        if root_pattern in mapping:
            # For partial matches, the pattern may not be mapped. In this case, we should simply
            # leave the image undefined in the match.
            image, root_score = mapping[root_pattern]
            if image is not None:
                combined_score *= root_score
                root_match.image.set(image)
                evidence.apply_evidence(root_match.vertex, combined_score)
                if root_pattern in context or root_pattern.template.get(validate=False) in context:
                    # This tells apply() not to override the image if it appears to be overly
                    # specific.
                    root_match.vertex.set_data_key('from_context', True)
        result_mapping[root_pattern] = root_match, combined_score
        return root_match, combined_score

    @classmethod
    def from_mapping(cls, root_pattern: 'Pattern', mapping: MatchMapping,
                     context: MatchMapping = None) -> 'PatternMatch':
        match_role = root_pattern.database.get_role(cls.role_name(), add=True)
        return cls._from_mapping(root_pattern, mapping, context, {}, match_role)[0]

    def _fill_mapping(self, mapping: MatchMapping) -> None:
        preimage = self.preimage.get(validate=False)
        if preimage is None or preimage in mapping:
            return
        mapping[preimage] = (self.image.get(validate=False),
                             evidence.get_evidence_mean(self.vertex))
        for child in self.children:
            child._fill_mapping(mapping)
        for selector in self.selectors:
            selector._fill_mapping(mapping)

    def get_mapping(self) -> MatchMapping:
        mapping = {}
        self._fill_mapping(mapping)
        return mapping

    def is_isomorphic(self) -> bool:
        """Whether the image is isomorphic to the pattern for this match."""
        preimage: Pattern = self.preimage.get(validate=False)
        assert preimage is not None
        representative_vertex = preimage.match.vertex

        # Make sure the preimage even has an image.
        image: 'schema.Schema' = self.image.get(validate=False)
        if image is None:
            return False

        # Check image role.
        if image.vertex.preferred_role != preimage.match.vertex.preferred_role:
            return False

        # Check children.
        if not all(child.is_isomorphic() for child in self.children):
            return False

        # Check selectors.
        if not all(selector.is_isomorphic() for selector in self.selectors):
            return False

        # Check the edges.
        for edge in itertools.chain(representative_vertex.iter_outbound(),
                                    representative_vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES:
                continue
            outbound = edge.source == representative_vertex
            other_vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            # other_pattern = other_value.pattern.get(validate=False)
            if not other_value.represented_pattern.defined:
                # The other value is not a pattern's match representative, so any edge between it
                # and the match representative for this pattern should be present between it and
                # the match image.
                edge_image = image.vertex.get_edge(edge.label, other_vertex, outbound=outbound)
                if edge_image is None:
                    return False
            else:
                # The other value is a pattern's match representative. If its pattern appears in the
                # children of this match's preimage pattern, then we should add a corresponding edge
                # between this and the other match's images.
                for child in self.children:
                    child_preimage = child.preimage.get(validate=False)
                    if not (child_preimage and child_preimage.match == other_value):
                        continue
                    child_image: 'schema.Schema' = child.image.get(validate=False)
                    assert child_image is not None
                    direct_edge = image.vertex.get_edge(edge.label, child_image.vertex,
                                                        outbound=outbound)
                    edge_exists = direct_edge or (
                            edge.label.transitive and
                            child_image.vertex in
                            image.vertex.iter_transitive_neighbors(edge.label, outbound=outbound)
                    )
                    if not edge_exists:
                        return False

        # Everything checks out.
        return True

    def apply(self) -> None:
        """Update the graph to make the image isomorphic to the pattern, adding vertices and edges
        as necessary. Then apply positive evidence to the pattern, image, and match."""

        preimage: Pattern = self.preimage.get(validate=False)
        assert preimage is not None
        representative_vertex = preimage.match.vertex

        image = self.image.get(validate=False)
        if image is None:
            # If there is no image, create one.
            image_vertex = self.database.add_vertex(representative_vertex.preferred_role)
            self.image.set(schema.Schema(image_vertex, self.database))
            image = self.image.get(validate=False)
            assert image is not None
            assert image.vertex == image_vertex
            _logger.info("Created image %s for preimage %s while applying %s.",
                         image, preimage, self)
        elif image.vertex.time_stamp and not self.vertex.get_data_key('from_context', False):
            # If there is an image, but it has a time stamp, create a new, generic vertex without
            # the time stamp. Otherwise, we have made an overly specific match, which will result
            # in confabulated memories.
            # TODO: Revisit this. We may need to do the same for other attributes or data keys.
            old_image = image
            image_vertex = self.database.add_vertex(image.vertex.preferred_role)
            for edge in old_image.vertex.iter_inbound():
                image_vertex.add_edge_from(edge.label, edge.source)
            for edge in old_image.vertex.iter_outbound():
                image_vertex.add_edge_to(edge.label, edge.sink)
            self.image.set(schema.Schema(image_vertex, self.database))
            image = self.image.get(validate=False)
            assert image is not None
            assert image != old_image
            assert image.vertex == image_vertex
            _logger.info("Generalizing image %s from original image %s for preimage %s while "
                         "applying %s.", image, old_image, preimage, self)
        for selector in self.selectors:
            assert selector.image.get(validate=False) in (None, image)
            if selector.image.get(validate=False) is None:
                selector.image.set(image)
            assert selector.image.get(validate=False) == image

        # Make sure all selectors and children are applied.
        for selector in self.selectors:
            selector.apply()
        for child in self.children:
            child.apply()

        # Make sure all edges connected to the match representative of the preimage pattern are also
        # present in the image.
        image: 'schema.Schema' = self.image.get(validate=False)
        assert image is not None
        for edge in itertools.chain(representative_vertex.iter_outbound(),
                                    representative_vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES:
                continue
            outbound = edge.source == representative_vertex
            other_vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            # other_preimage = other_value.pattern.get(validate=False)
            if not other_value.represented_pattern.defined:
                # The other value is not a pattern's match representative, so any edge between it
                # and the match representative for this pattern should be present between it and
                # the match image.
                direct_edge = image.vertex.get_edge(edge.label, other_vertex, outbound=outbound)
                edge_exists = direct_edge or (
                    edge.label.transitive and
                    other_vertex in image.vertex.iter_transitive_neighbors(edge.label,
                                                                           outbound=outbound)
                )
                if edge_exists:
                    if direct_edge:
                        _logger.info("Image edge %s already exists for preimage edge %s while "
                                     "applying %s.", direct_edge, edge, self)
                    else:
                        _logger.info("Indirect image edge already exists for preimage edge %s "
                                     "while applying %s.", edge, self)
                else:
                    new_edge = image.vertex.add_edge(edge.label, other_vertex, outbound=outbound)
                    _logger.info("Created edge %s while applying %s.", new_edge, self)
            else:
                # The other value is a pattern's match representative. If its pattern appears in the
                # children of this match's preimage pattern, then we should add a corresponding edge
                # between this and the other match's images.
                for child in self.children:
                    child_preimage = child.preimage.get(validate=False)
                    if not (child_preimage and child_preimage.match == other_value):
                        continue
                    child_image: 'schema.Schema' = child.image.get(validate=False)
                    assert child_image is not None
                    direct_edge = image.vertex.get_edge(edge.label, child_image.vertex,
                                                        outbound=outbound)
                    edge_exists = direct_edge or (
                            edge.label.transitive and
                            child_image.vertex in
                            image.vertex.iter_transitive_neighbors(edge.label,
                                                                   outbound=outbound)
                    )
                    if edge_exists:
                        if direct_edge:
                            _logger.info(
                                "Image edge %s already exists for preimage edge %s while "
                                "applying %s.", direct_edge, edge, self)
                        else:
                            _logger.info(
                                "Indirect image edge already exists for preimage edge %s "
                                "while applying %s.", edge, self)
                    else:
                        new_edge = image.vertex.add_edge(edge.label, child_image.vertex,
                                                         outbound=outbound)
                        _logger.info("Created edge %s while applying %s.", new_edge, self)

        # Make sure each selector is satisfied. During partial matching, selectors of unmatched
        # patterns are never given a chance to match, since their matches are dependent on their
        # parents. So now we have to give them that chance.
        selector_context = self.get_mapping()
        for selector in preimage.selectors:
            selector_context[selector] = (image, evidence.get_evidence_mean(self.vertex))
        for selector in preimage.selectors:
            for partial_match in selector.find_matches(selector_context, partial=True):
                # Take the first one found.
                partial_match.apply()
                selector_context = partial_match.get_mapping()
                break
        for selector in self.selectors:
            selector_image, _score = selector_context[selector.preimage.get(validate=False)]
            assert selector.image.get(validate=False) in (None, selector_image)
            if selector.image.get(validate=False) is None:
                selector.image.set(selector_image)
            assert selector.image.get(validate=False) == selector_image

        self.accept()

    def apply_evidence(self, mean: float, samples: float = 1):
        """Apply positive evidence to the pattern, image, and match, making no changes to image
        structure."""

        preimage: Pattern = self.preimage.get(validate=False)
        assert preimage is not None
        preimage_template = preimage.template.get(validate=False)
        representative_vertex = preimage.match.vertex

        # The match's evidence mean represents its likelihood of being accepted.
        evidence.apply_evidence(self.vertex, mean, samples)

        # The preimage's evidence mean represents the likelihood of matches containing it being
        # accepted.
        evidence.apply_evidence(preimage.vertex, mean, samples)

        # Likewise for the preimage's template, if it exists.
        if preimage_template:
            evidence.apply_evidence(preimage_template.vertex, mean, samples)

        # Make sure all children and selectors are handled.
        for selector in self.selectors:
            selector.apply_evidence(mean, samples)
        for child in self.children:
            child.apply_evidence(mean, samples)

        if not mean:
            # All the evidence updates remaining are for the image, which is updated proportionately
            # to the target mean. If the target mean is zero, nothing past this point will have an
            # effect, so we might as well save ourselves the trouble and return early.
            return

        # If there is no image, there's nothing at this level to apply evidence towards, so return
        # early.
        image: 'schema.Schema' = self.image.get(validate=False)
        if image is None:
            return

        # Apply evidence to the image itself.
        # The image's evidence mean represents its likelihood of being true. We update it towards
        # the preimage representative's truth value, at a rate proportionate to the target evidence
        # mean. We do not update the preimage representative's evidence mean, because it represents
        # a matched truth value and not a likelihood.
        evidence.apply_evidence(image.vertex,
                                evidence.get_evidence_mean(representative_vertex),
                                mean)

        # Apply evidence to the edges.
        for edge in itertools.chain(representative_vertex.iter_outbound(),
                                    representative_vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES:
                continue
            outbound = edge.source == representative_vertex
            other_vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            # other_pattern = other_value.pattern.get(validate=False)
            if not other_value.represented_pattern.defined:
                # The other value is not a pattern's match representative, so any edge between it
                # and the match representative for this pattern should be present between it and
                # the match image.
                edge_image = image.vertex.get_edge(edge.label, other_vertex, outbound=outbound)
                if edge_image is not None:
                    # The image edge's evidence represents its likelihood of being true. We update
                    # it towards the preimage edge's truth value, at a rate proportionate to the
                    # target evidence mean. We do not update the preimage edge's truth value,
                    # because it represents a matched truth value and not a likelihood.
                    evidence.apply_evidence(edge_image, evidence.get_evidence_mean(edge), mean)
            else:
                # The other value is a pattern's match representative. If its pattern appears in the
                # children of this match's preimage pattern, then we should add a corresponding edge
                # between this and the other match's images. We do not update the preimage edge's
                # truth value, because it represents a matched truth value and not a likelihood.
                for child in self.children:
                    child_preimage = child.preimage.get(validate=False)
                    if not (child_preimage and child_preimage.match == other_value):
                        continue
                    child_image: 'schema.Schema' = child.image.get(validate=False)
                    assert child_image is not None
                    edge_image = image.vertex.get_edge(edge.label, child_image.vertex,
                                                       outbound=outbound)
                    if edge_image is not None:
                        # The image edge's evidence represents its likelihood of being true. We
                        # update it towards the preimage edge's truth value, at a rate
                        # proportionate to the target evidence mean.
                        evidence.apply_evidence(edge_image, evidence.get_evidence_mean(edge), mean)

    def accept(self) -> None:
        """Apply positive evidence to the pattern, image, and match, making no changes to image
        structure."""
        self.apply_evidence(1)

    def reject(self) -> None:
        """Apply negative evidence to the pattern and match, making no changes to image
        structure."""
        self.apply_evidence(0)
