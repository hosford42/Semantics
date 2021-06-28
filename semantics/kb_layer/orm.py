"""The Object-Relational Model to map from semantic structures to graph elements."""

import typing

import semantics.kb_layer.schema as schema
import semantics.data_types.typedefs as typedefs


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


class Kind(schema.Schema):
    """A kind is an abstract type of thing."""

    @schema.validation('{schema} should have at least one name Word.')
    def has_name(self) -> bool:
        """Whether the kind has an associated name. In order for the kind to pass validation, this
        must return True."""
        return self.name.defined

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)


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


class Time(schema.Schema):
    """A time can represent a specific point in type if it has a time stamp, or else an abstract
    point or span of time if it has no time stamp."""

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        """The time stamp, if any, associated with this time."""
        return self._vertex.time_stamp


class Manifestation(schema.Schema):
    """A manifestation is a thing at a particular point in time."""

    @schema.validation('{schema} should have a single associated Time.')
    def has_time(self) -> bool:
        """Whether the manifestation has an associated time. In order for the manifestation to
        pass validation, this must return True."""
        return self.time.defined

    @schema.validation('{schema} should have at least one Instance.')
    def has_instance(self) -> bool:
        """Whether the manifestation has an associated instance. In order for the manifestation to
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
Instance.manifestations = schema.attribute('INSTANCE', Manifestation, outbound=False, plural=True)
Time.manifestations = schema.attribute('TIME', Manifestation, outbound=False, plural=True)
