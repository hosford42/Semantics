"""The Transaction is to the GraphDB Connection as the Controller is to the GraphDB itself. The Transaction hides the
low-level implementation details of data storage away from the Connection, so the Connection can focus on providing a
convenient high-level interface to the underlying data."""

import itertools
import typing

import semantics.data_control.interface as interface
import semantics.data_control.controllers as controllers
import semantics.data_structs.element_data as element_data
import semantics.data_types.allocators as allocators
import semantics.data_types.indices as indices

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Transaction(interface.ControllerInterface):
    """Temporarily stores modifications of a transaction until they are ready to be committed or rolled back. Manages
    the locks into the underlying controller that prevent conflicts if there are multiple concurrent transactions in
    progress."""

    def __init__(self, controller: controllers.Controller):
        super().__init__(controller.new_transaction_data())

    def commit(self) -> None:
        """Write any cached changes through to the underlying controller. Then clear the pending changes and release any
        held locks of the controller."""
        # For each change that was intercepted in this controller, write it through to the underlying one. The entire
        # operation must be atomic.
        with self._data.registry_lock:
            transaction_registry: typing.Dict[PersistentIDType, element_data.ElementData]
            for index_type, transaction_registry in self._data.registry_map.items():
                controller_registry: typing.MutableMapping[PersistentIDType, element_data.ElementData]
                controller_registry = self._data.controller_data.registry_map[index_type]
                deletions: typing.MutableSet[PersistentIDType]
                deletions = self._data.pending_deletion_map[index_type]
                controller_registry.update(transaction_registry)
                for index in deletions:
                    if index in controller_registry:
                        del controller_registry[index]
                # Role and label usage counts need to be decremented here. The other alternative is to capture them with
                # write locks like we do with vertices and edges, but that seems unwise since it will produce a lot of
                # lock contention, considering how much they will be used by comparison.
                if index_type is indices.VertexID:
                    controller_registry: typing.Dict[indices.VertexID, element_data.VertexData]
                    for index in deletions:
                        role_id = controller_registry[index].preferred_role
                        role_data = self._data.controller_data.registry_map[indices.RoleID][role_id]
                        assert role_data.usage_count > 0
                        role_data.usage_count -= 1
                elif index_type is indices.EdgeID:
                    controller_registry: typing.Dict[indices.EdgeID, element_data.EdgeData]
                    for index in deletions:
                        label_id = controller_registry[index].label
                        label_data = self._data.controller_data.registry_map[indices.LabelID][label_id]
                        assert label_data.usage_count > 0
                        label_data.usage_count -= 1
                transaction_registry.clear()
                deletions.clear()
            transaction_name_allocator: allocators.MapAllocator
            for index_type, transaction_name_allocator in self._data.name_allocator_map.items():
                name_allocator: allocators.MapAllocator = self._data.controller_data.name_allocator_map[index_type]
                deletions: typing.MutableSet[str] = self._data.pending_name_deletion_map[index_type]
                name_allocator.update(transaction_name_allocator, self)
                name_allocator.cancel_all_reservations(self)
                for name in deletions:
                    if name_allocator.get_index(name) is not None:
                        name_allocator.deallocate(name)
                transaction_name_allocator.clear()
                deletions.clear()

    def rollback(self) -> None:
        """Clear any pending changes without writing them, and release any held locks of the underlying controller."""
        with self._data.registry_lock:
            for index_type, transaction_registry in self._data.registry_map.items():
                controller_registry = self._data.controller_data.registry_map[index_type]
                deletions = self._data.pending_deletion_map[index_type]
                for index in itertools.chain(transaction_registry, deletions):
                    controller_registry[index].access_manager.release_write()
                transaction_registry.clear()
                deletions.clear()
            for index_type, transaction_name_allocator in self._data.name_allocator_map.items():
                deletions = self._data.pending_name_deletion_map[index_type]
                transaction_name_allocator.clear()
                deletions.clear()
                controller_name_allocator = self._data.controller_data.name_allocator_map[index_type]
                controller_name_allocator.cancel_all_reservations(self)
