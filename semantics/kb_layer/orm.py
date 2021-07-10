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

    # TODO: Don't specify a schema here. Make attributes pick schemas based on the defined
    #       associations between schemas in the ORM and roles in the graph.
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
        """The match representative of the pattern."""
        return self.match_representative.get(validate=False)

    def find_matches(self, context: typing.Mapping['Pattern', 'schema.Schema'] = None, *,
                     partial: bool = False) -> typing.Iterator['PatternMatch']:
        """Search the graph for matching subgraphs. Return an iterator over the results, *roughly*
        in order of descending match quality. If the partial flag is True, non-isomorphic matches
        (those which do not fully map all patterns to graph structures) can be yielded. Otherwise,
        only isomorphic matches are yielded."""
        if context is None:
            context = {}
        for mapping in self._find_full_matches(context):
            partial = False  # We only return a partial if a full match was not found.
            yield PatternMatch.from_mapping(mapping)
        if partial:
            mapping = self._find_partial_match(context)
            if mapping is not None:
                yield PatternMatch.from_mapping(mapping)

    def _find_partial_match(self, context: typing.Mapping['Pattern', 'schema.Schema']) \
            -> typing.Optional[typing.Mapping['Pattern', 'schema.Schema']]:
        """Find and return a partial match. If no partial match can be found, return None."""
        mapping = dict(context)
        for child in self.children:
            for mapping in child._find_full_matches(mapping):
                break  # Take the first one returned.
            else:
                # This is possible if the later-matched children are constrained by the
                # earlier-matched ones.
                return None
            assert child in mapping
        return context

    def _find_full_matches(self, context: typing.Mapping['Pattern', 'schema.Schema']) \
            -> typing.Iterator[typing.Mapping['Pattern', 'schema.Schema']]:
        """Return an iterator over full matches for this pattern. Context should be a dictionary
        partially mapping from related patterns to their images; yielded matches will be constrained
        to satisfy this mapping."""
        if self in context:
            # We already have a match candidate for this pattern. Either find a child which doesn't
            # have a match, or, if none exists, yield the result.
            for child in self.children:
                if child not in context:
                    for child_match in child._find_full_matches(context):
                        partial_match = dict(context)
                        partial_match.update(child_match)
                        yield from self._find_full_matches(partial_match)
                    break
            else:
                yield context
        else:
            # We don't have a match candidate for this pattern yet. Go through each candidate in
            # descending order of match quality and yield the matches that result.
            for candidate in self.find_match_candidates(context):
                mapping = dict(context)
                mapping[self] = candidate
                yield from self._find_full_matches(context)

    def score_candidates(self, candidates: typing.Iterable['schema.Schema'],
                         context: typing.Mapping['Pattern', 'schema.Schema']) \
            -> typing.Dict['schema.Schema', evidence.Evidence]:
        """Filter and score the given match candidates."""

        # Start with initially high scores.
        scores: typing.Dict['schema.Schema', 'evidence.Evidence'] = {
            candidate: evidence.Evidence(1.0, 1.0)
            for candidate in candidates
        }

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
                # The larger the evidence mean for the pattern's edge, the more important we
                # consider the edge to be during matching.
                edge_weight = evidence.get_evidence(edge).mean
                to_remove = []
                for candidate in scores:
                    edge_image = candidate.vertex.get_edge(edge.label, required_neighbor,
                                                           outbound=outbound)
                    if edge_image is None:
                        to_remove.append(candidate)
                    else:
                        edge_image_evidence_mean = evidence.get_evidence_mean(edge_image)
                        effect = evidence.Evidence(edge_image_evidence_mean, edge_weight)
                        scores[candidate].update(effect)
                for candidate in to_remove:
                    del scores[candidate]

        # Apply selectors to further modulate the score.
        for selector in self.selectors:
            selector_scores = selector.score_candidates(scores, context)
            to_remove = []
            for candidate, pattern_evidence in scores.items():
                selector_evidence = selector_scores.get(candidate, None)
                if selector_evidence is None:
                    to_remove.append(candidate)
                else:
                    pattern_evidence.update(selector_evidence)
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

        candidate_scores = self.score_candidates(candidate_set, context)

        # Yield them in descending order of evidence to get the best matches first.
        yield from sorted(candidate_scores,
                          key=lambda candidate: candidate_scores[candidate].mean,
                          reverse=True)


@schema_registry.register
class PatternMatch(schema.Schema):
    """A pattern match is a mapping from a pattern structure to a subgraph of the knowledge
    graph. The specific point in the subgraph at which the pattern matched is referred to as
    its image."""

    preimage = schema.attribute('PREIMAGE', Pattern)
    image = schema.attribute('IMAGE')

    children: 'schema_attributes.PluralAttribute[PatternMatch]'

    def is_isomorphic(self) -> bool:
        """Whether the image is isomorphic to the pattern for this match."""
        raise NotImplementedError()

    def apply(self) -> None:
        """Update the graph to make the image isomorphic to the pattern, adding vertices and edges
        as necessary. Then apply positive evidence to the pattern, image, and match."""
        raise NotImplementedError()

    def accept(self) -> None:
        """Apply positive evidence to the pattern, image, and match, making no changes to image
        structure."""
        raise NotImplementedError()

    def reject(self) -> None:
        """Apply negative evidence to the pattern and match, making no changes to image
        structure."""
        raise NotImplementedError()


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

PatternMatch.children = schema.attribute('CHILD', PatternMatch, outbound=True, plural=True)
