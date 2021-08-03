"""
Internal state of the controller.
"""

import threading
import typing

from semantics.data_structs import interface
from semantics.data_types import allocators
from semantics.data_types import data_access
from semantics.data_types import indices

if typing.TYPE_CHECKING:
    from semantics.data_types import data_access


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class ControllerData(interface.DataInterface[None, data_access.ControllerThreadAccessManager]):
    """The internal data of the Controller. Only basic data structures and accessors should appear
    in this class. Controller behavior should be determined entirely in the Controller class."""

    __NON_PERSISTENT_ATTRIBUTES = (
        'held_references',
        'held_references_union',
        'registry_lock',
    )

    def __init__(self):
        super().__init__()

        self.controller_data = None

        self.reference_id_allocator = allocators.IndexAllocator(indices.ReferenceID)

        self.id_allocator_map = {
            indices.RoleID: allocators.IndexAllocator(indices.RoleID),
            indices.VertexID: allocators.IndexAllocator(indices.VertexID),
            indices.LabelID: allocators.IndexAllocator(indices.LabelID),
            indices.EdgeID: allocators.IndexAllocator(indices.EdgeID),
            indices.CatalogID: allocators.IndexAllocator(indices.CatalogID),
        }

        self.held_references = {}
        self.held_references_union = self.held_references.keys()

        self.registry_map = {
            indices.RoleID: {},
            indices.VertexID: {},
            indices.LabelID: {},
            indices.EdgeID: {},
            indices.CatalogID: {},
        }
        self.registry_stack_map = self.registry_map
        self.pending_deletion_map = None
        self.pending_name_deletion_map = None

        self.name_allocator_map = {
            indices.RoleID: allocators.MapAllocator(str, indices.RoleID),
            indices.LabelID: allocators.MapAllocator(str, indices.LabelID),
            indices.CatalogID: allocators.MapAllocator(str, indices.CatalogID),
        }
        self.name_allocator_stack_map = self.name_allocator_map

        self.catalog_allocator_map = {}
        self.catalog_allocator_stack_map = self.catalog_allocator_map

        # Protects object creation, deletion, and reference count changes
        self.registry_lock = threading.Lock()

    def __getstate__(self):
        state = self.__dict__.copy()
        for name in self.__NON_PERSISTENT_ATTRIBUTES:
            del state[name]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.held_references = {}
        self.held_references_union = self.held_references.keys()
        self.registry_lock = threading.Lock()

    def access(self, index: 'PersistentIDType') -> 'data_access.ThreadAccessManagerInterface':
        """Return the thread access manager with the given index. Raise a KeyError if
        no data is associated with the index.

        Note: The registry lock must be held while calling this method.
        """
        assert self.registry_lock.locked()
        return self.access_map[type(index)][index]

    def new_access(self, index: 'PersistentIDType') -> data_access.ControllerThreadAccessManager:
        return data_access.ControllerThreadAccessManager(index)

    def allocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Allocate a new name for the index."""
        allocator = self.name_allocator_map[type(index)]
        allocator.allocate(name, index)

    def deallocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Deallocate the name from the index."""
        allocator = self.name_allocator_map[type(index)]
        assert allocator.get_index(name) == index
        allocator.deallocate(name)

    def allocate_catalog_key(self, catalog_id: 'indices.CatalogID', key: typing.Hashable,
                             index: 'indices.VertexID') -> None:
        assert self.registry_lock.locked()
        with self.access(catalog_id).read_lock:
            allocator = self.catalog_allocator_map[catalog_id]
            allocator.allocate(key, index)

    def deallocate_catalog_key(self, catalog_id: 'indices.CatalogID', key: typing.Hashable) -> None:
        assert self.registry_lock.locked()
        with self.access(catalog_id).read_lock:
            allocator = self.catalog_allocator_map[catalog_id]
            assert key in allocator
            allocator.deallocate(key)

    def add_catalog(self, catalog_id: 'indices.CatalogID', allocator: ...) -> None:
        assert self.registry_lock.locked()
        assert catalog_id not in self.catalog_allocator_map
        self.catalog_allocator_map[catalog_id] = allocator
        self.catalog_allocator_stack_map[catalog_id] = allocator
