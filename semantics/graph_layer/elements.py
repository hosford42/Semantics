"""
Graph elements.

Graph elements are high-level interfaces that serve as index-based references to the underlying data
in the database. Multiple elements can refer to the same underlying data if they share the same
index; in this case, they will compare as equal to each other.
"""

import abc
import collections
import typing

from semantics.data_types import exceptions
from semantics.data_types import indices
from semantics.data_types import typedefs

if typing.TYPE_CHECKING:
    import semantics.data_control.base as interface


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


EdgePath = typing.Tuple[typing.Tuple[typing.Optional['Edge'], 'Vertex'], ...]


class Element(typing.Generic[PersistentIDType], abc.ABC):
    """Abstract base class for all graph element types."""

    @classmethod
    @abc.abstractmethod
    def index_type(cls) -> typing.Type[PersistentIDType]:
        """The type of index that elements of this type are associated with."""
        raise NotImplementedError()

    def __init__(self, controller: 'interface.BaseController', index: PersistentIDType):
        # Make sure these two attributes are defined from the start so __del__ can check them
        # safely.
        self._index = None
        self._released = True

        if not isinstance(index, self.index_type()):
            raise TypeError(index, self.index_type())

        self._reference_id = controller.new_reference_id()
        self._controller = controller

        self._controller.acquire_reference(self._reference_id, index)

        # Now that we have the lock, we can overwrite the temporary values for these attributes.
        self._index = index
        self._released = False

    def __del__(self):
        if self._index is not None:
            try:
                self.release()
            except (exceptions.ConnectionClosedError, KeyError):
                pass

    def __repr__(self) -> str:
        return '<%s#%s>' % (type(self).__name__, int(self._index))

    @property
    def index(self) -> PersistentIDType:
        """The index associated with this element."""
        return self._index

    @property
    def audit(self) -> bool:
        """Whether the element should be audited."""
        return self._controller.get_audit_flag(self._index)

    @audit.setter
    def audit(self, value: bool) -> None:
        """Whether the element should be audited."""
        if value:
            self._controller.set_audit_flag(self._index)
        else:
            self._controller.clear_audit_flag(self._index)

    def _validate(self) -> None:
        if self._released:
            raise exceptions.InvalidatedReferenceError(self)

    def copy(self) -> 'Element[PersistentIDType]':
        """Copies the reference, but not the element referred to."""
        self._validate()
        return type(self)(self._controller, self._index)

    def release(self):
        """Release the reference to the underlying data. This is automatically called when the
        element is garbage-collected or it is exited as a context manager, but you can call it
        earlier if you know you won't be needing it further. Note that once this is called, the
        element reference is invalidated; you will need to get a new reference to the element if
        you want to perform further operations on it."""
        if not self._released:
            self._controller.release_reference(self._reference_id, self._index)
            self._released = True

    @abc.abstractmethod
    def remove(self) -> None:
        """Remove the element from the database."""
        raise NotImplementedError()

    def get_data_key(self, key: str, default=None) -> typedefs.SimpleDataType:
        """Return the key's value for this element, or the default value if the key has no value."""
        self._validate()
        return self._controller.get_data_key(self._index, key, default)

    def set_data_key(self, key: str, value: typedefs.SimpleDataType):
        """Map the key to the value for this element."""
        self._validate()
        self._controller.set_data_key(self._index, key, value)

    def clear_data_key(self, key: str):
        """If the key has a value for this element, remove it."""
        self._validate()
        self._controller.clear_data_key(self._index, key)

    def has_data_key(self, key: str) -> bool:
        """Return whether the key has a value for this element."""
        self._validate()
        return self._controller.has_data_key(self._index, key)

    def iter_data_keys(self) -> typing.Iterator[str]:
        """Return an iterator over the keys that have values for this element."""
        self._validate()
        return self._controller.iter_data_keys(self._index)

    def count_data_keys(self) -> int:
        """Return the number of keys that have values for this element."""
        self._validate()
        return self._controller.count_data_keys(self._index)

    def __eq__(self, other: 'Element') -> bool:
        self._validate()
        return (type(self) is type(other) and
                self._index == other._index)

    def __ne__(self, other: 'Element') -> bool:
        self._validate()
        return not (type(self) is type(other) and
                    self._index == other._index)

    def __hash__(self) -> int:
        self._validate()
        return hash(type(self)) ^ (hash(self._index) << 3)

    def __enter__(self):
        self._validate()
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
        """The type of index that roles are associated with."""
        return indices.RoleID

    def __init__(self, controller: 'interface.BaseController', index: indices.RoleID):
        super().__init__(controller, index)

    @property
    def name(self) -> str:
        """The name of the role."""
        self._validate()
        return self._controller.get_role_name(self._index)

    def remove(self) -> None:
        self._validate()
        self._controller.remove_role(self._index)
        # We don't call self.release() because there's nothing left to release.
        self._released = True


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
        """The type of index that vertices are associated with."""
        return indices.VertexID

    def __init__(self, controller: 'interface.BaseController',
                 index: indices.VertexID):
        super().__init__(controller, index)

    @property
    def preferred_role(self) -> 'Role':
        """The role of the vertex."""
        self._validate()
        role_id = self._controller.get_vertex_preferred_role(self._index)
        return Role(self._controller, role_id)

    @property
    def name(self) -> typing.Optional[str]:
        """The name of the vertex, if any."""
        self._validate()
        return self._controller.get_vertex_name(self._index)

    @name.setter
    def name(self, value: str) -> None:
        """The name of the vertex, if any."""
        self._validate()
        self._controller.set_vertex_name(self._index, value)

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        """The time stamp of the vertex, if any."""
        self._validate()
        return self._controller.get_vertex_time_stamp(self._index)

    @time_stamp.setter
    def time_stamp(self, value: typedefs.TimeStamp) -> None:
        """The time stamp of the vertex, if any."""
        self._validate()
        self._controller.set_vertex_time_stamp(self._index, value)

    def remove(self) -> None:
        """Remove the vertex from the database."""
        self._validate()
        self._controller.remove_vertex(self._index)
        # We don't call self.release() because there's nothing left to release.
        self._released = True

    def count_outbound(self) -> int:
        """Return the number of outbound edges from the vertex."""
        self._validate()
        return self._controller.count_vertex_outbound(self._index)

    def iter_outbound(self) -> typing.Iterator['Edge']:
        """Return an iterator over the outbound edges from the vertex."""
        self._validate()
        for edge_id in self._controller.iter_vertex_outbound(self._index):
            yield Edge(self._controller, edge_id)

    def count_inbound(self) -> int:
        """Return the number of inbound edges to the vertex."""
        self._validate()
        return self._controller.count_vertex_inbound(self._index)

    def iter_inbound(self) -> typing.Iterator['Edge']:
        """Return an iterator over the inbound edges to the vertex."""
        self._validate()
        for edge_id in self._controller.iter_vertex_inbound(self._index):
            yield Edge(self._controller, edge_id)

    def iter_transitive_sinks(self, label: 'Label') -> typing.Iterator['Vertex']:
        """Return an iterator over all vertices reachable via a sequence of outbound edges
        of the given label."""
        self._validate()
        visited = set()
        to_visit = collections.deque(edge.sink for edge in self.iter_outbound()
                                     if edge.label == label)
        while to_visit:
            sink = to_visit.popleft()
            if sink in visited:
                continue
            yield sink
            visited.add(sink)
            to_visit.extend(edge.sink for edge in sink.iter_outbound()
                            if edge.label == label and edge.sink not in visited)

    def iter_transitive_sources(self, label: 'Label') -> typing.Iterator['Vertex']:
        """Return an iterator over all vertices reachable via a sequence of inbound edges
        of the given label."""
        self._validate()
        visited = set()
        to_visit = collections.deque(edge.source for edge in self.iter_inbound()
                                     if edge.label == label)
        while to_visit:
            sink = to_visit.popleft()
            if sink in visited:
                continue
            yield sink
            visited.add(sink)
            to_visit.extend(edge.source for edge in sink.iter_inbound()
                            if edge.label == label and edge.source not in visited)

    def iter_transitive_neighbors(self, label: 'Label', *, outbound: bool) \
            -> typing.Iterator['Vertex']:
        if outbound:
            return self.iter_transitive_sinks(label)
        else:
            return self.iter_transitive_sources(label)

    def get_shortest_transitive_path(self, label: 'Label', sink: 'Vertex', *,
                                     outbound: bool = True) -> typing.Optional[EdgePath]:
        for path in self.iter_transitive_shortest_paths(label, outbound=outbound):
            terminator = path[-1][-1]
            if terminator == sink:
                return path
        return None

    def iter_transitive_shortest_paths(self, label: 'Label', *,
                                       outbound: bool = True) -> typing.Iterator[EdgePath]:
        self._validate()
        visited = set()
        if outbound:
            def get_other_vertex(edge):
                return edge.sink
            get_edges = Vertex.iter_outbound
        else:
            def get_other_vertex(edge):
                return edge.source
            get_edges = Vertex.iter_inbound
        pending: typing.Deque[EdgePath] = collections.deque(((None, edge.source),)
                                                            for edge in get_edges(self)
                                                            if edge.label == label)
        while pending:
            path = pending.popleft()
            terminator = path[-1][-1]
            if terminator in visited:
                continue
            yield path
            visited.add(terminator)
            for edge in get_edges(terminator):
                if edge.label != label:
                    continue
                other = get_other_vertex(edge)
                if other in visited:
                    continue
                new_path = path + ((edge, other),)
                pending.append(new_path)

    def add_edge_to(self, edge_label: 'Label', sink: 'Vertex') -> 'Edge':
        """Add an outbound edge to another vertex."""
        self._validate()
        return Edge(self._controller,
                    self._controller.add_edge(edge_label.index, self._index, sink.index))

    def add_edge_from(self, edge_label: 'Label', source: 'Vertex') -> 'Edge':
        """Add an inbound edge from another vertex."""
        self._validate()
        return Edge(self._controller,
                    self._controller.add_edge(edge_label.index, source.index, self._index))

    def add_edge(self, edge_label: 'Label', other: 'Vertex', *, outbound: bool) -> 'Edge':
        """Add an edge to/from another vertex. If outbound is True, the added edge will be an
        outbound edge to the other vertex. Otherwise, the added edge will be an inbound edge from
        the other vertex."""
        self._validate()
        if outbound:
            return self.add_edge_to(edge_label, other)
        return self.add_edge_from(edge_label, other)

    def get_edge_to(self, edge_label: 'Label', sink: 'Vertex') -> typing.Optional['Edge']:
        """Get an outbound edge to another vertex. If the edge doesn't exist, returns None."""
        self._validate()
        edge_id = self._controller.find_edge(edge_label.index, self._index, sink.index)
        if edge_id is None:
            return None
        return Edge(self._controller, edge_id)

    def get_edge_from(self, edge_label: 'Label', source: 'Vertex') -> typing.Optional['Edge']:
        """Get an inbound edge from another vertex. If the edge doesn't exist, returns None."""
        self._validate()
        edge_id = self._controller.find_edge(edge_label.index, source.index, self._index)
        if edge_id is None:
            return None
        return Edge(self._controller, edge_id)

    def get_edge(self, edge_label: 'Label', other: 'Vertex', *,
                 outbound: bool) -> typing.Optional['Edge']:
        """Find an edge to/from another vertex. If outbound is True, the edge will be an outbound
        edge to the other vertex. Otherwise, the edge will be an inbound edge from the other vertex.
        If no such edge can be found, return None."""
        self._validate()
        if outbound:
            return self.get_edge_to(edge_label, other)
        return self.get_edge_from(edge_label, other)


