"""The Object-Relational Model to map from semantic structures to graph elements."""

import typing

from semantics.kb_layer import schema
from semantics.data_types import typedefs


if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


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

    kinds: 'schema_attributes.PluralAttribute'


class Kind(schema.Schema):
    """A kind is an abstract type of thing."""

    @schema.validation('{schema} should have at least one name Word.')
    def has_name(self) -> bool:
        """Whether the kind has an associated name. In order for the kind to pass validation, this
        must return True."""
        return self.name.defined

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    instances: 'schema_attributes.PluralAttribute'


class Instance(schema.Schema):
    """An instance is a particular thing."""

    @schema.validation('{schema} should have at least one Kind.')
    def has_kind(self) -> bool:
        """Whether the instance has an associated kind. In order for the instance to pass
        validation, this must return True."""
        return self.kind.defined

    # Individual instances can be named just like kinds, but usually don't.
    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    kind = schema.attribute('KIND', Kind)
    kinds = schema.attribute('KIND', Kind, plural=True)

    observations: 'schema_attributes.PluralAttribute'


class Time(schema.Schema):
    """A time can represent a specific point in type if it has a time stamp, or else an abstract
    point or span of time if it has no time stamp."""

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        """The time stamp, if any, associated with this time."""
        return self._vertex.time_stamp

    observations: 'schema_attributes.PluralAttribute'


class Observation(schema.Schema):
    """An observation is a thing at a particular point in time."""

    @schema.validation('{schema} should have a single associated Time.')
    def has_time(self) -> bool:
        """Whether the observation has an associated time. In order for the observation to
        pass validation, this must return True."""
        return self.time.defined

    @schema.validation('{schema} should have at least one Instance.')
    def has_instance(self) -> bool:
        """Whether the observation has an associated instance. In order for the observation to
        pass validation, this must return True."""
        return self.instance.defined

    time = schema.attribute('TIME', Time)
    times = schema.attribute('TIME', Time, plural=True)

    instance = schema.attribute('INSTANCE', Instance)
    instances = schema.attribute('INSTANCE', Instance, plural=True)


# Attribute reverse-lookups. These have to be down here because they form cyclic references
# with the class definitions of the schemas they take as arguments.
Word.kinds = schema.attribute('WORD', Kind, outbound=False, plural=True)
Kind.instances = schema.attribute('KIND', Instance, outbound=False, plural=True)
Instance.observations = schema.attribute('INSTANCE', Observation, outbound=False, plural=True)
Time.observations = schema.attribute('TIME', Observation, outbound=False, plural=True)
