"""
Shared functionality provided by both controllers and transactions.
"""

import contextlib
import itertools
import typing

import semantics.data_structs.element_data as element_data
import semantics.data_structs.interface as interface
import semantics.data_types.exceptions as exceptions
import semantics.data_types.indices as indices
import semantics.data_types.typedefs as typedefs

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class BaseController:
    """Base class for shared functionality in controller and transaction types."""

    def __init__(self, data: interface.DataInterface):
        self._data = data

    def new_reference_id(self) -> indices.ReferenceID:
        """Create a new reference ID, guaranteed to be unique."""
        return self._data.reference_id_allocator.new_id()

    def acquire_reference(self, reference_id: indices.ReferenceID, index: 'PersistentIDType'):
        """Acquire and hold an external reference to the element with the given index."""
        with self._data.registry_lock:
            assert reference_id not in self._data.held_references_union
            self._data.access(index).acquire_read()
            self._data.held_references.add(reference_id)

    def release_reference(self, reference_id: indices.ReferenceID, index: PersistentIDType):
        """Release a previously acquired external reference to the element with the given index."""
        with self._data.registry_lock:
            assert reference_id in self._data.held_references
            self._data.access(index).release_read()
            self._data.held_references.remove(reference_id)

    def add_role(self, name: str) -> indices.RoleID:
        """Add a new role with the given name, and return its index."""
        with self._data.add(indices.RoleID, name) as role_data:
            self._data.allocate_name(name, role_data.index)
        return role_data.index

    def remove_role(self, role_id: indices.RoleID) -> None:
        """Remove an existing role. The role must not be referenced by any vertex."""
        with self._data.remove(role_id) as role_data:
            role_data: element_data.RoleData
            self._data.deallocate_name(role_data.name, role_data.index)

    def get_role_name(self, role_id: indices.RoleID) -> str:
        """Get the name of an existing role."""
        with self._data.read(role_id) as role_data:
            role_data: element_data.RoleData
            return role_data.name

    def find_role(self, name: str) -> typing.Optional[indices.RoleID]:
        """Find the role with the given name and return its index. If no such role exists, return
        None."""
        with self._data.find(indices.RoleID, name) as role_data:
            if role_data is None:
                return None
            return role_data.index

    def add_vertex(self, preferred_role: indices.RoleID) -> indices.VertexID:
        """Add a new vertex with the given role. Return the new vertex's index."""
        with self._data.add(indices.VertexID, preferred_role) as vertex_data, \
                self._data.read(preferred_role):
            pass
        return vertex_data.index

    def remove_vertex(self, vertex_id: indices.VertexID, adjacent_edges: bool = False) -> None:
        """Remove an existing vertex. If the edge has adjacent edges, and adjacent_edges is False,
        raise an exception. Otherwise, remove the adjacent edges as well."""
        # If there are incident edges, and we can get write access to all of them and the other
        # vertices they connect to, we can go ahead with the removal, but we must remove the edges,
        # too.
        with contextlib.ExitStack() as context_stack:
            vertex_data = context_stack.enter_context(self._data.remove(vertex_id))
            assert isinstance(vertex_data, element_data.VertexData)
            if vertex_data.name is not None or vertex_data.time_stamp is not None:
                raise exceptions.ResourceUnavailableError(vertex_id)
            sources = []
            sinks = []
            if adjacent_edges:
                visited_edges = set()
                for edge_id in itertools.chain(vertex_data.outbound, vertex_data.inbound):
                    if edge_id in visited_edges:
                        # We can see the same edge twice if it's in both inbound and
                        # outbound -- a loop.
                        continue
                    visited_edges.add(edge_id)
                    edge_data = context_stack.enter_context(self._data.remove(edge_id))
                    assert isinstance(edge_data, element_data.EdgeData)
                    if edge_data.source == vertex_data.index:
                        # If it's a loop, we don't have to remove it from the sink's inbound, so
                        # skip it.
                        if edge_data.sink == vertex_data.index:
                            continue
                        adjacent = context_stack.enter_context(self._data.update(edge_data.sink))
                        sinks.append((edge_id, adjacent))
                    else:
                        assert edge_data.sink == vertex_data.index
                        adjacent = context_stack.enter_context(self._data.update(edge_data.source))
                        sources.append((edge_id, adjacent))
            else:
                if vertex_data.outbound or vertex_data.inbound:
                    raise exceptions.ResourceUnavailableError(vertex_id)
            for edge_id, sink in sinks:
                sink: element_data.VertexData
                sink.inbound.remove(edge_id)
            for edge_id, source in sources:
                source: element_data.VertexData
                source.outbound.remove(edge_id)

    def get_vertex_preferred_role(self, vertex_id: indices.VertexID) -> indices.RoleID:
        """Return the index of the role of an existing vertex."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            return vertex_data.preferred_role

    def get_vertex_name(self, vertex_id: indices.VertexID) -> typing.Optional[str]:
        """Return the name of an existing vertex. If the vertex is unnamed, return None."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            return vertex_data.name

    def set_vertex_name(self, vertex_id: indices.VertexID, name: str):
        """Set the name of an existing vertex. If the vertex is already named or the name is
        already assigned to another vertex, raise an exception."""
        with self._data.update(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            self._data.allocate_name(name, vertex_id)
            vertex_data.name = name

    def get_vertex_time_stamp(self, vertex_id: indices.VertexID) \
            -> typing.Optional[typedefs.TimeStamp]:
        """Return the time stamp of an existing vertex. If the vertex has no time stamp, return
        None."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            return vertex_data.time_stamp

    def set_vertex_time_stamp(self, vertex_id: indices.VertexID, time_stamp: typedefs.TimeStamp):
        """Set the time stamp of an existing vertex. If the vertex already has a time stamp, or
        the same time stamp is already assigned to another vertex, raise an exception."""
        with self._data.update(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            self._data.allocate_time_stamp(time_stamp, vertex_data.index)
            vertex_data.time_stamp = time_stamp

    def find_vertex(self, name: str) -> typing.Optional[indices.VertexID]:
        """Find the vertex with the given name and return its index. If no such vertex exists,
        return None."""
        with self._data.find(indices.VertexID, name) as vertex_data:
            if vertex_data is None:
                return None
            return vertex_data.index

    def count_vertex_outbound(self, vertex_id: indices.VertexID) -> int:
        """Return the number of outbound edges from an existing vertex."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            return len(vertex_data.outbound)

    def iter_vertex_outbound(self, vertex_id: indices.VertexID) -> typing.Iterator[indices.EdgeID]:
        """Return an iterator over the indices of the outbound edges from an existing vertex."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            yield from vertex_data.outbound

    def count_vertex_inbound(self, vertex_id: indices.VertexID) -> int:
        """Return the number of inbound edges to an existing vertex."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            return len(vertex_data.inbound)

    def iter_vertex_inbound(self, vertex_id: indices.VertexID) -> typing.Iterator[indices.EdgeID]:
        """Return an iterator over the indices of the inbound edges to an existing vertex."""
        with self._data.read(vertex_id) as vertex_data:
            vertex_data: element_data.VertexData
            yield from vertex_data.inbound

    def add_label(self, name: str) -> indices.LabelID:
        """Add a new label with the given name, and return its index."""
        with self._data.add(indices.LabelID, name) as label_data:
            self._data.allocate_name(name, label_data.index)
        return label_data.index

    def remove_label(self, label_id: indices.LabelID) -> None:
        """Remove an existing label. The role must not be referenced by any edge."""
        with self._data.remove(label_id) as label_data:
            label_data: element_data.LabelData
            self._data.deallocate_name(label_data.name, label_data.index)

    def get_label_name(self, label_id: indices.LabelID) -> str:
        """Get the name of an existing label."""
        with self._data.read(label_id) as label_data:
            label_data: element_data.LabelData
            return label_data.name

    def find_label(self, name: str) -> typing.Optional[indices.LabelID]:
        """Find the label with the given name and return its index. If no such label exists, return
        None."""
        with self._data.find(indices.LabelID, name) as label_data:
            if label_data is None:
                return None
            return label_data.index

    def add_edge(self, label_id: indices.LabelID, source_id: indices.VertexID,
                 sink_id: indices.VertexID) -> indices.EdgeID:
        """Add a new edge with the given label, source, and sink, and return its index."""
        with contextlib.ExitStack() as context_stack:
            edge_data = context_stack.enter_context(
                self._data.add(indices.EdgeID, label_id, source_id, sink_id)
            )
            context_stack.enter_context(self._data.read(label_id))
            source_data = context_stack.enter_context(self._data.update(source_id))
            assert isinstance(source_data, element_data.VertexData)
            if source_id == sink_id:
                # It's a loop. Don't try to acquire a second write lock to the same vertex.
                sink_data = source_data
            else:
                sink_data = context_stack.enter_context(self._data.update(sink_id))
                assert isinstance(sink_data, element_data.VertexData)
            for other_edge_id in source_data.outbound & sink_data.inbound:
                if self.get_edge_label(other_edge_id) == label_id:
                    # The edge already exists.
                    raise KeyError(other_edge_id)
            source_data.outbound.add(edge_data.index)
            sink_data.inbound.add(edge_data.index)
        return edge_data.index

    def remove_edge(self, edge_id: indices.EdgeID) -> None:
        """Remove an existing edge."""
        with self._data.remove(edge_id) as edge_data:
            edge_data: element_data.EdgeData
            with self._data.update(edge_data.source) as source:
                source: element_data.VertexData
                if edge_data.source == edge_data.sink:
                    # It's a loop. We shouldn't try to acquire it twice.
                    sink = source
                    assert edge_id in source.outbound
                    assert edge_id in sink.inbound
                    source.outbound.remove(edge_id)
                    sink.inbound.remove(edge_id)
                else:
                    with self._data.update(edge_data.sink) as sink:
                        sink: element_data.VertexData
                        assert edge_id in source.outbound
                        assert edge_id in sink.inbound
                        source.outbound.remove(edge_id)
                        sink.inbound.remove(edge_id)

    def get_edge_label(self, edge_id: indices.EdgeID) -> indices.LabelID:
        """Get the index of an edge's label."""
        with self._data.read(edge_id) as edge_data:
            edge_data: element_data.EdgeData
            return edge_data.label

    def get_edge_source(self, edge_id: indices.EdgeID) -> indices.VertexID:
        """Get the index of an edge's source vertex."""
        with self._data.read(edge_id) as edge_data:
            edge_data: element_data.EdgeData
            return edge_data.source

    def get_edge_sink(self, edge_id: indices.EdgeID) -> indices.VertexID:
        """Get the index of an edge's sink vertex."""
        with self._data.read(edge_id) as edge_data:
            edge_data: element_data.EdgeData
            return edge_data.sink

    def get_data_key(self, index: 'PersistentIDType', key: str, default=None) \
            -> typedefs.SimpleDataType:
        """Look up and return the key's value for the element. If the element has no value
        associated with the key, return the default."""
        with self._data.read(index) as owning_element_data:
            return owning_element_data.data.get(key, default)

    def set_data_key(self, index: 'PersistentIDType', key: str, value: typedefs.SimpleDataType):
        """Set the keys' value for the element. If the key already has a value for the element,
        overwrite it."""
        if value is None:
            self.clear_data_key(index, key)
        else:
            with self._data.update(index) as owning_element_data:
                owning_element_data.data[key] = value

    def clear_data_key(self, index: 'PersistentIDType', key: str) -> None:
        """If the key has a value for the element, remove it."""
        with self._data.update(index) as owning_element_data:
            if key in owning_element_data.data:
                del owning_element_data.data[key]

    def has_data_key(self, index: 'PersistentIDType', key: str) -> bool:
        """Return whether the key has a value for the element."""
        with self._data.read(index) as owning_element_data:
            return key in owning_element_data.data

    def iter_data_keys(self, index: 'PersistentIDType') -> typing.Iterator[str]:
        """Return an iterator over the keys that have values for the element."""
        with self._data.read(index) as owning_element_data:
            yield from owning_element_data.data

    def count_data_keys(self, index: 'PersistentIDType') -> int:
        """Return the number of keys that have values for the element."""
        with self._data.read(index) as owning_element_data:
            return len(owning_element_data.data)
