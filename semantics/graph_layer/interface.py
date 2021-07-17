"""
Shared functionality of both the graph database and transactional connections to it.
"""

import abc
import typing

from semantics.data_control import controllers
import semantics.data_control.base as interface
from semantics.data_types import indices, typedefs
from semantics.graph_layer import elements


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

    def add_vertex(self, preferred_role: elements.Role) -> elements.Vertex:
        """Add a new vertex to the database and return it."""
        vertex_id = self._controller.add_vertex(preferred_role.index)
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

    def add_edge(self, label: elements.Label, source: elements.Vertex,
                 sink: elements.Vertex) -> elements.Edge:
        """Add a new edge to the database and return it."""
        edge_id = self._controller.add_edge(label.index, source.index, sink.index)
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

    def get_vertex_audit(self) -> typing.List[elements.Vertex]:
        """Return the audit entries for vertices in a list ordered from oldest to youngest."""
        return [elements.Vertex(self._controller, index)
                for index in self._controller.get_audit_entries(indices.VertexID)]

    def get_edge_audit(self) -> typing.List[elements.Edge]:
        """Return the audit entries for edges in a list ordered from oldest to youngest."""
        return [elements.Edge(self._controller, index)
                for index in self._controller.get_audit_entries(indices.EdgeID)]

    def get_role_audit(self) -> typing.List[elements.Role]:
        """Return the audit entries for roles in a list ordered from oldest to youngest."""
        return [elements.Role(self._controller, index)
                for index in self._controller.get_audit_entries(indices.RoleID)]

    def get_label_audit(self) -> typing.List[elements.Label]:
        """Return the audit entries for labels in a list ordered from oldest to youngest."""
        return [elements.Label(self._controller, index)
                for index in self._controller.get_audit_entries(indices.LabelID)]

    def get_vertex_audit_count(self) -> int:
        """Return the number of vertex audit entries."""
        return self._controller.get_audit_entry_count(indices.VertexID)

    def get_edge_audit_count(self) -> int:
        """Return the number of edge audit entries."""
        return self._controller.get_audit_entry_count(indices.EdgeID)

    def get_role_audit_count(self) -> int:
        """Return the number of role audit entries."""
        return self._controller.get_audit_entry_count(indices.RoleID)

    def get_label_audit_count(self) -> int:
        """Return the number of label audit entries."""
        return self._controller.get_audit_entry_count(indices.LabelID)

    def clear_vertex_audit(self) -> None:
        """Clear all vertex audit entries."""
        self._controller.clear_audit_entries(indices.VertexID)

    def clear_edge_audit(self) -> None:
        """Clear all edge audit entries."""
        self._controller.clear_audit_entries(indices.EdgeID)

    def clear_role_audit(self) -> None:
        """Clear all role audit entries."""
        self._controller.clear_audit_entries(indices.RoleID)

    def clear_label_audit(self) -> None:
        """Clear all label audit entries."""
        self._controller.clear_audit_entries(indices.LabelID)

    def pop_most_recently_audited_vertex(self) -> typing.Optional[elements.Vertex]:
        """Return the most recently audited vertex, removing it from the audit."""
        index = self._controller.pop_youngest_audit_entry(indices.VertexID)
        if index is None:
            return None
        return elements.Vertex(self._controller, index)

    def pop_most_recently_audited_edge(self) -> typing.Optional[elements.Edge]:
        """Return the most recently audited edge, removing it from the audit."""
        index = self._controller.pop_youngest_audit_entry(indices.EdgeID)
        if index is None:
            return None
        return elements.Edge(self._controller, index)

    def pop_most_recently_audited_role(self) -> typing.Optional[elements.Role]:
        """Return the most recently audited role, removing it from the audit."""
        index = self._controller.pop_youngest_audit_entry(indices.RoleID)
        if index is None:
            return None
        return elements.Role(self._controller, index)

    def pop_most_recently_audited_label(self) -> typing.Optional[elements.Label]:
        """Return the most recently audited label, removing it from the audit."""
        index = self._controller.pop_youngest_audit_entry(indices.LabelID)
        if index is None:
            return None
        return elements.Label(self._controller, index)

    def pop_least_recently_audited_vertex(self) -> typing.Optional[elements.Vertex]:
        """Return the most recently audited vertex, removing it from the audit."""
        index = self._controller.pop_oldest_audit_entry(indices.VertexID)
        if index is None:
            return None
        return elements.Vertex(self._controller, index)

    def pop_least_recently_audited_edge(self) -> typing.Optional[elements.Edge]:
        """Return the most recently audited edge, removing it from the audit."""
        index = self._controller.pop_oldest_audit_entry(indices.EdgeID)
        if index is None:
            return None
        return elements.Edge(self._controller, index)

    def pop_least_recently_audited_role(self) -> typing.Optional[elements.Role]:
        """Return the most recently audited role, removing it from the audit."""
        index = self._controller.pop_oldest_audit_entry(indices.RoleID)
        if index is None:
            return None
        return elements.Role(self._controller, index)

    def pop_least_recently_audited_label(self) -> typing.Optional[elements.Label]:
        """Return the most recently audited label, removing it from the audit."""
        index = self._controller.pop_oldest_audit_entry(indices.LabelID)
        if index is None:
            return None
        return elements.Label(self._controller, index)
