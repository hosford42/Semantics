import abc
import typing

import semantics.data_types.exceptions as exceptions
import semantics.data_types.indices as indices
import semantics.data_types.typedefs as typedefs

if typing.TYPE_CHECKING:
    import semantics.data_control.base as interface


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Element(typing.Generic[PersistentIDType]):

    @classmethod
    @abc.abstractmethod
    def index_type(cls) -> typing.Type[PersistentIDType]:
        raise NotImplementedError()

    def __init__(self, controller: 'interface.BaseController', index: PersistentIDType):
        if not isinstance(index, self.index_type()):
            raise TypeError(index, self.index_type())
        self._reference_id = controller.new_reference_id()
        self._controller = controller
        self._index = index

        # Set self._released to True temporarily in case of an exception while acquiring the
        # reference, since __del__ will still be called.
        self._released = True
        self._controller.acquire_reference(self._reference_id, index)
        self._released = False

    def __del__(self):
        if hasattr(self, '_index') and not getattr(self, '_released', False):
            self._controller.release_reference(self._reference_id, self._index)

    @property
    def index(self) -> PersistentIDType:
        return self._index

    def copy(self) -> 'Element[PersistentIDType]':
        """Copies the reference, but not the element referred to."""
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return type(self)(self._controller, self._index)

    def release(self):
        if not self._released:
            self._controller.release_reference(self._reference_id, self._index)
            self._released = True

    @abc.abstractmethod
    def remove(self) -> None:
        raise NotImplementedError()

    def get_data_key(self, key: str, default=None) -> typedefs.SimpleDataType:
        return self._controller.get_data_key(self._index, key, default)

    def set_data_key(self, key: str, value: typedefs.SimpleDataType):
        self._controller.set_data_key(self._index, key, value)

    def clear_data_key(self, key: str):
        self._controller.clear_data_key(self._index, key)

    def has_data_key(self, key: str) -> bool:
        return self._controller.has_data_key(self._index, key)

    def iter_data_keys(self) -> typing.Iterator[str]:
        return self._controller.iter_data_keys(self._index)

    def count_data_keys(self) -> int:
        return self._controller.count_data_keys(self._index)

    def __eq__(self, other: 'Element') -> bool:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return (type(self) is type(other) and
                self._controller is other._controller and
                self._index == other._index)

    def __ne__(self, other: 'Element') -> bool:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return not (type(self) is type(other) and
                    self._controller is other._controller and
                    self._index == other._index)

    def __enter__(self):
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class Role(Element[indices.RoleID]):
    """Roles are GraphElements that serve as a sort of indicator for the expected behavior and usage
    of each Vertex.

    RoleID is the index type, used to uniquely identify which Role is referred to. RoleData is an
    internally used data class for the attributes of the Role. Role is an *indirect reference* to
    the RoleData, via the RoleID, and serves as the externally accessible interface. Multiple Role
    instances can refer to the same RoleData if they have the same RoleID."""

    @classmethod
    def index_type(cls) -> typing.Type[indices.RoleID]:
        return indices.RoleID

    def __init__(self, controller: 'interface.BaseController', index: indices.RoleID):
        super().__init__(controller, index)

    @property
    def name(self) -> str:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self._controller.get_role_name(self._index)

    def remove(self) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        self._controller.remove_role(self._index)
        self.release()


