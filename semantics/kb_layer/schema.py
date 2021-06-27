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
    print(obj.get_validation_error())  # Returns the message associated with the first failing validator
obj.validate()  # Raises an exception if any validation does not pass

obj.my_attribute()  # Gets the value of the attribute, which will either be None or a MyOtherClass instance
obj.my_attribute = MyOtherClass(...)  # Sets the value of the attribute
obj.my_attribute.is_defined  # True if the property has a defined value, False if it is None

obj.my_attributes()  # Gets an iterator over the values of the attribute, each of which is a MyOtherClass instance
len(obj.my_attributes)  # The number of items that would be yielded by obj.my_attributes()
other_obj in obj.my_attributes  # Whether the other object belongs to this attribute's values
"""

import re
import typing

import semantics.data_types.exceptions as exceptions
import semantics.graph_layer.elements as elements
import semantics.graph_layer.interface as graph_db_interface
import semantics.kb_layer.evidence as evidence
from semantics.data_types import comparable


class SchemaValidation:

    def __init__(self, message: str, implementation: typing.Callable[['Schema'], bool]):
        self._message = message
        self._implementation = implementation

    def format_message(self, instance: 'Schema') -> str:
        return self._message.format(schema=type(instance).__name__)

    def is_valid(self, instance: 'Schema'):
        return self._implementation(instance)

    def get_validation_error(self, instance: 'Schema') -> typing.Optional[str]:
        if not self._implementation(instance):
            return self.format_message(instance)

    def validate(self, instance: 'Schema') -> None:
        if not self._implementation(instance):
            raise exceptions.SchemaValidationError(self.format_message(instance))


def validation(message: str, implementation: typing.Callable[['Schema'], bool] = None):
    """Decorator for schema validation methods."""
    if implementation:
        return SchemaValidation(message, implementation)
    else:
        return lambda implementation: SchemaValidation(message, implementation)


def default_attribute_preference(edge: elements.Edge, vertex: elements.Vertex) -> comparable.Comparable:
    return evidence.get_evidence_mean(edge) * evidence.get_evidence_mean(vertex)


AttributeType = typing.TypeVar('AttributeType', bound='Schema')
AttributePreference = typing.NewType('AttributePreference', typing.Callable[[elements.Edge, elements.Vertex],
                                                                            comparable.Comparable])
AttributeValidation = typing.NewType('AttributeValidation', typing.Callable[[elements.Edge, elements.Vertex], bool])


class AttributeDescriptor(typing.Generic[AttributeType]):

    def __init__(self, edge_label: str, schema_out_type: typing.Type[AttributeType], *, outbound: bool = True,
                 preference: AttributePreference = None, validation: AttributeValidation = None,
                 minimum_preference: comparable.Comparable = None):
        self._name = None
        self._edge_label = edge_label
        self._schema_out_type = schema_out_type
        self._outbound = outbound
        self._preference = preference or default_attribute_preference
        self._validation = validation
        self._minimum_preference = minimum_preference

    def __set_name__(self, owner, name):
        self._name = name

    def preference(self, preference: AttributePreference) -> AttributePreference:
        """Provide a preference function after the attribute has already been created. Can be used as a decorator."""
        assert self._preference is None
        self._preference = preference
        return preference

    def validation(self, validation: AttributeValidation) -> AttributeValidation:
        """Provide a validation function after the attribute has already been created. Can be used as a decorator."""
        assert self._validation is None
        self._validation = validation
        return validation

    def iter_choices(self, instance: 'Schema', *, validate: bool = True, preferences: bool = None) \
            -> typing.Iterator[typing.Tuple[elements.Edge, elements.Vertex, typing.Optional[comparable.Comparable]]]:
        if preferences is None:
            preferences = self._minimum_preference is not None
        edge_label = instance.db.get_label(self._edge_label)
        if edge_label is None:
            return iter(())
        if self._outbound:
            pair_iter = ((edge, edge.sink) for edge in instance.vertex.iter_outbound())
        else:
            pair_iter = ((edge, edge.source) for edge in instance.vertex.iter_inbound())
        if preferences:
            choice_iter = ((edge, vertex, self._preference(edge, vertex)) for edge, vertex in pair_iter)
        else:
            choice_iter = ((edge, vertex, None) for edge, vertex in pair_iter)
        if validate:
            choice_iter = (choice for choice in choice_iter
                           if (choice[0].label == edge_label and
                               self._schema_out_type(choice[1], instance.db, validate=False).is_valid))
            if self._validation:
                choice_iter = (choice for choice in choice_iter if self._validation(*choice[:2]))
            if self._minimum_preference is not None and preferences:
                choice_iter = (choice for choice in choice_iter if self._minimum_preference <= choice[2])
        return choice_iter

    def best_choice(self, instance: 'Schema', *, validate: bool = True) \
            -> typing.Optional[typing.Tuple[elements.Edge, elements.Vertex, comparable.Comparable]]:
        return min(self.iter_choices(instance, validate=validate, preferences=True),
                   key=lambda choice: choice[-1],
                   default=None)

    def sorted_choices(self, instance: 'Schema', *, validate: bool = True) \
            -> typing.List[typing.Tuple[elements.Edge, elements.Vertex, comparable.Comparable]]:
        return sorted(self.iter_choices(instance, validate=validate, preferences=True),
                      key=lambda choice: choice[2],
                      reverse=True)

    def __delete__(self, instance: 'Schema') -> None:
        for edge, _vertex, _none in self.iter_choices(instance):
            evidence.apply_evidence(edge, 0.0)


class SingularAttribute(typing.Generic[AttributeType]):

    def __init__(self, obj: 'Schema', descriptor: 'SingularAttributeDescriptor'):
        self._obj = obj
        self._descriptor = (descriptor,)  # Wrap it in a tuple to avoid triggering descriptor behavior

    @property
    def defined(self) -> bool:
        return self._descriptor[0].defined(self._obj)

    def __call__(self) -> AttributeType:
        return self._descriptor[0].get_value(self._obj)


class SingularAttributeDescriptor(AttributeDescriptor[AttributeType]):

    def __init__(self, edge_label: str, schema_out_type: typing.Type[AttributeType], *, outbound: bool = True,
                 preference: AttributePreference = None, validation: AttributeValidation = None,
                 minimum_preference: comparable.Comparable = None):
        super().__init__(edge_label, schema_out_type, outbound=outbound, preference=preference, validation=validation,
                         minimum_preference=minimum_preference)

    def defined(self, instance: 'Schema') -> bool:
        for _choice in self.iter_choices(instance):
            return True
        return False

    def get_value(self, instance: 'Schema') -> typing.Optional[AttributeType]:
        choice = self.best_choice(instance)
        if choice:
            vertex = choice[1]
            return self._schema_out_type(vertex)
        else:
            return None

    def __get__(self, instance, instance_class=None) -> SingularAttribute:
        return SingularAttribute(instance, self)

    def __set__(self, instance: 'Schema', value: 'Schema'):
        # If necessary, add an edge to the assigned value. Apply positive evidence towards it and negative evidence
        # toward any other (valid) values.
        selected_edge = None
        for edge, vertex, _none in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
            else:
                evidence.apply_evidence(edge, 0.0)
        if selected_edge is None:
            edge_label = instance.db.get_label(self._edge_label)
            assert edge_label is not None
            selected_edge = instance.vertex.add_edge(edge_label, value.vertex, self._outbound)
        evidence.apply_evidence(selected_edge, 1.0)


class PluralAttribute(typing.Generic[AttributeType]):

    def __init__(self, obj: 'Schema', descriptor: 'PluralAttributeDescriptor'):
        self._obj = obj
        self._descriptor = (descriptor,)  # Wrap it in a tuple to avoid triggering descriptor behavior

    @property
    def __len__(self) -> int:
        return self._descriptor[0].count(self._obj)

    def add(self, value: 'Schema') -> None:
        self._descriptor[0].add(self._obj, value)

    def remove(self, value: 'Schema') -> None:
        self._descriptor[0].remove(self._obj, value)

    def discard(self, value: 'Schema') -> None:
        self._descriptor[0].discard(self._obj, value)

    def __contains__(self, item: 'Schema') -> bool:
        return self._descriptor[0].contains(self._obj, item)

    def __call__(self) -> typing.Iterator[AttributeType]:
        return self._descriptor[0].iter_values(self._obj)


class PluralAttributeDescriptor(AttributeDescriptor[AttributeType]):

    def __init__(self, edge_label: str, schema_out_type: typing.Type[AttributeType], *, outbound: bool = True,
                 preference: AttributePreference = None, validation: AttributeValidation = None,
                 minimum_preference: comparable.Comparable = None):
        super().__init__(edge_label, schema_out_type, outbound=outbound, preference=preference, validation=validation,
                         minimum_preference=minimum_preference)

    def count(self, instance: 'Schema') -> int:
        return sum(1 for _choice in self.iter_choices(instance))

    def iter_values(self, instance: 'Schema') -> typing.Iterator[AttributeType]:
        for edge, vertex, _preference in self.iter_choices(instance):
            yield self._schema_out_type(vertex)

    def add(self, instance: 'Schema', value: 'Schema') -> None:
        # If necessary, add an edge to the assigned value. Apply positive evidence towards it. Ignore any other edges.
        selected_edge = None
        for edge, vertex, _none in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
                break
        if selected_edge is None:
            edge_label = instance.db.get_label(self._edge_label)
            assert edge_label is not None
            selected_edge = instance.vertex.add_edge(edge_label, value.vertex, self._outbound)
        evidence.apply_evidence(selected_edge, 1.0)

    def remove(self, instance: 'Schema', value: 'Schema') -> None:
        # If an edge to the value exists, apply negative evidence towards it, ignoring any other edges. If no such
        # (valid) edge exists, raise a KeyError.
        selected_edge = None
        for edge, vertex, _none in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
                break
        if selected_edge is None:
            raise KeyError(value)
        evidence.apply_evidence(selected_edge, 0.0)

    def discard(self, instance: 'Schema', value: 'Schema') -> None:
        # If necessary, add an edge to the assigned value. Apply negative evidence towards it. Ignore any other edges.
        selected_edge = None
        for edge, vertex, _preference in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
                break
        if selected_edge is None:
            edge_label = instance.db.get_label(self._edge_label)
            assert edge_label is not None
            selected_edge = instance.vertex.add_edge(edge_label, value.vertex, self._outbound)
        evidence.apply_evidence(selected_edge, 0.0)

    def contains(self, instance: 'Schema', value: 'Schema') -> bool:
        for edge, vertex, _preference in self.iter_choices(instance):
            if vertex == value.vertex:
                return True
        return False

    def __get__(self, instance: 'Schema', instance_class=None) -> PluralAttribute:
        return PluralAttribute(instance, self)


# See https://docs.python.org/3/howto/descriptor.html for how to define your own 'property' implementations.
def attribute(edge_label: str, schema: 'typing.Type[Schema]', *, outbound: bool = True, plural: bool = False,
              preference: AttributePreference = None, validation: AttributeValidation = None):
    if plural:
        return PluralAttributeDescriptor(edge_label, schema, outbound=outbound, preference=preference,
                                         validation=validation)
    else:
        return SingularAttributeDescriptor(edge_label, schema, outbound=outbound, preference=preference,
                                           validation=validation)


class Schema:

    __role_name__ = None

    @classmethod
    def role_name(cls) -> str:
        if cls.__role_name__ is None:
            # By default, we set the name to the all uppercase snake-case name, i.e. what we would use
            # for constants. For example, MyClassName would be converted to MY_CLASS_NAME.
            cls.__role_name__ = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).upper()
        return cls.__role_name__

    def __init__(self, vertex: elements.Vertex, db: 'graph_db_interface.GraphDBInterface', validate: bool = False):
        self._db = db
        self._vertex = vertex
        if validate:
            self.validate()

    @property
    def db(self) -> 'graph_db_interface.GraphDBInterface':
        return self._db

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
        return self._vertex.preferred_role == self._db.get_role(self.role_name())

    @property
    def vertex(self) -> elements.Vertex:
        return self._vertex
