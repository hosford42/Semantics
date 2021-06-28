import abc
import typing

import semantics.data_control.controllers as controllers
import semantics.data_control.base as interface
import semantics.data_types.indices as indices
import semantics.graph_layer.elements as elements


class GraphDBInterface(metaclass=abc.ABCMeta):
    """The outward-facing, public interface of the graph database."""

    def __init__(self, controller: interface.BaseController = None):
        self._controller = controllers.Controller() if controller is None else controller

    def get_vertex(self, index: indices.VertexID) -> elements.Vertex:
        return elements.Vertex(self._controller, index)

    def add_vertex(self, preferred_role: elements.Role) -> elements.Vertex:
        vertex_id = self._controller.add_vertex(preferred_role.index)
        return self.get_vertex(vertex_id)

    def find_vertex(self, name: str) -> typing.Optional[elements.Vertex]:
        vertex_id = self._controller.find_vertex(name)
        if vertex_id is None:
            return None
        return self.get_vertex(vertex_id)

    def get_edge(self, index: indices.EdgeID) -> elements.Edge:
        return elements.Edge(self._controller, index)

    def add_edge(self, label: elements.Label, source: elements.Vertex,
                 sink: elements.Vertex) -> elements.Edge:
        edge_id = self._controller.add_edge(label.index, source.index, sink.index)
        return self.get_edge(edge_id)

    def get_label(self, name: str, add: bool = False) -> typing.Optional[elements.Label]:
        label_id = self._controller.find_label(name)
        if label_id is None:
            if add:
                label_id = self._controller.add_label(name)
            else:
                return None
        return elements.Label(self._controller, label_id)

    def get_role(self, name: str, add: bool = False) -> typing.Optional[elements.Role]:
        role_id = self._controller.find_role(name)
        if role_id is None:
            if add:
                role_id = self._controller.add_role(name)
            else:
                return None
        return elements.Role(self._controller, role_id)
