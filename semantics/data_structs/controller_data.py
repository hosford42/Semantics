"""
Internal state of the controller.
"""

import threading
import typing

import semantics.data_structs.interface as interface
import semantics.data_types.allocators as allocators
import semantics.data_types.indices as indices
import semantics.data_types.typedefs as typedefs

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class ControllerData(interface.DataInterface):
    """The internal data of the Controller. Only basic data structures and accessors should appear
    in this class. Controller behavior should be determined entirely in the Controller class."""

    __NON_PERSISTENT_ATTRIBUTES = (
        'held_references',
        'registry_lock',
    )

    def __init__(self):
        self.controller_data = None

        self.reference_id_allocator = allocators.IndexAllocator(indices.ReferenceID)

        self.id_allocator_map = {
            indices.RoleID: allocators.IndexAllocator(indices.RoleID),
            indices.VertexID: allocators.IndexAllocator(indices.VertexID),
            indices.LabelID: allocators.IndexAllocator(indices.LabelID),
            indices.EdgeID: allocators.IndexAllocator(indices.EdgeID),
        }

        self.name_allocator_map = {
            indices.RoleID: allocators.MapAllocator(str, indices.RoleID),
            indices.VertexID: allocators.MapAllocator(str, indices.VertexID),
            indices.LabelID: allocators.MapAllocator(str, indices.LabelID),
            # Edges are never named, so no name allocator is required.
        }

        self.vertex_time_stamp_allocator = allocators.MapAllocator(typedefs.TimeStamp,
                                                                   indices.VertexID)

        self.held_references = set()
        self.held_references_union = self.held_references

        self.registry_map = {
            indices.RoleID: {},
            indices.VertexID: {},
            indices.LabelID: {},
            indices.EdgeID: {}
        }
        self.registry_stack_map = self.registry_map
        self.pending_deletion_map = None

        self.name_allocator_stack_map = self.name_allocator_map
        self.pending_name_deletion_map = None

        # Protects object creation, deletion, and reference count changes
        self.registry_lock = threading.Lock()

    def __getstate__(self):
        state = self.__dict__.copy()
        for name in self.__NON_PERSISTENT_ATTRIBUTES:
            del state[name]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.held_references = set()
        self.registry_lock = threading.Lock()

    def allocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Allocate a new name for the index."""
        allocator = self.name_allocator_map[type(index)]
        allocator.allocate(name, index)

    def deallocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Deallocate the name from the index."""
        allocator = self.name_allocator_map[type(index)]
        assert allocator.get_index(name) == index
        allocator.deallocate(name)

    def allocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID) \
            -> None:
        """Allocate a new time stamp for the vertex index."""
        self.vertex_time_stamp_allocator.allocate(time_stamp, vertex_id)
