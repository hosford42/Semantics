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

    def get_label(self, name: str, add: bool = False) -> typing.Optional[elements.Label]:
        """Look up a label by name and return it. If no label by that name exists, and add is True,
        create a new label with that name and return it. Otherwise, return None."""
        label_id = self._controller.find_label(name)
        if label_id is None:
            if add:
                label_id = self._controller.add_label(name)
            else:
                return None
        return elements.Label(self._controller, label_id)

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

    def find_vertex_by_time_stamp(self, time_stamp: typedefs.TimeStamp) \
            -> typing.Optional[elements.Vertex]:
        """Look up a vertex by time stamp and return it. If no vertex for that time stamp exists,
        return None."""
        vertex_id = self._controller.find_vertex_by_time_stamp(time_stamp)
        if vertex_id is None:
            return None
        return self.get_vertex(vertex_id)