class Label(Element[indices.LabelID]):
    """Labels are GraphElements that serve as a sort of indicator for the expected behavior and
    usage of each Edge.

    LabelID is the index type, used to uniquely identify which Label is referred to. LabelData is an
    internally used data class for the attributes of the Label. A Label instance is an *indirect
    reference* to the LabelData, via the LabelID, and serves as the externally accessible interface.
    Multiple Label instances can refer to the same LabelData if they have the same LabelID."""

    @classmethod
    def index_type(cls) -> typing.Type[indices.LabelID]:
        """The type of index that labels are associated with."""
        return indices.LabelID

    def __init__(self, controller: 'interface.BaseController', index: indices.LabelID):
        super().__init__(controller, index)

    def __repr__(self):
        return '<Label#%s(%s)>' % (int(self.index), self.name)

    @property
    def name(self) -> str:
        """The name of the label."""
        self._validate()
        return self._controller.get_label_name(self._index)

    @property
    def transitive(self) -> bool:
        """Whether edges with this label are transitive."""
        self._validate()
        return self._controller.get_label_transitivity(self._index)

    def remove(self) -> None:
        """Remove the label from the database."""
        self._validate()
        self._controller.remove_label(self._index)
        # We don't call self.release() because there's nothing left to release.
        self._released = True


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
        """The type of index that edges are associated with."""
        return indices.EdgeID

    def __init__(self, controller: 'interface.BaseController', index: indices.EdgeID):
        super().__init__(controller, index)

    def __repr__(self):
        return '<Edge#%s(%s%s:%s)>' % (int(self.index), self.source, self.label.name, self.sink)

    @property
    def label(self) -> 'Label':
        """The label of the edge."""
        self._validate()
        label_id = self._controller.get_edge_label(self._index)
        return Label(self._controller, label_id)

    @property
    def source(self) -> 'Vertex':
        """The source (origin) vertex of the edge. (All edges are directed.)"""
        self._validate()
        vertex_id = self._controller.get_edge_source(self._index)
        return Vertex(self._controller, vertex_id)

    @property
    def sink(self) -> 'Vertex':
        """The sink (destination) vertex of the edge. (All edges are directed.)"""
        self._validate()
        vertex_id = self._controller.get_edge_sink(self._index)
        return Vertex(self._controller, vertex_id)

    def remove(self) -> None:
        """Remove the edge from the database."""
        self._validate()
        self._controller.remove_edge(self._index)
        # We don't call self.release() because there's nothing left to release.
        self._released = True
