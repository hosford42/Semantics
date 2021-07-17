"""
Shared functionality of both the graph database and transactional connections to it.
"""

import abc
import typing

from semantics.data_control import controllers
import semantics.data_control.base as interface
from semantics.data_types import indices, typedefs
from semantics.graph_layer import elements


ElementType = typing.TypeVar('ElementType', bound=elements.Element)


class GraphDBInterface(metaclass=abc.ABCMeta):
    """The outward-facing, public interface shared by both the graph database and the transactional
    connections to it."""

    def __init__(self, controller: interface.BaseController = None):
        self._controller = controllers.Controller() if controller is None else controller

    def __repr__(self) -> str:
        return '%s%r' % (type(self).__name__, (self._controller,))

    def get_all_vertices(self) -> typing.Set[elements.Vertex]:
        return {elements.Vertex(self._controller, index)
                for index in self._controller.get_all_vertices()}

    def get_vertex(self, index: indices.VertexID) -> elements.Vertex:
        """Look up a vertex by index and return it. If no vertex with that index exists, raise an
        exception."""
        return elements.Vertex(self._controller, index)

    def add_vertex(self, preferred_role: elements.Role, *, audit: bool = False) -> elements.Vertex:
        """Add a new vertex to the database and return it."""
        vertex_id = self._controller.add_vertex(preferred_role.index, audit=audit)
        return self.get_vertex(vertex_id)

    def find_vertex(self, name: str) -> typing.Optional[elements.Vertex]:
        """Look up a vertex by name and return it. If no vertex by that name exists, return None."""
        vertex_id = self._controller.find_vertex(name)
        if vertex_id is None:
            return None
        return self.get_vertex(vertex_id)

    def get_edge(self, index: indices.EdgeID) -> elements.Edge:
        """Look up an existing edge by its index and return it. If no edge with that index exists,
        raise an exception."""
        return elements.Edge(self._controller, index)

    def add_edge(self, label: elements.Label, source: elements.Vertex, sink: elements.Vertex, *,
                 audit: bool = False) -> elements.Edge:
        """Add a new edge to the database and return it."""
        edge_id = self._controller.add_edge(label.index, source.index, sink.index, audit=audit)
        return self.get_edge(edge_id)

    def find_edge(self, label: elements.Label, source: elements.Vertex, sink: elements.Vertex) \
            -> typing.Optional[elements.Edge]:
        """If a matching edge exists in teh graph, return it."""
        edge_id = self._controller.find_edge(label.index, source.index, sink.index)
        if edge_id is None:
            return None
        return self.get_edge(edge_id)

    def get_label(self, name: str, add: bool = False,
                  transitive: bool = None) -> typing.Optional[elements.Label]:
        """Look up a label by name and return it. If no label by that name exists, and add is True,
        create a new label with that name and return it. Otherwise, return None."""
        label_id = self._controller.find_label(name)
        if label_id is None:
            if add:
                label_id = self._controller.add_label(name, transitive=bool(transitive))
            else:
                return None
        label = elements.Label(self._controller, label_id)
        assert transitive is None or label.transitive == transitive
        return label

    def get_role(self, name: str, add: bool = False) -> typing.Optional[elements.Role]:
        """Look up a role by name and return it. If no role by that name exists, and add is True,
        create a new role with that name and return it. Otherwise, return None."""
        role_id = self._controller.find_role(name)
        if role_id is None:
            if add:
                role_id = self._controller.add_role(name)
            else:
                return None
        return elements.Role(self._controller, role_id)

    def find_vertex_by_time_stamp(self, time_stamp: typedefs.TimeStamp, *, nearest: bool = False) \
            -> typing.Optional[elements.Vertex]:
        """Look up a vertex by time stamp and return it. If no vertex for that time stamp exists,
        return None."""
        vertex_id = self._controller.find_vertex_by_time_stamp(time_stamp, nearest=nearest)
        if vertex_id is None:
            return None
        return self.get_vertex(vertex_id)

    def get_audit(self, element_type: typing.Type[ElementType]) -> typing.List[ElementType]:
        """Return the audit entries for elements of the given type. Results are in a list ordered
        from oldest to youngest."""
        return [element_type(self._controller, index)
                for index in self._controller.get_audit_entries(element_type.index_type())]

    def get_audit_count(self, element_type: typing.Type[ElementType]) -> int:
        """Return the number of audit entries for the given element type."""
        return self._controller.get_audit_entry_count(element_type.index_type())

    def clear_audit(self, element_type: typing.Type[ElementType]) -> None:
        """Clear all audit entries for the given element type."""
        self._controller.clear_audit_entries(element_type.index_type())

    def pop_most_recently_audited(self, element_type: typing.Type[ElementType]) \
            -> typing.Optional[ElementType]:
        """Return the most recently audited element of the given type, removing it from the
        audit."""
        index = self._controller.pop_youngest_audit_entry(element_type.index_type())
        if index is None:
            return None
        return element_type(self._controller, index)

    def pop_least_recently_audited(self, element_type: typing.Type[ElementType]) \
            -> typing.Optional[ElementType]:
        """Return the most recently audited element of the given type, removing it from the
        audit."""
        index = self._controller.pop_oldest_audit_entry(element_type.index_type())
        if index is None:
            return None
        return element_type(self._controller, index)
