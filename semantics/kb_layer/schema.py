"""
Knowledge base ORM-related functionality.


Usage:

class MyOtherClass(Schema):
    ...


class MyClass(Schema):

    @validation("{schema} should have property X.")
    def has_X(self) -> bool:
        return hasattr(self, 'X')

    my_attribute = attribute('MyEdgeLabel', MyOtherClass, plural=False)
    my_attributes = attribute('MyEdgeLabel', MyOtherClass, plural=True)


kb = ...
vertex = ...
obj = MyClass(vertex, kb, validate=False)

if not obj.is_valid:  # Executes each validator and makes sure it returns True
    # Returns the message associated with the first failing validator
    print(obj.get_validation_error())
obj.validate()  # Raises an exception if any validation does not pass

# Gets the value of the attribute, which will either be None or a MyOtherClass instance
obj.my_attribute()

obj.my_attribute = MyOtherClass(...)  # Sets the value of the attribute
obj.my_attribute.is_defined  # True if the property has a defined value, False if it is None

# Gets an iterator over the values of the attribute, each of which is a MyOtherClass instance
obj.my_attributes()

len(obj.my_attributes)  # The number of items that would be yielded by obj.my_attributes()
other_obj in obj.my_attributes  # Whether the other object belongs to this attribute's values
"""
import functools
import re
import typing

from semantics.kb_layer.schema_attributes import attribute

from semantics.data_types import exceptions
from semantics.graph_layer import elements

if typing.TYPE_CHECKING:
    import semantics.graph_layer.interface as graph_db_interface
    from semantics.kb_layer import orm, schema_attributes


__all__ = [
    'validation',
    'attribute',
    'Schema',
]


class SchemaValidation:
    """A validation method of a schema. Validation methods must return True for the schema instance
    to pass validation."""

    def __init__(self, message: str, implementation: typing.Callable[['Schema'], bool]):
        self._name = None
        self._message = message
        self._implementation = implementation

    def __str__(self):
        assert self._name
        return self._name

    def format_message(self, instance: 'Schema') -> str:
        """Format the schema validation message, replacing {schema} with the schema name."""
        return self._message.format(schema=type(instance).__name__)

    def get_validation_error(self, instance: 'Schema') -> typing.Optional[str]:
        """If validation of this schema instance fails, return a string describing why it failed.
        Otherwise, return None."""
        if self._implementation(instance):
            return None
        return self.format_message(instance)

    def validate(self, instance: 'Schema') -> None:
        """If validation of this schema instance fails, raise a SchemaValidationError."""
        if not self._implementation(instance):
            raise exceptions.SchemaValidationError(self.format_message(instance))

    def __set_name__(self, owner: typing.Type['Schema'], name):
        assert self._name is None
        self._name = name
        owner.add_validator(self)

    def __get__(self, instance: 'Schema', owner) -> typing.Callable[[], bool]:
        return functools.partial(self._implementation, instance)

    def __call__(self, instance: 'Schema') -> bool:
        return self._implementation(instance)


def validation(message: str, implementation: typing.Callable[['Schema'], bool] = None):
    """Decorator for schema validation methods.

    Usage:
        >>> class MySchema(Schema):
        >>>     @validation("Foo validation failed.")
        >>>     def foo(self) -> bool:
        >>>         return True
        >>>     @validation("Bar validation failed.")
        >>>     def bar(self) -> bool:
        >>>         return False
        >>> instance = MySchema(...)
        >>> instance.get_validation_error()
        "Bar validation failed."
        >>>
    """
    if implementation:
        return SchemaValidation(message, implementation)
    return lambda implementation: SchemaValidation(message, implementation)


class Schema:
    """Base class for ORM schemata. A schema is a class that controls how the underlying graph
    is interacted with, to ensure that standardized representational patterns are respected."""

    __role_name__ = None
    __validators__: typing.Dict[typing.Type['Schema'], typing.List[SchemaValidation]] = {}

    # If this attribute is defined, this schema instance is a match representative of a pattern.
    pattern: 'schema_attributes.SingularAttribute[orm.Pattern]'

    @classmethod
    def role_name(cls) -> str:
        """The name of the vertex role in the database that this schema is associated with."""
        if cls.__role_name__ is None:
            assert cls is not Schema
            # By default, we set the name to the all uppercase snake-case name, i.e. what we would
            # use for constants. For example, MyClassName would be converted to MY_CLASS_NAME.
            cls.__role_name__ = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).upper()
        return cls.__role_name__

    @classmethod
    def add_validator(cls, validator: SchemaValidation) -> None:
        """Add a validator to the schema."""
        if cls in cls.__validators__:
            cls.__validators__[cls].append(validator)
        else:
            cls.__validators__[cls] = [validator]

    @classmethod
    def iter_validators(cls) -> typing.Iterator[SchemaValidation]:
        """Return an iterator over all validators for this schema."""
        yield from cls.__validators__.get(cls, ())
        super_validators = getattr(super(), 'iter_validators', None)
        if super_validators is not None:
            # Pylint things that super_validators is not callable, and can't be persuaded otherwise.
            # pylint: disable=E1102
            yield from super_validators()

    def __init__(self, vertex: elements.Vertex, database: 'graph_db_interface.GraphDBInterface',
                 validate: bool = False):
        self._database = database
        self._vertex = vertex
        if validate:
            self.validate()

    def __repr__(self) -> str:
        return '<%s#%s>' % (type(self).__name__, int(self._vertex.index))

    def __eq__(self, other: 'Schema') -> bool:
        return type(self) is type(other) and self._vertex == other._vertex

    def __ne__(self, other: 'Schema') -> bool:
        return not (type(self) is type(other) and self._vertex == other._vertex)

    def __hash__(self) -> int:
        return hash(type(self)) ^ (hash(self._vertex) << 3)

    @property
    def database(self) -> 'graph_db_interface.GraphDBInterface':
        """The graph database where this schema instance resides."""
        return self._database

    @property
    def is_valid(self) -> bool:
        """Whether this schema instance is valid, according to its validators."""
        for validator in self.iter_validators():
            if not validator(self):
                return False
        return True

    def get_validation_error(self) -> typing.Optional[str]:
        """If any of the schema's validators fail for this schema instance, return a string
        explaining why. Otherwise, return None."""
        for validator in self.iter_validators():
            message = validator.get_validation_error(self)
            if message:
                return message
        return None

    def validate(self) -> None:
        """If any of the schema's validators fail for this schema instance, raise a
        SchemaValidationError with a descriptive message explaining why."""
        for validator in self.iter_validators():
            validator.validate(self)

    @validation('{schema} has incorrect role.')
    def has_correct_role(self):
        """Whether this schema instance's vertex has the expected role. In order for this schema
        instance to pass validation, this must return True."""
        return self._vertex.preferred_role == self._database.get_role(self.role_name())

    @property
    def vertex(self) -> elements.Vertex:
        """The vertex in the graph database that is associated with this schema instance."""
        return self._vertex
