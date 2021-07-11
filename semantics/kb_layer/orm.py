"""The Object-Relational Model to map from semantic structures to graph elements."""

import itertools
import typing

from semantics.data_types import typedefs
from semantics.graph_layer import elements
from semantics.kb_layer import schema, evidence
from semantics.kb_layer import schema_registry

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


PATTERN_RELATED_LABEL_NAMES = frozenset([
    'MATCH_REPRESENTATIVE',
    'PREIMAGE',
    'IMAGE',
    'CHILD',
])


@schema_registry.register
class Word(schema.Schema):
    """A word is a sequence of characters, independent of their meaning."""

    @schema.validation('{schema} must have an associated spelling attribute.')
    def has_spelling(self) -> bool:
        """Whether the word has an associated spelling. In order for the word to pass validation,
        this must return True."""
        return self._vertex.name is not None

    @property
    def spelling(self) -> typing.Optional[str]:
        """The spelling, if any, associated with this word."""
        return self._vertex.name

    kind: 'schema_attributes.SingularAttribute[Kind]'
    kinds: 'schema_attributes.PluralAttribute[Kind]'
    selector: 'schema_attributes.SingularAttribute[Pattern]'
    selectors: 'schema_attributes.PluralAttribute[Pattern]'
    divisibility: 'schema_attributes.SingularAttribute[Divisibility]'
    divisibilities: 'schema_attributes.PluralAttribute[Divisibility]'


@schema_registry.register
class Kind(schema.Schema):
    """A kind is an abstract type of thing."""

    @schema.validation('{schema} should have at least one name Word.')
    def has_name(self) -> bool:
        """Whether the kind has an associated name. In order for the kind to pass validation, this
        must return True."""
        return self.name.defined

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    instances: 'schema_attributes.PluralAttribute[Instance]'


@schema_registry.register
class Divisibility(schema.Schema):
    """A divisibility is an attribute determining whether/to what degree an instance or observation
    can be subdivided. These are 'singular' (an indivisible unit), 'plural' (divisible into two or
    more singular components), and 'mass' (a substance, divisible into any number of likewise
    mass-divisible components)."""

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)


@schema_registry.register
class Time(schema.Schema):
    """A time can represent a specific point in type if it has a time stamp, or else an abstract
    point or span of time if it has no time stamp."""

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        """The time stamp, if any, associated with this time."""
        return self._vertex.time_stamp

    later_times: 'schema_attributes.PluralAttribute[Time]'
    earlier_times: 'schema_attributes.PluralAttribute[Time]'
    observations: 'schema_attributes.PluralAttribute[Instance]'


@schema_registry.register
class Instance(schema.Schema):
    """An instance is a particular thing."""

    # Individual instances can be named just like kinds, but usually don't.
    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    kind = schema.attribute('KIND', Kind)
    kinds = schema.attribute('KIND', Kind, plural=True)

    time = schema.attribute('TIME', Time)
    times = schema.attribute('TIME', Time, plural=True)

    divisibility = schema.attribute('DIVISIBILITY', Divisibility)

    instance: 'schema_attributes.SingularAttribute[Instance]'
    instances: 'schema_attributes.PluralAttribute[Instance]'
    observations: 'schema_attributes.PluralAttribute[Instance]'

    actor: 'schema_attributes.SingularAttribute[Instance]'


MatchSchema = typing.TypeVar('MatchSchema', bound=schema.Schema)


