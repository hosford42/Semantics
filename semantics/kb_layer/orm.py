"""The Object-Relational Model to map from semantic structures to graph elements."""

import typing

import semantics.kb_layer.schema as schema
import semantics.data_types.typedefs as typedefs


class Word(schema.Schema):
    """A word is a sequence of characters, independent of their meaning."""

    @schema.validation('{schema} must have an associated spelling attribute.')
    def has_spelling(self) -> bool:
        return self._vertex.name is not None

    @property
    def spelling(self) -> typing.Optional[str]:
        return self._vertex.name


class Kind(schema.Schema):
    """A kind is an abstract type of thing."""

    @schema.validation('{schema} should have at least one name Word.')
    def has_name(self) -> bool:
        return self.name.defined

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)


class Instance(schema.Schema):
    """An instance is a particular thing."""

    @schema.validation('{schema} should have at least one Kind.')
    def has_kind(self) -> bool:
        return self.kind.defined

    # Individual instances can be named just like kinds, but usually don't.
    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    kind = schema.attribute('KIND', Kind)
    kinds = schema.attribute('KIND', Kind, plural=True)


class Time(schema.Schema):

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        return self._vertex.time_stamp


class Manifestation(schema.Schema):
    """A manifestation is a thing at a particular point in time."""

    @schema.validation('{schema} should have a single associated Time.')
    def has_time(self) -> bool:
        return self.time.defined

    @schema.validation('{schema} should have at least one Instance.')
    def has_instance(self) -> bool:
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