class Vertex(Element[indices.VertexID]):
    """Vertices are GraphElements that can be linked to each other via Edges. Vertices know which
    Edges are inbound and which are outbound. Each Vertex always has an associated Role, which acts
    as a sort of indicator for the expected behavior and usage of the Vertex. A Vertex's Role can
    never be changed once the Vertex is created.

    VertexID is the index type, used to uniquely identify which Vertex is referred to. VertexData is
    an internally used data class for the attributes of the Vertex. Vertex is an *indirect
    reference* to the VertexData, via the VertexID, and serves as the externally accessible
    interface. Multiple Vertex instances can refer to the same VertexData if they have the same
    VertexID."""

    @classmethod
    def index_type(cls) -> typing.Type[indices.VertexID]:
        return indices.VertexID

    def __init__(self, controller: 'interface.BaseController',
                 index: indices.VertexID):
        super().__init__(controller, index)

    @property
    def preferred_role(self) -> 'Role':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        role_id = self._controller.get_vertex_preferred_role(self._index)
        return Role(self._controller, role_id)

    @property
    def name(self) -> typing.Optional[str]:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self._controller.get_vertex_name(self._index)

    @name.setter
    def name(self, value: str) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        self._controller.set_vertex_name(self._index, value)

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self._controller.get_vertex_time_stamp(self._index)

    @time_stamp.setter
    def time_stamp(self, value: typedefs.TimeStamp) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        self._controller.set_vertex_time_stamp(self._index, value)

    def remove(self) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        self._controller.remove_vertex(self._index)
        self.release()

    def count_outbound(self) -> int:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self._controller.count_vertex_outbound(self._index)

    def iter_outbound(self) -> typing.Iterator['Edge']:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        for edge_id in self._controller.iter_vertex_outbound(self._index):
            yield Edge(self._controller, edge_id)

    def count_inbound(self) -> int:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self._controller.count_vertex_inbound(self._index)

    def iter_inbound(self) -> typing.Iterator['Edge']:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        for edge_id in self._controller.iter_vertex_inbound(self._index):
            yield Edge(self._controller, edge_id)

    def add_edge_to(self, edge_label: 'Label', sink: 'Vertex') -> 'Edge':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return Edge(self._controller,
                    self._controller.add_edge(edge_label.index, self._index, sink.index))

    def add_edge_from(self, edge_label: 'Label', source: 'Vertex') -> 'Edge':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return Edge(self._controller,
                    self._controller.add_edge(edge_label.index, source.index, self._index))

    def add_edge(self, edge_label: 'Label', other: 'Vertex', outbound: bool) -> 'Edge':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        if outbound:
            return self.add_edge_to(edge_label, other)
        return self.add_edge_from(edge_label, other)


class Label(Element[indices.LabelID]):
    """Labels are GraphElements that serve as a sort of indicator for the expected behavior and
    usage of each Edge.

    LabelID is the index type, used to uniquely identify which Label is referred to. LabelData is an
    internally used data class for the attributes of the Label. A Label instance is an *indirect
    reference* to the LabelData, via the LabelID, and serves as the externally accessible interface.
    Multiple Label instances can refer to the same LabelData if they have the same LabelID."""

    @classmethod
    def index_type(cls) -> typing.Type[indices.LabelID]:
        return indices.LabelID

    def __init__(self, controller: 'interface.BaseController', index: indices.LabelID):
        super().__init__(controller, index)

    @property
    def name(self) -> str:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        return self._controller.get_label_name(self._index)

    def remove(self) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        self._controller.remove_label(self._index)
        self.release()


class Edge(Element[indices.EdgeID]):
    """Edges are GraphElements that link two Vertices together. Edges are always directed. Each Edge
    always has an associated Label, which acts as a sort of indicator for the expected behavior and
    usage of the Edge. An Edge's Label can never be changed once the Edge is created.

    EdgeID is the index type, used to uniquely identify which Edge is referred to. EdgeData is an
    internally used data class for the attributes of the Edge. Edge is an *indirect reference* to
    the EdgeData, via the EdgeID, and serves as the externally accessible interface. Multiple Edge
    instances can refer to the same EdgeData if they have the same EdgeID."""

    @classmethod
    def index_type(cls) -> typing.Type[indices.EdgeID]:
        return indices.EdgeID

    def __init__(self, controller: 'interface.BaseController', index: indices.EdgeID):
        super().__init__(controller, index)

    @property
    def label(self) -> 'Label':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        label_id = self._controller.get_edge_label(self._index)
        return Label(self._controller, label_id)

    @property
    def source(self) -> 'Vertex':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        vertex_id = self._controller.get_edge_source(self._index)
        return Vertex(self._controller, vertex_id)

    @property
    def sink(self) -> 'Vertex':
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        vertex_id = self._controller.get_edge_sink(self._index)
        return Vertex(self._controller, vertex_id)

    def remove(self) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)
        self._controller.remove_edge(self._index)
        self.release()
