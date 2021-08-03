import itertools
import logging
import typing

from semantics.graph_layer import elements
from semantics.kb_layer import schema, evidence, orm
from semantics.kb_layer import schema_registry

from semantics.kb_layer.orm._word_schema import Word

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


PATTERN_RELATED_LABEL_NAMES = frozenset([
    'TEMPLATE',
    'MATCH_REPRESENTATIVE',
    'CHILD',
    'SELECTOR',
    'PREIMAGE',
    'IMAGE',
])


MatchSchema = typing.TypeVar('MatchSchema', bound=schema.Schema)
MatchMapping = typing.Dict['Pattern', typing.Tuple['schema.Schema', float]]


@schema_registry.register
class Pattern(schema.Schema, typing.Generic[MatchSchema]):
    """A pattern is a description of the structure of a subgraph of the knowledge graph. Patterns
    correspond to phrases or sentences in natural language. The components of the pattern are
    arranged into a tree or hierarchy which determines the order of search. Matches are built up
    from the leaves to the root of the tree, with each branch representing a sub-clause or
    sub-phrase of the larger pattern."""

    def __repr__(self) -> str:
        name = '<unnamed>'
        name_obj = self.name.get(validate=False)
        if name_obj and name_obj.spelling:
            name = name_obj.spelling
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index), name)

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

    # The template pattern, if defined, is another pattern which was cloned to produce this one,
    # and which should have its evidence updated when this pattern's evidence is updated.
    template: 'schema_attributes.SingularAttribute[Pattern[MatchSchema]]'

    @property
    def match(self) -> typing.Optional[MatchSchema]:
        """The match representative of the pattern.

        NOTE: The evidence mean for the pattern represents its accuracy, whereas the evidence mean
        for the match representative represents the truth value to be matched in the image vertex.
        """
        return self.match_representative.get(validate=False)

    def templated_clone(self) -> 'Pattern':
        """Clone this pattern (and its selectors and children) to produce a new, identical deep
        copy. This pattern's evidence will be updated whenever the clone's is.

        The purpose for cloning of patterns is to ensure that during matching, each point of usage
        of a reusable pattern has its own unique and distinguishable identity. For example, consider
        the selector pattern, "the", in the phrase "the eye of the storm". If the same pattern is
        used for both occurrences of "the", then we cannot distinguish their matches and assign a
        different value to each usage.
        """
        clone_vertex = self.database.add_vertex(self.vertex.preferred_role)
        clone = Pattern(clone_vertex, self.database)
        clone.template.set(self)
        clone.match_representative.set(self.match_representative.get(validate=False))
        for selector in self.selectors:
            clone.selectors.add(selector.templated_clone())
        for child in self.children:
            clone.children.add(child.templated_clone())
        return clone

    def find_matches(self, context: MatchMapping = None, *,
                     partial: bool = False) -> typing.Iterator['orm.PatternMatch']:
        """Search the graph for matching subgraphs. Return an iterator over the results, *roughly*
        in order of descending match quality. If the partial flag is True, non-isomorphic matches
        (those which do not fully map all patterns to graph structures) can be yielded. Otherwise,
        only isomorphic matches are yielded."""
        if context is None:
            context = {}
        for mapping in self._find_matches(context, partial=partial):
            yield orm.PatternMatch.from_mapping(self, mapping, context)

    def _find_matches(self, context: MatchMapping = None, *,
                      partial: bool = False) -> typing.Iterator[MatchMapping]:
        if context is None:
            context = {}
        for mapping in self._find_full_matches(context):
            partial = False  # We only return a partial if a full match was not found.
            yield mapping
        if partial:
            mapping = self._find_partial_match(context)
            if mapping is not None:
                # Remove images with attached data if we are partially matching. Otherwise, during
                # calls to apply() we will confabulate memories.
                to_remove = []
                for key, (value, score) in mapping.items():
                    if (value.vertex.count_data_keys() > 0 and
                            key not in context and
                            key.template.get(validate=False) not in context):
                        to_remove.append(key)
                for key in to_remove:
                    del mapping[key]
                yield mapping

    def _find_partial_match(self, context: MatchMapping) -> typing.Optional[MatchMapping]:
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

    def _find_full_matches(self, context: MatchMapping) -> typing.Iterator[MatchMapping]:
        """Return an iterator over full matches for this pattern. Context should be a dictionary
        partially mapping from related patterns to their images; yielded matches will be constrained
        to satisfy this mapping."""
        template = self.template.get(validate=False)
        if template is not None and template in context:
            context = dict(context)
            context[self] = context[template]
        # Check for any child pattern that doesn't have a match.
        for child in self.children:
            if child not in context:
                for child_match in child._find_full_matches(context):
                    partial_match = dict(context)
                    partial_match.update(child_match)
                    assert child in partial_match
                    yield from self._find_full_matches(partial_match)
                return
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
                    return
            # There are no selectors to check, just yield the match.
            yield context
        else:
            # Go through each candidate and yield the matches that result.
            for candidate in self.find_match_candidates(context):
                mapping = dict(context)
                mapping[self] = candidate
                yield from self._find_full_matches(mapping)

    def score_candidates(self, candidates: typing.Iterable['schema.Schema'],
                         context: MatchMapping) -> typing.Dict['schema.Schema', float]:
        """Filter and score the given match candidates."""

        assert self not in context, (self, candidates, context)

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
            # other_pattern = other_value.pattern.get(validate=False)
            required_neighbor = required_neighbor_score = None
            if other_value.represented_pattern.defined:
                for other_pattern, other in context.items():
                    if other_pattern.match != other_value:
                        continue
                    # If the match representative of this pattern is connected to another match
                    # representative which is already mapped in the context, then we should
                    # constrain the candidates to those that connect in the same way to the vertex
                    # that the other match representative is mapped to. In simpler terms, we want
                    # to make sure that any edges on the preimage side are also present on the image
                    # side, but we can only do that if both patterns are mapped already.
                    other_pattern_match, other_pattern_score = other
                    required_neighbor = other_pattern_match.vertex
                    required_neighbor_score = other_pattern_score
            else:
                # If the match representative of this pattern is connected to a vertex which is not
                # a match representative, then we treat the edge to the other vertex as a *literal*.
                # Any match for this pattern must also connect to that same exact vertex in the same
                # way.
                required_neighbor = other_vertex
                required_neighbor_score = 1.0
            if required_neighbor is not None:
                # The preimage edge's evidence mean represents the target truth value for the
                # image edge.
                edge_target_truth_value = evidence.get_evidence_mean(edge)
                to_remove = []
                for candidate in scores:
                    scores[candidate] *= required_neighbor_score
                    edge_image = candidate.vertex.get_edge(edge.label, required_neighbor,
                                                           outbound=outbound)
                    if edge_image is None:
                        if not edge.label.transitive:
                            to_remove.append(candidate)
                            continue
                        # neighbors = candidate.vertex.iter_transitive_neighbors(edge.label,
                        #                                                        outbound=outbound)
                        # if required_neighbor not in neighbors:
                        #     to_remove.append(candidate)
                        #     continue

                        path = candidate.vertex.get_shortest_transitive_path(edge.label,
                                                                             required_neighbor,
                                                                             outbound=outbound)
                        if path is None:
                            to_remove.append(candidate)
                            continue

                        # TODO: When we apply evidence to direct edges in apply(), we should also
                        #       do the same for each edge in transitive paths where they are what is
                        #       matched.
                        # Use the product of evidence means of the edges that were followed to
                        # modulate the score for the candidate.
                        edge_actual_truth_value = 1
                        for path_edge, _path_vertex in path:
                            if path_edge is not None:
                                edge_actual_truth_value *= evidence.get_evidence_mean(path_edge)
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

    def find_match_candidates(self, context: MatchMapping = None,
                              neighbor: elements.Vertex = None) \
            -> typing.Iterator[typing.Tuple[MatchSchema, float]]:
        """For each vertex that satisfies the pattern's constraints, yield the vertex as a
        candidate. NOTE: To satisfy a pattern's constraints, a vertex must also be a valid
        match for every selector of the pattern.

        If neighbor is not None, the method only looks at vertices that are neighbors to the given
        vertex.
        """

        # Find edges to/from the match representative which link to vertices that are not match
        # representatives. Use these non-pattern vertices as a search starting point. For example,
        # if the match representative is an instance with a non-pattern kind associated with it, we
        # can look at instances of that kind. Once we have a source of candidates identified in this
        # way, we can filter it through the constraints to identify reasonable candidates.
        # We look first at intransitive edges because they are more efficient to work with.
        vertex = self.match.vertex
        for edge in itertools.chain(vertex.iter_outbound(), vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES or edge.label.transitive:
                continue
            outbound = edge.source == vertex
            other_vertex: elements.Vertex = edge.sink if outbound else edge.source
            if neighbor is not None and neighbor != other_vertex:
                continue
            other_value = schema_registry.get_schema(other_vertex, self.database)
            # other_pattern = other_value.pattern.get(validate=False)
            if other_value.represented_pattern.defined:
                for other_pattern, other in context.items():
                    if other_pattern.match != other_value:
                        continue
                    # Overwrite other_value/other_vertex with its image
                    other_value, other_score = context[other_pattern]
                    other_vertex = other_value.vertex
                    break
                else:
                    continue
            if outbound:
                candidate_set = {other_edge.source for other_edge in other_vertex.iter_inbound()
                                 if other_edge.label == edge.label}
            else:
                candidate_set = {other_edge.sink for other_edge in other_vertex.iter_outbound()
                                 if other_edge.label == edge.label}
            break
        else:
            # If we can't find a good intransitive edge, look at transitive ones.
            for edge in itertools.chain(vertex.iter_outbound(), vertex.iter_inbound()):
                if edge.label.name in PATTERN_RELATED_LABEL_NAMES or not edge.label.transitive:
                    continue
                outbound = edge.source == vertex
                other_vertex: elements.Vertex = edge.sink if outbound else edge.source
                if neighbor is not None and neighbor != other_vertex:
                    continue
                other_value = schema_registry.get_schema(other_vertex, self.database)
                # other_pattern = other_value.pattern.get(validate=False)
                if other_value.represented_pattern.defined:
                    for other_pattern, other in context.items():
                        if other_pattern.match != other_value:
                            continue
                        # Overwrite other_value/other_vertex with its image
                        other_value, other_score = context[other_pattern]
                        other_vertex = other_value.vertex
                        break
                    else:
                        continue
                candidate_set = set(other_vertex.iter_transitive_neighbors(edge.label,
                                                                           outbound=not outbound))
                break
            else:
                # If we don't have a relevant and well-defined set of candidates to choose from, we
                # should just fail to match. Trying every vertex in the graph is simply not an
                # option.
                logging.info("No candidates found for: %s", self)
                return

        # TODO: We should maybe check data keys first. But I'm not sure if they'll even be used
        #       for pattern matching yet.

        candidate_set = {schema_registry.get_schema(candidate, self.database)
                         for candidate in candidate_set}
        candidate_set = {value for value in candidate_set if not value.represented_pattern.defined}
        candidate_scores = self.score_candidates(candidate_set, context)

        # Yield them in descending order of evidence to get the best matches first.
        yield from sorted(candidate_scores.items(), key=lambda item: item[-1], reverse=True)

    def iter_trigger_points(self) -> typing.Iterator[typing.Tuple['Pattern', 'schema.Schema']]:
        vertex = self.match.vertex
        for edge in itertools.chain(vertex.iter_outbound(), vertex.iter_inbound()):
            if edge.label.name in PATTERN_RELATED_LABEL_NAMES or edge.label.transitive:
                continue
            outbound = edge.source == vertex
            other_vertex: elements.Vertex = edge.sink if outbound else edge.source
            other_value = schema_registry.get_schema(other_vertex, self.database)
            if not other_value.represented_pattern.defined:
                yield self, other_value
        for child in self.children:
            yield from child.iter_trigger_points()
