"""The Object-Relational Model to map from semantic structures to graph elements."""

import typing

from semantics.data_types import typedefs
from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


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

    def find_matches(self, *, partial: bool = False,
                     context: typing.Dict['Pattern', 'schema.Schema'] = None) \
            -> typing.Iterator['PatternMatch']:
        """Search the graph for matching subgraphs. Return an iterator over the results, in order
        of descending match quality. If the partial flag is True, non-isomorphic matches (those
        which do not fully map all patterns to graph structures) can be yielded. Otherwise,
        only isomorphic matches are yielded. If context is provided, it should be a dictionary
        partially mapping from related patterns to their images; yielded matches will be constrained
        to satisfy this mapping."""
        # TODO:
        #   Recursively walk the pattern to find subgraphs that match it:
        #   * If context is provided and this pattern appears in it:
        #       * Identify the first child not appearing in the context.
        #       * If no such child exists:
        #           * Yield the context as a match.
        #       * Otherwise:
        #           * For each contextual match of the identified child:
        #               * Temporarily extend the context to incorporate the child's match.
        #               * Recursively yield from find_matches for this pattern with the newly
        #                 extended context.
        #   * Otherwise, if context is provided and this pattern does not appear in it:
        #       * For each match for this pattern which satisfies the context:
        #           * Temporarily add the match to the context.
        #           * Recursively yield from find_matches for this pattern with the newly extended
        #             context.
        #   * Otherwise, if there are children:
        #       * For each match of the first child:
        #           * Create a context mapping the first child to its match.
        #           * Recursively yield from find_matches for this pattern with the newly created
        #             context.
        #   * Otherwise:
        #       * For each vertex that satisfies the pattern's constraints:
        #           * Yield the vertex as a match for the pattern.
        #   * If partial is True and no matches have already been yielded:
        #       * Map each child pattern to its best match.
        #       * Yield the partial mapping as a match.
        #   NOTE: To satisfy a pattern's constraints, a vertex must also be a valid match for every
        #         selector of the pattern.
        raise NotImplementedError()


@schema_registry.register
class PatternMatch(schema.Schema):
    """A pattern match is a mapping from a pattern structure to a subgraph of the knowledge
    graph. The specific point in the subgraph at which the pattern matched is referred to as
    its image."""

    pattern = schema.attribute('PATTERN', Pattern)
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