@schema_registry.register
class Pattern(schema.Schema, typing.Generic[MatchSchema]):
    """A pattern is a description of the structure of a subgraph of the knowledge graph. Patterns
    correspond to phrases or sentences in natural language. The components of the pattern are
    arranged into a tree or hierarchy which determines the order of search. Matches are built up
    from the leaves to the root of the tree, with each branch representing a sub-clause or
    sub-phrase of the larger pattern."""

    match_representative = schema.attribute('MATCH_REPRESENTATIVE')

    # Some, but not all, patterns are named. Typically named patterns are reusable mixins that
    # are only used in a selector role.
    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    # Selectors are other patterns which match against the *same* vertex in the graph as this
    # pattern does. Think of a selector as roughly equivalent to a mixin class, but for patterns.
    selectors: 'schema_attributes.PluralAttribute[Pattern[MatchSchema]]'

    # Children are other patterns which match against arbitrary other vertices in the graph.
    children: 'schema_attributes.PluralAttribute[Pattern]'

    @property
    def match(self) -> typing.Optional[MatchSchema]:
        """The match representative of the pattern.

        NOTE: The evidence mean for the pattern represents its accuracy, whereas the evidence mean
        for the match representative represents the truth value to be matched in the image vertex.
        """
        return self.match_representative.get(validate=False)

    def find_matches(self, context: typing.Mapping['Pattern', 'schema.Schema'] = None, *,
                     partial: bool = False) -> typing.Iterator['PatternMatch']:
        """Search the graph for matching subgraphs. Return an iterator over the results, *roughly*
        in order of descending match quality. If the partial flag is True, non-isomorphic matches
        (those which do not fully map all patterns to graph structures) can be yielded. Otherwise,
        only isomorphic matches are yielded."""
        if context is None:
            context = {}
        for mapping in self._find_matches(context, partial=partial):
            yield PatternMatch.from_mapping(self, mapping)

    def _find_matches(self, context: typing.Mapping['Pattern', 'schema.Schema'] = None, *,
                      partial: bool = False) \
            -> typing.Iterator[typing.Dict['Pattern', 'schema.Schema']]:
        for mapping in self._find_full_matches(context):
            partial = False  # We only return a partial if a full match was not found.
            yield mapping
        if partial:
            mapping = self._find_partial_match(context)
            if mapping is not None:
                yield mapping

    def _find_partial_match(self, context: typing.Mapping['Pattern', 'schema.Schema']) \
            -> typing.Optional[typing.Mapping['Pattern', 'schema.Schema']]:
        """Find and return a partial match. If no partial match can be found, return None."""
        for mapping in self._find_full_matches(context):
            return mapping  # Take the first full match, if any.
        # If there were no full matches, we need to search for partial ones.
        mapping = dict(context)
        for selector in self.selectors:
            for mapping in selector._find_matches(mapping, partial=True):
                break  # Take the first one returned, if any.
        for child in self.children:
            for mapping in child._find_matches(mapping, partial=True):
                break  # Take the first one returned, if any.
        return mapping

    def _find_full_matches(self, context: typing.Mapping['Pattern', 'schema.Schema']) \
            -> typing.Iterator[typing.Mapping['Pattern', 'schema.Schema']]:
        """Return an iterator over full matches for this pattern. Context should be a dictionary
        partially mapping from related patterns to their images; yielded matches will be constrained
        to satisfy this mapping."""
        if self in context:
            # We already have a match candidate for this pattern.
            # Check for any selector pattern that doesn't have a match.
            for selector in self.selectors:
                if selector not in context:
                    # Selectors must always match the same vertex as the parent pattern.
                    extended_context = dict(context)
                    extended_context[selector] = extended_context[self]
                    for selector_match in selector._find_full_matches(extended_context):
                        partial_match = dict(context)
                        partial_match.update(selector_match)
                        assert selector in partial_match
                        yield from self._find_full_matches(partial_match)
                    break
            else:
                # If all selectors are good, check for any child pattern that doesn't have a match.
                for child in self.children:
                    if child not in context:
                        for child_match in child._find_full_matches(context):
                            partial_match = dict(context)
                            partial_match.update(child_match)
                            assert child in partial_match
                            yield from self._find_full_matches(partial_match)
                        break
                else:
                    # If all selectors and children are matched, simply yield the result.
                    yield context
        else:
            # We don't have a match candidate for this pattern yet. Go through each candidate and
            # yield the matches that result.
            for candidate in self.find_match_candidates(context):
                mapping = dict(context)
                mapping[self] = candidate
                yield from self._find_full_matches(mapping)

    def score_candidates(self, candidates: typing.Iterable['schema.Schema'],
                         context: typing.Mapping['Pattern', 'schema.Schema']) \
            -> typing.Dict['schema.Schema', float]:
        """Filter and score the given match candidates."""

        # Initialize candidate scores.
        # The preimage representative vertex's evidence mean represents the target truth value for
        # the image vertex.
        scores: typing.Dict['schema.Schema', float] = {}
        vertex_target_truth_value = evidence.get_evidence_mean(self.match.vertex)
        for candidate in candidates:
            vertex_actual_truth_value = evidence.get_evidence_mean(candidate.vertex)
            candidate_match_quality = 1 - (vertex_target_truth_value -
                                           vertex_actual_truth_value) ** 2
            scores[candidate] = candidate_match_quality

        # We treat each edge adjacent to the match representative that isn't used strictly for
        # pattern-related bookkeeping as a match constraint.
        vertex = self.match.vertex
        for edge in itertools.chain(vertex.iter_outbound(), vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES:
                continue
            outbound = edge.source == vertex
            other_vertex: elements.Vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            other_pattern = other_value.pattern.get()
            other_is_match_representative = other_pattern is not None
            required_neighbor = None
            if other_is_match_representative:
                other_pattern_match = context.get(other_pattern)
                if other_pattern_match:
                    # If the match representative of this pattern is connected to another match
                    # representative which is already mapped in the context, then we should
                    # constrain the candidates to those that connect in the same way to the vertex
                    # that the other match representative is mapped to. In simpler terms, we want
                    # to make sure that any edges on the preimage side are also present on the image
                    # side, but we can only do that if both patterns are mapped already.
                    required_neighbor = other_pattern_match.vertex
            else:
                # If the match representative of this pattern is connected to a vertex which is not
                # a match representative, then we treat the edge to the other vertex as a *literal*.
                # Any match for this pattern must also connect to that same exact vertex in the same
                # way.
                required_neighbor = other_vertex
            if required_neighbor is not None:
                # The preimage edge's evidence mean represents the target truth value for the
                # image edge.
                edge_target_truth_value = evidence.get_evidence_mean(edge)
                to_remove = []
                for candidate in scores:
                    edge_image = candidate.vertex.get_edge(edge.label, required_neighbor,
                                                           outbound=outbound)
                    if edge_image is None:
                        to_remove.append(candidate)
                    else:
                        edge_actual_truth_value = evidence.get_evidence_mean(edge_image)
                        edge_match_quality = 1 - (edge_target_truth_value -
                                                  edge_actual_truth_value) ** 2
                        scores[candidate] *= edge_match_quality
                for candidate in to_remove:
                    del scores[candidate]

        # Use selectors to further modulate the score.
        for selector in self.selectors:
            selector_scores = selector.score_candidates(scores, context)
            to_remove = []
            for candidate in scores:
                selector_score = selector_scores.get(candidate, None)
                if selector_score is None:
                    to_remove.append(candidate)
                else:
                    scores[candidate] *= selector_score
            for candidate in to_remove:
                del scores[candidate]

        return scores

    def find_match_candidates(self, context: typing.Mapping['Pattern', 'schema.Schema'] = None) \
            -> typing.Iterator[MatchSchema]:
        """For each vertex that satisfies the pattern's constraints, yield the vertex as a
        candidate. NOTE: To satisfy a pattern's constraints, a vertex must also be a valid
        match for every selector of the pattern."""

        # Find edges to/from the match representative which link to vertices that are not match
        # representatives. Use these non-pattern vertices as a search starting point. For example,
        # if the match representative is an instance with a non-pattern kind associated with it, we
        # can look at instances of that kind. Once we have a source of candidates identified in this
        # way, we can filter it through the constraints to identify reasonable candidates.
        vertex = self.match.vertex
        for edge in itertools.chain(vertex.iter_outbound(), vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES:
                continue
            outbound = edge.source == vertex
            other_vertex: elements.Vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            if other_value.pattern.defined:
                continue
            if outbound:
                candidate_set = {other_edge.source for other_edge in other_vertex.iter_inbound()
                                 if other_edge.label == edge.label}
            else:
                candidate_set = {other_edge.sink for other_edge in other_vertex.iter_outbound()
                                 if other_edge.label == edge.label}
            break
        else:
            # If we don't have a relevant and well-defined set of candidates to choose from, we
            # should just fail to match. Trying every vertex in the graph is simply not an option.
            return

        # TODO: We should maybe check data keys first. But I'm not sure if they'll even be used
        #       for pattern matching yet.

        candidate_set = {schema_registry.get_schema(candidate, self.database)
                         for candidate in candidate_set}
        candidate_scores = self.score_candidates(candidate_set, context)

        # Yield them in descending order of evidence to get the best matches first.
        yield from sorted(candidate_scores, key=candidate_scores.get, reverse=True)


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
    def _from_mapping(cls, root_pattern: 'Pattern',
                      mapping: typing.Mapping['Pattern', 'schema.Schema'],
                      result_mapping: typing.Dict['Pattern', 'PatternMatch'],
                      match_role: elements.Role) -> 'PatternMatch':
        if root_pattern in result_mapping:
            return result_mapping[root_pattern]
        root_match_vertex = root_pattern.database.add_vertex(match_role)
        root_match = cls(root_match_vertex, root_pattern.database)
        root_match.preimage.set(root_pattern)
        if root_pattern in mapping:
            # For partial matches, the pattern may not be mapped. In this case, we should simply
            # leave the image undefined in the match.
            root_match.image.set(mapping[root_pattern])
        result_mapping[root_pattern] = root_match
        for selector_pattern in root_pattern.selectors:
            selector_match = cls._from_mapping(selector_pattern, mapping, result_mapping,
                                               match_role)
            root_match.selectors.add(selector_match)
        for child_pattern in root_pattern.children:
            child_match = cls._from_mapping(child_pattern, mapping, result_mapping, match_role)
            root_match.children.add(child_match)
        return root_match

    @classmethod
    def from_mapping(cls, root_pattern: 'Pattern',
                     mapping: typing.Mapping['Pattern', 'schema.Schema']) -> 'PatternMatch':
        match_role = root_pattern.database.get_role(cls.role_name(), add=True)
        return cls._from_mapping(root_pattern, mapping, {}, match_role)

    def _fill_mapping(self, mapping: typing.Dict['Pattern', 'schema.Schema']) -> None:
        preimage = self.preimage.get(validate=False)
        if preimage is None or preimage in mapping:
            return
        mapping[preimage] = self.image.get(validate=False)
        for child in self.children:
            child._fill_mapping(mapping)
        for selector in self.selectors:
            selector._fill_mapping(mapping)

    # TODO: I just realized, we can't put selectors into the mapping, here or anywhere else in
    #       pattern-matching code. This is because there can be multiple occurrences of the same
    #       selector in the pattern tree, referring to different things. The problem originates from
    #       the fact that selectors were made into first-class patterns, but are shared between
    #       patterns. So we have one of 3 choices: (1) Make selector matching use a separate
    #       mapping, (2) make selectors not be first-class patterns and have patterns just reference
    #       them indirectly, or (3) copy selectors each time they are used. Option (1) is probably
    #       the easiest to do, but I'm not sure it's the best one. Options (2) and (3) are
    #       semantically distinct but functionally almost identical; in either case we end up with
    #       something that approximates the kind-instance distinction, but with patterns. This has
    #       some appeal, due to consistency, but I can't come up with a firm justification for the
    #       extra work involved.
    def get_mapping(self) -> typing.Dict['Pattern', 'schema.Schema']:
        mapping = {}
        self._fill_mapping(mapping)
        return mapping

    def is_isomorphic(self) -> bool:
        """Whether the image is isomorphic to the pattern for this match."""
        preimage: Pattern = self.preimage.get()
        assert preimage is not None
        representative_vertex = preimage.match.vertex

        # Make sure the preimage even has an image.
        image: 'schema.Schema' = self.image.get(validate=False)
        if image is None:
            return False

        # Check the edges.
        for edge in itertools.chain(representative_vertex.iter_outbound(),
                                    representative_vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES:
                continue
            outbound = edge.source == representative_vertex
            other_vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            other_pattern = other_value.pattern.get()
            if other_pattern is None:
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
                    if other_pattern == child.pattern:
                        child_image: 'schema.Schema' = child.image.get(validate=False)
                        assert child_image is not None
                        edge_image = image.vertex.get_edge(edge.label, child_image.vertex,
                                                           outbound=outbound)
                        if edge_image is None:
                            return False

        # Check the selectors and children.
        return (all(selector.is_isomorphic() for selector in self.selectors) and
                all(child.is_isomorphic() for child in self.children))

    def apply(self) -> None:
        """Update the graph to make the image isomorphic to the pattern, adding vertices and edges
        as necessary. Then apply positive evidence to the pattern, image, and match."""

        preimage: Pattern = self.preimage.get()
        assert preimage is not None
        representative_vertex = preimage.match.vertex

        # If there is no image, create one.
        if self.image.get(validate=False) is None:
            image_vertex = self.database.add_vertex(representative_vertex.preferred_role)
            self.image.set(schema.Schema(image_vertex, self.database))
            assert self.image.get(validate=False) is not None
            for selector in self.selectors:
                selector.image.set(self.image.get(validate=False))

        # Make sure all children and selectors are applied.
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
            other_preimage = other_value.pattern.get()
            if other_preimage is None:
                # The other value is not a pattern's match representative, so any edge between it
                # and the match representative for this pattern should be present between it and
                # the match image.
                if not image.vertex.get_edge(edge.label, other_vertex, outbound=outbound):
                    image.vertex.add_edge(edge.label, other_vertex, outbound=outbound)
            else:
                # The other value is a pattern's match representative. If its pattern appears in the
                # children of this match's preimage pattern, then we should add a corresponding edge
                # between this and the other match's images.
                for child in self.children:
                    if other_preimage == child.preimage.get():
                        child_image: 'schema.Schema' = child.image.get(validate=False)
                        assert child_image is not None
                        if not image.vertex.get_edge(edge.label, child_image.vertex,
                                                     outbound=outbound):
                            image.vertex.add_edge(edge.label, child_image.vertex, outbound=outbound)

        # Make sure each selector is satisfied. During partial matching, selectors of unmatched
        # patterns are never given a chance to match, since their matches are dependent on their
        # parents. So now we have to give them that chance.
        selector_context = self.get_mapping()
        for selector in preimage.selectors:
            selector_context[selector] = self.image.get(validate=False)
            for partial_match in selector.find_matches(selector_context, partial=True):
                # Take the first one found.
                partial_match.apply()
                selector_context = partial_match.get_mapping()
                break

        self.accept()

    def apply_evidence(self, mean: float, samples: float = 1):
        """Apply positive evidence to the pattern, image, and match, making no changes to image
        structure."""

        preimage: Pattern = self.preimage.get()
        assert preimage is not None
        representative_vertex = preimage.match.vertex

        # The match's evidence mean represents its likelihood of being accepted.
        evidence.apply_evidence(self.vertex, mean, samples)

        # The preimage's evidence mean represents the likelihood of matches containing it being
        # accepted.
        evidence.apply_evidence(preimage.vertex, mean, samples)

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
            other_pattern = other_value.pattern.get()
            if other_pattern is None:
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
                    if other_pattern == child.pattern:
                        child_image: 'schema.Schema' = child.image.get(validate=False)
                        assert child_image is not None
                        edge_image = image.vertex.get_edge(edge.label, child_image.vertex,
                                                           outbound=outbound)
                        if edge_image is not None:
                            # The image edge's evidence represents its likelihood of being true. We
                            # update it towards the preimage edge's truth value, at a rate
                            # proportionate to the target evidence mean.
                            evidence.apply_evidence(edge_image,
                                                    evidence.get_evidence_mean(edge),
                                                    mean)

    def accept(self) -> None:
        """Apply positive evidence to the pattern, image, and match, making no changes to image
        structure."""
        self.apply_evidence(1)

    def reject(self) -> None:
        """Apply negative evidence to the pattern and match, making no changes to image
        structure."""
        self.apply_evidence(0)


# =================================================================================================
# Attribute reverse-lookups. These have to be down here because they form cyclic references
# with the class definitions of the schemas they take as arguments.
# =================================================================================================

schema.Schema.pattern = schema.attribute('MATCH_REPRESENTATIVE', Pattern, outbound=False)

Word.kind = schema.attribute('NAME', Kind, outbound=False, plural=False)
Word.kinds = schema.attribute('NAME', Kind, outbound=False, plural=True)
Word.selector = schema.attribute('NAME', Pattern, outbound=False, plural=False)
Word.selectors = schema.attribute('NAME', Pattern, outbound=False, plural=True)
Word.divisibility = schema.attribute('NAME', Divisibility, outbound=False, plural=False)
Word.divisibilities = schema.attribute('NAME', Divisibility, outbound=False, plural=True)

Kind.instances = schema.attribute('KIND', Instance, outbound=False, plural=True,
                                  minimum_preference=0.5)

Time.earlier_times = schema.attribute('PRECEDES', Time, outbound=False, plural=True)
Time.later_times = schema.attribute('PRECEDES', Time, outbound=True, plural=True)
Time.observations = schema.attribute('TIME', Instance, outbound=False, plural=True)

Instance.instance = schema.attribute('INSTANCE', Instance, outbound=True, plural=False)
Instance.instances = schema.attribute('INSTANCE', Instance, outbound=True, plural=True)
Instance.observations = schema.attribute('INSTANCE', Instance, outbound=False, plural=True)
Instance.actor = schema.attribute('ACTOR', Instance, outbound=True, plural=False)

Pattern.selectors = schema.attribute('SELECTOR', Pattern, outbound=True, plural=True)
Pattern.children = schema.attribute('CHILD', Pattern, outbound=True, plural=True)

PatternMatch.selectors = schema.attribute('SELECTOR', PatternMatch, outbound=True, plural=True)
PatternMatch.children = schema.attribute('CHILD', PatternMatch, outbound=True, plural=True)
