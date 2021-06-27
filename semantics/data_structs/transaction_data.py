import collections
import typing

import semantics.data_structs.controller_data as controller_data
import semantics.data_structs.interface as interface
import semantics.data_types.allocators as allocators
import semantics.data_types.indices as indices
import semantics.data_types.typedefs as typedefs
from semantics.data_types import set_unions

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class TransactionData(interface.DataInterface):
    """The internal data of the Transaction. Only basic data structures and accessors should appear in this class.
    Transaction behavior should be determined entirely in the Transaction class."""

    def __init__(self, controller_data: controller_data.ControllerData):
        self.controller_data = controller_data

        # Just pass through to the underlying controller. We don't care if an ID gets skipped and is never recovered,
        # because we have an infinite supply and their values only need to be unique.
        self.reference_id_allocator = controller_data.reference_id_allocator
        self.id_allocator_map = controller_data.id_allocator_map

        self.name_allocator_map = {
            index_type: allocators.MapAllocator(str, index_type)
            for index_type in self.controller_data.name_allocator_map
        }

        self.name_allocator_stack_map = {
            index_type: collections.ChainMap(controller_name_allocator, self.name_allocator_map[index_type])
            for index_type, controller_name_allocator in self.controller_data.name_allocator_map.items()
        }

        self.vertex_time_stamp_allocator = allocators.MapAllocator(typedefs.TimeStamp, indices.VertexID)

        self.held_references = set()
        self.held_references_union = set_unions.SetUnion(controller_data.held_references, self.held_references)

        self.registry_map = {index_type: {} for index_type in self.controller_data.registry_map}

        self.registry_stack_map = {
            index_type: collections.ChainMap(controller_registry, self.registry_map[index_type])
            for index_type, controller_registry in self.controller_data.registry_map.items()
        }

        # Objects that will be deleted on commit
        self.pending_deletion_map = {index_type: set() for index_type in self.registry_map}

        # Names that will be deleted on commit
        self.pending_name_deletion_map = {index_type: set() for index_type in self.name_allocator_map}

        # Lock both the transaction and the underlying controller at once.
        self.registry_lock = controller_data.registry_lock

        # Held write locks of underlying controller that needs to be released on commit/rollback
        self.write_lock_map = {
            indices.RoleID: set(),
            indices.VertexID: set(),
            indices.LabelID: set(),
            indices.EdgeID: set(),
        }

    def allocate_name(self, name: str, index: 'PersistentIDType') -> None:
        transaction_name_allocator = self.name_allocator_map[type(index)]
        controller_name_allocator = self.controller_data.name_allocator_map[type(index)]
        transaction_name_allocator.allocate(name, index)
        try:
            controller_name_allocator.reserve(name, self)
        except KeyError:
            transaction_name_allocator.deallocate(name)
            raise

    def add_usage(self, index: 'PersistentIDType') -> None:
        self.registry_map[type(index)][index].usage_count += 1

    def remove_usage(self, index: 'PersistentIDType') -> None:
        data = self.registry_map[type(index)][index]
        assert data.usage_count > 0
        # The usage count isn't actually decremented unless/until the transaction is committed.

    def deallocate_name(self, name: str, index: 'PersistentIDType') -> None:
        assert name not in self.pending_name_deletion_map[type(index)]
        assert self.name_allocator_stack_map[type(index)][name] == index
        self.pending_name_deletion_map[type(index)].add(name)

    def allocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID) -> None:
        self.vertex_time_stamp_allocator.allocate(time_stamp, vertex_id)
        try:
            self.controller_data.vertex_time_stamp_allocator.reserve(time_stamp, self)
        except KeyError:
            self.vertex_time_stamp_allocator.deallocate(time_stamp)
            raise

    # def deallocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID) -> None:
    #     self.controller_data.vertex_time_stamp_allocator.
