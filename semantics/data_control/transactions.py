"""The Transaction is to the GraphDB Connection as the Controller is to the GraphDB itself. The
Transaction hides the low-level implementation details of data storage away from the Connection, so
the Connection can focus on providing a convenient high-level interface to the underlying data."""

import typing

import semantics.data_control.base as interface
from semantics.data_control import controllers
from semantics.data_structs import element_data
from semantics.data_structs import transaction_data
from semantics.data_types import allocators
from semantics.data_types import data_access
from semantics.data_types import exceptions
from semantics.data_types import indices

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Transaction(interface.BaseController[transaction_data.TransactionData]):
    """Temporarily stores modifications of a transaction until they are ready to be committed or
    rolled back. Manages the locks into the underlying controller that prevent conflicts if there
    are multiple concurrent transactions in progress."""

    def __init__(self, controller: controllers.Controller):
        super().__init__(controller.new_transaction_data())
        self._is_open = True

    @property
    def is_open(self) -> bool:
        """Whether the connection is open. Attempts to use the connection after it has been closed
        will cause a ConnectionClosedError to be raised."""
        return self._is_open

    def __del__(self):
        if getattr(self, '_is_open', False):
            self.close()

    def __getattribute__(self, name):
        # This forces a ConnectionClosedError if anybody tries to use the transaction after it's
        # been closed.
        if name == '_data' and not super().__getattribute__('_is_open'):
            raise exceptions.ConnectionClosedError()
        return super().__getattribute__(name)

    def close(self) -> None:
        """Close the transaction. If there are pending changes, they are rolled back."""
        if self._is_open:
            # Roll back any pending changes.
            self.rollback()

            # And make it impossible to make new changes.
            self._is_open = False

    def commit(self) -> None:
        """Atomically write any cached changes through to the underlying controller. Then clear the
        pending changes and release any held locks of the controller."""
        with self._data.registry_lock:
            transaction_registry: typing.Dict[PersistentIDType, element_data.ElementData]
            for index_type, transaction_registry in self._data.registry_map.items():
                controller_registry: typing.MutableMapping[PersistentIDType,
                                                           element_data.ElementData]
                controller_registry = self._data.controller_data.registry_map[index_type]
                controller_access: typing.MutableMapping[PersistentIDType,
                                                         data_access.ThreadAccessManagerInterface]
                controller_access = self._data.controller_data.access_map[index_type]
                deletions: typing.MutableSet[PersistentIDType]
                deletions = self._data.pending_deletion_map[index_type]
                controller_registry.update(transaction_registry)
                for index in deletions:
                    if index in controller_registry:
                        del controller_registry[index]
                        del self._data.access_map[index_type][index]
                        del controller_access[index]
                transaction_registry.clear()
                deletions.clear()
            transaction_name_allocator: allocators.MapAllocator
            for index_type, transaction_name_allocator in self._data.name_allocator_map.items():
                name_allocator: allocators.MapAllocator = \
                    self._data.controller_data.name_allocator_map[index_type]
                deletions: typing.MutableSet[str] = self._data.pending_name_deletion_map[index_type]
                name_allocator.update(transaction_name_allocator, self._data)
                name_allocator.cancel_all_reservations(self)
                for name in deletions:
                    if name_allocator.get_index(name) is not None:
                        name_allocator.deallocate(name)
                transaction_name_allocator.clear()
                deletions.clear()
            for index_type, access in self._data.access_map.items():
                controller_access = self._data.controller_data.access_map[index_type]
                expired_indices = []
                for index, access_manager in access.items():
                    assert not access_manager.is_write_locked
                    # It should always be a transaction manager, whose controller manager may or may
                    # not be present in the controller depending on whether it's a new element. If
                    # it's not present, we add it. Then we expire the transaction manager using the
                    # same logic in either case.
                    assert isinstance(access_manager, data_access.TransactionThreadAccessManager)
                    if index not in controller_access:
                        controller_access[index] = access_manager.controller_manager
                    if access_manager.controller_write_lock_held:
                        access_manager.release_controller_write_lock()
                    if not access_manager.is_read_locked:
                        if access_manager.controller_read_lock_held:
                            access_manager.release_controller_read_lock()
                        expired_indices.append(index)
                for index in expired_indices:
                    del access[index]

    def rollback(self) -> None:
        """Clear any pending changes without writing them, and release any held locks of the
        underlying controller."""
        with self._data.registry_lock:
            for index_type, transaction_registry in self._data.registry_map.items():
                transaction_registry.clear()
                deletions = self._data.pending_deletion_map[index_type]
                deletions.clear()
            for index_type, transaction_name_allocator in self._data.name_allocator_map.items():
                deletions = self._data.pending_name_deletion_map[index_type]
                transaction_name_allocator.clear()
                deletions.clear()
                controller_name_allocator = \
                    self._data.controller_data.name_allocator_map[index_type]
                controller_name_allocator.cancel_all_reservations(self)
            for index_type, access in self._data.access_map.items():
                expired_indices = []
                for index, access_manager in access.items():
                    assert not access_manager.is_write_locked
                    if access_manager.controller_write_lock_held:
                        access_manager.release_controller_write_lock()
                    if not access_manager.is_read_locked:
                        if access_manager.controller_read_lock_held:
                            access_manager.release_controller_read_lock()
                        expired_indices.append(index)
                for index in expired_indices:
                    del access[index]
