"""
Internal state of the transaction.
"""

import collections
import typing

from semantics.data_structs import controller_data as controller_data_module
from semantics.data_structs import interface
from semantics.data_types import allocators
from semantics.data_types import data_access
from semantics.data_types import indices
from semantics.data_types import set_unions

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class TransactionData(interface.DataInterface[controller_data_module.ControllerData,
                                              data_access.TransactionThreadAccessManager]):
    """The internal data of the Transaction. Only basic data structures and accessors should appear
    in this class. Transaction behavior should be determined entirely in the Transaction class."""

    def __init__(self, controller_data: controller_data_module.ControllerData):
        super().__init__()

        self.controller_data = controller_data

        # Just pass through to the underlying controller. We don't care if an ID gets skipped and is
        # never recovered, because we have an infinite supply and their values only need to be
        # unique.
        self.reference_id_allocator = controller_data.reference_id_allocator
        self.id_allocator_map = controller_data.id_allocator_map

        self.name_allocator_map = {
            index_type: allocators.MapAllocator(str, index_type)
            for index_type in self.controller_data.name_allocator_map
        }

        self.name_allocator_stack_map = {
            index_type: collections.ChainMap(self.name_allocator_map[index_type],
                                             controller_name_allocator)
            for index_type, controller_name_allocator
            in self.controller_data.name_allocator_map.items()
        }

        self.catalog_allocator_map = {
            index: type(allocator)(allocator.key_type, allocator.index_type)
            for index, allocator in self.controller_data.catalog_allocator_map.items()
        }
        self.catalog_allocator_stack_map = {
            index: collections.ChainMap(self.catalog_allocator_map[index], controller_allocator)
            for index, controller_allocator in self.controller_data.catalog_allocator_map.items()
        }

        self.held_references = {}
        self.held_references_union = set_unions.SetUnion(controller_data.held_references.keys(),
                                                         self.held_references.keys())

        self.registry_map = {index_type: {} for index_type in self.controller_data.registry_map}

        self.registry_stack_map = {
            index_type: collections.ChainMap(self.registry_map[index_type], controller_registry)
            for index_type, controller_registry in self.controller_data.registry_map.items()
        }

        # Objects that will be deleted on commit
        self.pending_deletion_map = {index_type: set() for index_type in self.registry_map}

        # Names that will be deleted on commit
        self.pending_name_deletion_map = {index_type: set()
                                          for index_type in self.name_allocator_map}

        # Catalog keys that will be deleted on commit.
        self.pending_catalog_deletion_map: typing.Dict[indices.CatalogID,
                                                       typing.Set[typing.Hashable]] = {}

        # Lock both the transaction and the underlying controller at once.
        self.registry_lock = controller_data.registry_lock

        # Held write locks of underlying controller that needs to be released on commit/rollback
        self.write_lock_map = {
            indices.RoleID: set(),
            indices.VertexID: set(),
            indices.LabelID: set(),
            indices.EdgeID: set(),
            indices.CatalogID: set(),
        }

    def access(self, index: 'PersistentIDType') -> 'data_access.TransactionThreadAccessManager':
        """Return the thread access manager with the given index. Raise a KeyError if
        no data is associated with the index.

        Note: The registry lock must be held while calling this method.
        """
        assert self.registry_lock.locked()
        if index in self.pending_deletion_map[type(index)]:
            raise KeyError(index)
        if index not in self.access_map[type(index)] and \
                index in self.controller_data.access_map[type(index)]:
            manager = self.controller_data.access_map[type(index)][index]
            assert isinstance(manager, data_access.ControllerThreadAccessManager)
            manager = manager.get_transaction_level_manager()
            self.access_map[type(index)][index] = manager
            return manager
        return self.access_map[type(index)][index]

    def new_access(self, index: 'PersistentIDType') -> data_access.TransactionThreadAccessManager:
        controller_manager = data_access.ControllerThreadAccessManager(index)
        return data_access.TransactionThreadAccessManager(controller_manager)

    def allocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Allocate a new name for the index."""
        transaction_name_allocator = self.name_allocator_map[type(index)]
        controller_name_allocator = self.controller_data.name_allocator_map[type(index)]
        transaction_name_allocator.allocate(name, index)
        try:
            controller_name_allocator.reserve(name, self)
        except KeyError:
            transaction_name_allocator.deallocate(name)
            raise

    def deallocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Deallocate the name from the index."""
        assert name not in self.pending_name_deletion_map[type(index)]
        assert self.name_allocator_stack_map[type(index)].get(name) == index
        self.pending_name_deletion_map[type(index)].add(name)

    def allocate_catalog_key(self, catalog_id: 'indices.CatalogID', key: typing.Hashable,
                             index: 'indices.VertexID') -> None:
        assert self.registry_lock.locked()
        with self.access(catalog_id).read_lock:
            transaction_allocator = self.catalog_allocator_map[catalog_id]
            controller_allocator = self.controller_data.catalog_allocator_map.get(catalog_id, None)
            transaction_allocator.allocate(key, index)
            if controller_allocator is not None:
                try:
                    controller_allocator.reserve(key, self)
                except KeyError:
                    transaction_allocator.deallocate(key)
                    raise

    def deallocate_catalog_key(self, catalog_id: 'indices.CatalogID', key: typing.Hashable) -> None:
        assert self.registry_lock.locked()
        with self.access(catalog_id).read_lock:
            assert key not in self.pending_catalog_deletion_map[catalog_id]
            assert key in self.catalog_allocator_map[catalog_id]
            self.pending_catalog_deletion_map[catalog_id].add(key)

    def add_catalog(self, catalog_id: 'indices.CatalogID', allocator: ...) -> None:
        assert self.registry_lock.locked()
        assert catalog_id not in self.catalog_allocator_map
        self.catalog_allocator_map[catalog_id] = allocator
        controller_allocator = self.controller_data.catalog_allocator_map.get(catalog_id, None)
        if controller_allocator is None:
            self.catalog_allocator_stack_map[catalog_id] = allocator
        else:
            self.catalog_allocator_stack_map[catalog_id] = \
                collections.ChainMap(allocator, controller_allocator)
