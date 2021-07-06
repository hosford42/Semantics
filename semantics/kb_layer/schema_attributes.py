"""
The attribute interface for schemas.
"""

import typing

from semantics.graph_layer import elements
from semantics.kb_layer import evidence
from semantics.data_types import comparable

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema


def default_attribute_preference(edge: elements.Edge, vertex: elements.Vertex) \
        -> comparable.Comparable:
    """The default attribute preference implementation. By default, we sort competing attribute
    values according to the evidence mean for the edge times the evidence mean for the other vertex.
    """
    # We take the square root so we have a natural rounding point of 0.5 when comparing against
    # a minimum preference threshold.
    return (evidence.get_evidence_mean(edge) * evidence.get_evidence_mean(vertex)) ** 0.5


AttributeType = typing.TypeVar('AttributeType', bound='Schema')
AttributePreference = typing.NewType('AttributePreference',
                                     typing.Callable[[elements.Edge, elements.Vertex],
                                                     comparable.Comparable])
AttributeValidation = typing.NewType('AttributeValidation',
                                     typing.Callable[[elements.Edge, elements.Vertex], bool])


class AttributeDescriptor(typing.Generic[AttributeType]):
    """
    Implements the descriptor protocol (like the @property decorator does) for schema attributes.
    """

    def __init__(self, edge_label: str, schema_out_type: typing.Type[AttributeType], *,
                 outbound: bool = True, preference: AttributePreference = None,
                 validation: AttributeValidation = None,
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
        """Provide a preference function after the attribute has already been created. Can be used
        as a decorator."""
        assert self._preference is None
        self._preference = preference
        return preference

    def validation(self, validation: AttributeValidation) -> AttributeValidation:
        """Provide a validation function after the attribute has already been created. Can be used
        as a decorator."""
        assert self._validation is None
        self._validation = validation
        return validation

    def iter_choices(self, instance: 'schema.Schema', *, validate: bool = True,
                     preferences: bool = None) \
            -> typing.Iterator[typing.Tuple[elements.Edge,
                                            elements.Vertex,
                                            typing.Optional[comparable.Comparable]]]:
        """Return an iterator over tuples of the form (edge, vertex, preference), where `edge`
        is the edge in the graph database connecting this schema instance's vertex to the other
        vertex, `vertex` is the other vertex the edge connects to, and `preference` is either
        None or a preference value depending on the value passed to the `preference` parameter.
        If validate is True (by default), only tuples that pass validation are yielded. Otherwise,
        all tuples are yielded. If the `preference` parameter is set to True or preference values
        are required in order to perform validation and validation is performed, then the preference
        values in the iterated tuples will be populated. Otherwise, they will be None.
        """
        if preferences is None:
            preferences = self._minimum_preference is not None
        edge_label = instance.database.get_label(self._edge_label)
        if edge_label is None:
            return iter(())
        if self._outbound:
            pair_iter = ((edge, edge.sink) for edge in instance.vertex.iter_outbound())
        else:
            pair_iter = ((edge, edge.source) for edge in instance.vertex.iter_inbound())
        if preferences:
            choice_iter = ((edge, vertex, self._preference(edge, vertex))
                           for edge, vertex in pair_iter)
        else:
            choice_iter = ((edge, vertex, None) for edge, vertex in pair_iter)
        if validate:
            choice_iter = (choice for choice in choice_iter
                           if (choice[0].label == edge_label and
                               self._schema_out_type(choice[1],
                                                     instance.database,
                                                     validate=False).is_valid))
            if self._validation:
                choice_iter = (choice for choice in choice_iter if self._validation(*choice[:2]))
            if self._minimum_preference is not None and preferences:
                choice_iter = (choice for choice in choice_iter
                               if self._minimum_preference <= choice[2])
        return choice_iter

    def best_choice(self, instance: 'schema.Schema', *, validate: bool = True) \
            -> typing.Optional[typing.Tuple[elements.Edge, elements.Vertex, comparable.Comparable]]:
        """Return the tuple (edge, vertex, preference) yielded by iter_choices that has the highest
        preference. If validate is True, tuples are filtered by validation before being compared.
        If there are no (valid) choices, returns None. If a tuple is returned, the preference value
        is always populated and is never None."""
        return max(self.iter_choices(instance, validate=validate, preferences=True),
                   key=lambda choice: choice[-1],
                   default=None)

    def sorted_choices(self, instance: 'schema.Schema', *, validate: bool = True) \
            -> typing.List[typing.Tuple[elements.Edge, elements.Vertex, comparable.Comparable]]:
        """Return a sorted list of the tuples (edge, vertex, preference) yielded by iter_choices
        in order of descending preference. If validate is True, tuples are filtered by validation
        before being compared. If there are no (valid) choices, returns an empty list. The
        preference value of each tuple is always populated and is never None."""
        return sorted(self.iter_choices(instance, validate=validate, preferences=True),
                      key=lambda choice: choice[2],
                      reverse=True)

    def clear(self, instance: 'schema.Schema') -> None:
        for edge, _vertex, _none in self.iter_choices(instance):
            evidence.apply_evidence(edge, 0.0)

    def __set__(self, instance, value):
        raise AttributeError("%s attribute cannot be assigned to." % self._name)

    def __del__(self):
        raise AttributeError("%s attribute cannot be deleted." % self._name)


class SingularAttribute(typing.Generic[AttributeType]):
    """An attribute that represents a single related value, rather than a collection of values."""

    def __init__(self, obj: 'schema.Schema', descriptor: 'SingularAttributeDescriptor'):
        self._obj = obj
        # Wrap it in a tuple to avoid triggering descriptor behavior
        self._descriptor = (descriptor,)

    @property
    def defined(self) -> bool:
        """Whether the attribute is defined, i.e., an associated value for it exists."""
        return self._descriptor[0].defined(self._obj)

    def get(self) -> AttributeType:
        return self._descriptor[0].get_value(self._obj)

    def set(self, value: AttributeType) -> None:
        self._descriptor[0].set_value(self._obj, value)

    def clear(self) -> None:
        self._descriptor[0].clear(self._obj)


class SingularAttributeDescriptor(AttributeDescriptor[AttributeType]):
    """
    Implements the descriptor protocol (like the @property decorator does) for singular schema
    attributes.
    """

    def defined(self, instance: 'schema.Schema') -> bool:
        """Return whether the singular attribute is defined for the given schema instance, i.e., an
        appropriate associated value for it exists in the knowledge base."""
        for _choice in self.iter_choices(instance):
            return True
        return False

    def get_value(self, instance: 'schema.Schema') -> typing.Optional[AttributeType]:
        """Return the singular attribute's associated value for this schema instance, if any. If
        the attribute is undefined, returns None."""
        choice = self.best_choice(instance)
        if choice:
            vertex = choice[1]
            return self._schema_out_type(vertex, instance.database)
        return None

    def set_value(self, instance: 'schema.Schema', value: AttributeType) -> None:
        # If necessary, add an edge to the assigned value. Apply positive evidence towards it and
        # negative evidence toward any other (valid) values.
        selected_edge = None
        for edge, vertex, _none in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
            else:
                evidence.apply_evidence(edge, 0.0)
        if selected_edge is None:
            edge_label = instance.database.get_label(self._edge_label)
            assert edge_label is not None, "Edge label %r does not exist" % self._edge_label
            selected_edge = instance.vertex.add_edge(edge_label, value.vertex,
                                                     outbound=self._outbound)
        evidence.apply_evidence(selected_edge, 1.0)

    def __get__(self, instance, instance_class=None) -> SingularAttribute:
        return SingularAttribute(instance, self)

    def __set__(self, instance, value):
        raise AttributeError("%s attribute cannot be assigned to. "
                             "Did you mean to use the set() method?" % self._name)

    # def __set__(self, instance: 'schema.Schema', value: 'schema.Schema'):
    #     # If necessary, add an edge to the assigned value. Apply positive evidence towards it and
    #     # negative evidence toward any other (valid) values.
    #     selected_edge = None
    #     for edge, vertex, _none in self.iter_choices(instance):
    #         if vertex == value.vertex:
    #             selected_edge = edge
    #         else:
    #             evidence.apply_evidence(edge, 0.0)
    #     if selected_edge is None:
    #         edge_label = instance.database.get_label(self._edge_label)
    #         assert edge_label is not None, "Edge label %r does not exist" % self._edge_label
    #         selected_edge = instance.vertex.add_edge(edge_label, value.vertex,
    #                                                  outbound=self._outbound)
    #     evidence.apply_evidence(selected_edge, 1.0)


class PluralAttribute(typing.Generic[AttributeType]):
    """An attribute that represents a collection of values related to a schema instance in a
    similar way, rather than a single value."""

    def __init__(self, obj: 'schema.Schema', descriptor: 'PluralAttributeDescriptor'):
        self._obj = obj
        # Wrap it in a tuple to avoid triggering descriptor behavior
        self._descriptor = (descriptor,)

    def __len__(self) -> int:
        return self._descriptor[0].count(self._obj)

    def __iter__(self) -> typing.Iterator[AttributeType]:
        return self._descriptor[0].iter_values(self._obj)

    def ascending(self) -> typing.List[AttributeType]:
        """Return the values of the collection in a list sorted by ascending preference."""
        return self._descriptor[0].sorted_values(self._obj, reverse=False)

    def descending(self) -> typing.List[AttributeType]:
        """Return the values of the collection in a list sorted by descending preference."""
        return self._descriptor[0].sorted_values(self._obj, reverse=True)

    def add(self, value: 'schema.Schema') -> None:
        """Add a new value to the collection."""
        self._descriptor[0].add(self._obj, value)

    def remove(self, value: 'schema.Schema') -> None:
        """Remove a value from the collection. Note that this updates evidence but does not remove
        the actual edge in the graph database."""
        self._descriptor[0].remove(self._obj, value)

    def discard(self, value: 'schema.Schema') -> None:
        """Discard a value from the collection. Note that this updates evidence but does not remove
        the actual edge in the graph database."""
        self._descriptor[0].discard(self._obj, value)

    def clear(self) -> None:
        """Remove all values from the collection. Note that this updates evidence but does not
        remove the actual edge in the graph database. Also, if there is sufficient pre-existing
        evidence in favor of a value being present, the newly added negative evidence won't be
        enough to cause the value to disappear from the collection."""
        self._descriptor[0].clear(self._obj)

    def __contains__(self, item: 'schema.Schema') -> bool:
        return self._descriptor[0].contains(self._obj, item)

    def evidence_map(self, *, validate: bool = True) \
            -> typing.Dict[AttributeType, typing.Tuple[evidence.Evidence, evidence.Evidence]]:
        """Return a mapping from each attribute to a tuple of the form
        (edge_evidence, vertex_evidence), where edge_evidence is an Evidence instance which
        represents the evidence for/against the attribute's edge, and vertex_evidence is an
        Evidence instance which represents the evidence for/against the attribute's vertex."""
        return self._descriptor[0].evidence_map(self._obj, validate=validate)

    # def __call__(self) -> typing.Iterator[AttributeType]:
    #     return self._descriptor[0].iter_values(self._obj)


class PluralAttributeDescriptor(AttributeDescriptor[AttributeType]):
    """
    Implements the descriptor protocol (like the @property decorator does) for plural schema
    attributes.
    """

    def count(self, instance: 'schema.Schema') -> int:
        """Return the number of associated values in the plural attribute's collection for this
        schema instance."""
        return sum(1 for _choice in self.iter_choices(instance))

    def iter_values(self, instance: 'schema.Schema') -> typing.Iterator[AttributeType]:
        """Returns an iterator over the associated values in the plural attribute's collection for
        this schema instance."""
        for _edge, vertex, _preference in self.iter_choices(instance):
            yield self._schema_out_type(vertex, instance.database)

    def evidence_map(self, instance: 'schema.Schema', *, validate: bool = True) \
            -> typing.Dict[AttributeType, typing.Tuple[evidence.Evidence, evidence.Evidence]]:
        """Return a mapping from each attribute to a tuple of the form
        (edge_evidence, vertex_evidence), where edge_evidence is an Evidence instance which
        represents the evidence for/against the attribute's edge, and vertex_evidence is an
        Evidence instance which represents the evidence for/against the attribute's vertex."""
        results = {}
        for edge, vertex, _preference in self.iter_choices(instance, validate=validate):
            value = self._schema_out_type(vertex, instance.database)
            results[value] = (evidence.get_evidence(edge), evidence.get_evidence(vertex))
        return results

    def sorted_values(self, instance: 'schema.Schema', *,
                      reverse: bool = False) -> typing.List[AttributeType]:
        choices = sorted(self.iter_choices(instance, preferences=True),
                         key=lambda triple: triple[-1], reverse=reverse)
        return [self._schema_out_type(vertex, instance.database)
                for _edge, vertex, _preference in choices]

    def add(self, instance: 'schema.Schema', value: 'schema.Schema') -> None:
        """Add a new value to the plural attribute's collection for this schema instance."""
        # If necessary, add an edge to the assigned value. Apply positive evidence towards it.
        # Ignore any other edges.
        selected_edge = None
        for edge, vertex, _none in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
                break
        if selected_edge is None:
            edge_label = instance.database.get_label(self._edge_label)
            assert edge_label is not None
            selected_edge = instance.vertex.add_edge(edge_label, value.vertex,
                                                     outbound=self._outbound)
        evidence.apply_evidence(selected_edge, 1.0)

    def remove(self, instance: 'schema.Schema', value: 'schema.Schema') -> None:
        """Remove a value from the plural attribute's collection for this schema instance. Note that
        this updates evidence but does not remove the actual edge in the graph database."""
        # If an edge to the value exists, apply negative evidence towards it, ignoring any other
        # edges. If no such (valid) edge exists, raise a KeyError.
        selected_edge = None
        for edge, vertex, _none in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
                break
        if selected_edge is None:
            raise KeyError(value)
        evidence.apply_evidence(selected_edge, 0.0)

    def discard(self, instance: 'schema.Schema', value: 'schema.Schema') -> None:
        """Discard a value from the plural attribute's collection for this schema instance. Note
        that this updates evidence but does not remove the actual edge in the graph database."""
        # If necessary, add an edge to the assigned value. Apply negative evidence towards it.
        # Ignore any other edges.
        selected_edge = None
        for edge, vertex, _preference in self.iter_choices(instance):
            if vertex == value.vertex:
                selected_edge = edge
                break
        if selected_edge is None:
            edge_label = instance.database.get_label(self._edge_label)
            assert edge_label is not None
            selected_edge = instance.vertex.add_edge(edge_label, value.vertex,
                                                     outbound=self._outbound)
        evidence.apply_evidence(selected_edge, 0.0)

    def contains(self, instance: 'schema.Schema', value: 'schema.Schema') -> bool:
        """Return whether the value is in the plural attribute's associated collection for this
        schema instance."""
        for _edge, vertex, _preference in self.iter_choices(instance):
            if vertex == value.vertex:
                return True
        return False

    def __get__(self, instance: 'schema.Schema', instance_class=None) -> PluralAttribute:
        return PluralAttribute(instance, self)


def attribute(edge_label: str, schema: 'typing.Type[schema.Schema]', *, outbound: bool = True,
              plural: bool = False, preference: AttributePreference = None,
              validation: AttributeValidation = None,
              minimum_preference: float = None) -> typing.Union[SingularAttribute, PluralAttribute]:
    """Create an property-like declaratively defined attribute for an ORM schema class.

    Usage:
        >>> from semantics.kb_layer.schema import Schema
        >>> class FooSchema(Schema):
        >>>     ...
        >>> class MySchema(Schema):
        >>>     foo = attribute('FOO_EDGE', FooSchema)
        >>> instance = MySchema(...)
        >>> instance.foo.get()
        FooSchema(...)
        >>>
    """
    # See https://docs.python.org/3/howto/descriptor.html for how to define your own 'property'
    # implementations.
    # NOTE: We have to disable the type checker here and have attribute() annotated with an
    #       incorrect type, or else the type checker will get the Schema subclass's attribute
    #       type checking all wrong. The type checker doesn't know how to handle other classes
    #       that implement the descriptor protocol besides the built-in `property`. Someday,
    #       they'll fix this issue and we can correct the type annotations.
    if plural:
        # noinspection PyTypeChecker
        return PluralAttributeDescriptor(edge_label, schema, outbound=outbound,
                                         preference=preference, validation=validation,
                                         minimum_preference=minimum_preference)
    # noinspection PyTypeChecker
    return SingularAttributeDescriptor(edge_label, schema, outbound=outbound,
                                       preference=preference, validation=validation,
                                       minimum_preference=minimum_preference)
