"""
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

import re
import typing

from semantics.kb_layer.schema_attributes import attribute

import semantics.data_types.exceptions as exceptions
import semantics.graph_layer.elements as elements

if typing.TYPE_CHECKING:
    import semantics.graph_layer.interface as graph_db_interface

__all__ = [
    'validation',
    'attribute',
    'Schema',
]


class SchemaValidation:

    def __init__(self, message: str, implementation: typing.Callable[['Schema'], bool]):
        self._message = message
        self._implementation = implementation

    def format_message(self, instance: 'Schema') -> str:
        return self._message.format(schema=type(instance).__name__)

    def is_valid(self, instance: 'Schema'):
        return self._implementation(instance)

    def get_validation_error(self, instance: 'Schema') -> typing.Optional[str]:
        if self._implementation(instance):
            return None
        return self.format_message(instance)

    def validate(self, instance: 'Schema') -> None:
        if not self._implementation(instance):
            raise exceptions.SchemaValidationError(self.format_message(instance))


def validation(message: str, implementation: typing.Callable[['Schema'], bool] = None):
    """Decorator for schema validation methods."""
    if implementation:
        return SchemaValidation(message, implementation)
    return lambda implementation: SchemaValidation(message, implementation)


class Schema:

    __role_name__ = None

    @classmethod
    def role_name(cls) -> str:
        if cls.__role_name__ is None:
            # By default, we set the name to the all uppercase snake-case name, i.e. what we would
            # use for constants. For example, MyClassName would be converted to MY_CLASS_NAME.
            cls.__role_name__ = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).upper()
        return cls.__role_name__

    def __init__(self, vertex: elements.Vertex, database: 'graph_db_interface.GraphDBInterface',
                 validate: bool = False):
        self._database = database
        self._vertex = vertex
        if validate:
            self.validate()

    @property
    def database(self) -> 'graph_db_interface.GraphDBInterface':
        return self._database

    @property
    def is_valid(self) -> bool:
        for validator in vars(self).values():
            if isinstance(validator, SchemaValidation) and not validator.is_valid(self):
                return False
        return True

    def get_validation_error(self) -> typing.Optional[str]:
        for validator in vars(self).values():
            if isinstance(validator, SchemaValidation):
                message = validator.get_validation_error(self)
                if message:
                    return message
        return None

    def validate(self) -> None:
        for validator in vars(self).values():
            if isinstance(validator, SchemaValidation):
                validator.validate(self)

    @validation('{schema} has incorrect role.')
    def validate_role(self):
        return self._vertex.preferred_role == self._database.get_role(self.role_name())

    @property
    def vertex(self) -> elements.Vertex:
        return self._vertex
