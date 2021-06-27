"""Context managers for safely interacting with DataInterface contents. These classes are meant to ensure that the
appropriate locks are held and data constraints are met when the ControllerInterface interacts with its data. They also
serve as convenient generalizations across GraphElement subtypes for the various operations the ControllerInterface
needs to perform on them."""
import copy
import typing

if typing.TYPE_CHECKING:
    import semantics.data_structs.interface as interface
import semantics.data_structs.element_data as element_data
import semantics.data_types.exceptions as exceptions
import semantics.data_types.indices as indices


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Addition(typing.Generic[PersistentIDType]):
    # Only one shared class for Addition, because the two use cases are identical in behavior.

    def __init__(self, data: 'interface.DataInterface', index_type: typing.Type[PersistentIDType],
                 *args, **kwargs):
        self._data = data
        self._index_type = index_type
        self._element_data: typing.Optional[element_data.ElementData[PersistentIDType]] = None
        self._args = args
        self._kwargs = kwargs

    def begin(self):
        assert self._element_data is None
        index = self._data.id_allocator_map[self._index_type].new_id()
        self._element_data = self._data.element_type_map[self._index_type](index, *self._args, **self._kwargs)

    def commit(self):
        assert self._element_data
        with self._data.registry_lock:
            registry = self._data.registry_map[self._index_type]
            assert self._element_data.index not in registry
            registry[self._element_data.index] = self._element_data
        self._element_data = None

    def rollback(self):
        self._element_data = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        self.begin()
        assert self._element_data is not None
        return self._element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


class Read(typing.Generic[PersistentIDType]):

    def __init__(self, data: 'interface.DataInterface', index: PersistentIDType):
        self._data = data
        self._index = index
        self._element_data: typing.Optional[element_data.ElementData] = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        with self._data.registry_lock:
            if self._data.pending_deletion_map and self._index in self._data.pending_deletion_map[type(self._index)]:
                raise KeyError(self._index)
            element_data = self._data.registry_stack_map[type(self._index)][self._index]
            element_data.access_manager.acquire_read()
        self._element_data = element_data
        return element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._element_data is not None
        with self._data.registry_lock:
            self._element_data.access_manager.release_read()
        self._element_data = None


class Find(typing.Generic[PersistentIDType]):

    def __init__(self, data: 'interface.DataInterface', index_type: typing.Type[PersistentIDType], name: str):
        self._data = data
        self._index_type = index_type
        self._name = name
        self._element_data = None

    def __enter__(self) -> typing.Optional[element_data.ElementData[PersistentIDType]]:
        assert self._element_data is None
        with self._data.registry_lock:
            index = self._data.name_allocator_stack_map[self._index_type].get(self._name)
            if index is None or (self._data.pending_deletion_map and
                                 index in self._data.pending_deletion_map[self._index_type]):
                return None
            element_data = self._data.registry_stack_map[self._index_type][index]
            element_data.access_manager.acquire_read()
        self._element_data = element_data
        return element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        # The element data can be None if there was no element found with the given name.
        if self._element_data is not None:
            with self._data.registry_lock:
                self._element_data.access_manager.release_read()
        self._element_data = None


class Update(typing.Generic[PersistentIDType]):

    def __init__(self, data: 'interface.DataInterface', index: PersistentIDType):
        self._data = data
        self._index = index
        self._controller_element_data: typing.Optional[element_data.ElementData] = None
        self._transaction_element_data: typing.Optional[element_data.ElementData] = None

    def begin(self):
        with self._data.registry_lock:
            if self._data.pending_deletion_map and self._index in self._data.pending_deletion_map[type(self._index)]:
                raise KeyError(self._index)
            if self._data.controller_data is None:
                controller_registry = self._data.registry_map[type(self._index)]
                transaction_registry = None
            else:
                controller_registry = self._data.controller_data.registry_map[type(self._index)]
                transaction_registry = self._data.registry_map[type(self._index)]
            # We use copy-on-write semantics for the updated element if it's a transaction. If the data is in the
            # underlying controller and not the transaction, we need to make a copy of it in the transaction and modify
            # that instead. In any case, we should grab and hold the controller copy's write lock to make sure nobody
            # else tries to modify it until the transaction is terminated.
            controller_data = controller_registry[self._index]
            controller_data.access_manager.acquire_write()
            if transaction_registry is None:
                # TODO: We should be making a copy of the controller data to enforce rollback on exception.
                transaction_data = None
            else:
                try:
                    if self._index in transaction_registry:
                        transaction_data = transaction_registry[self._index]
                    else:
                        transaction_data = copy.copy(self._controller_element_data)
                    transaction_data.access_manager.acquire_write()
                except Exception:
                    self._controller_element_data.access_manager.release_write()
                    raise
        self._controller_element_data = controller_data
        self._transaction_element_data = transaction_data

    def commit(self):
        assert self._controller_element_data is not None
        with self._data.registry_lock:
            if self._transaction_element_data is None:
                # Put the controller's element data into the registry and release the the write lock.
                self._data.registry_map[type(self._index)][self._index] = self._controller_element_data
            else:
                # Put the transaction's copy of the element's data into the transaction registry and continue to hold
                # the write lock of the controller's copy.
                self._data.registry_map[type(self._index)][self._index] = self._transaction_element_data
                self._transaction_element_data.access_manager.release_write()
            self._controller_element_data.access_manager.release_write()
        self._controller_element_data = self._transaction_element_data = None

    def rollback(self):
        assert self._controller_element_data is not None
        with self._data.registry_lock:
            # Release the write lock of the controller's element data and discard the changes.
            if self._transaction_element_data is not None:
                self._transaction_element_data.access_manager.release_write()
            self._controller_element_data.access_manager.release_write()
        self._controller_element_data = self._transaction_element_data = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        self.begin()
        if self._transaction_element_data is None:
            result = self._controller_element_data
        else:
            result = self._transaction_element_data
        assert result is not None
        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


class Removal(typing.Generic[PersistentIDType]):

    def __init__(self, data: 'interface.DataInterface', index: PersistentIDType):
        self._data = data
        self._index = index
        self._controller_element_data: typing.Optional[element_data.ElementData] = None
        self._transaction_element_data: typing.Optional[element_data.ElementData] = None

    def begin(self):
        with self._data.registry_lock:
            if (self._data.pending_deletion_map is not None and
                    self._index in self._data.pending_deletion_map[type(self._index)]):
                raise KeyError(self._index)
            # This can be expensive for roles and labels, because the entire database is scanned for uses.
            # For vertices and edges, though, it's cheap.
            if self._data.is_in_use(self._index):
                raise exceptions.ResourceUnavailableError(self._index)
            if self._data.controller_data is None:
                controller_registry = self._data.registry_map[type(self._index)]
                transaction_registry = None
            else:
                controller_registry = self._data.controller_data.registry_map[type(self._index)]
                transaction_registry = self._data.registry_map[type(self._index)]
            # We use copy-on-write semantics for the deleted element if it's a transaction. If the data is in the
            # underlying controller and not the transaction, we need to make a copy of it in the transaction and modify
            # that instead. In any case, we should grab and hold the controller copy's write lock to make sure nobody
            # else tries to modify it until the transaction is terminated.
            controller_element_data = controller_registry[self._index]
            controller_element_data.access_manager.acquire_write()
            try:
                if transaction_registry is None:
                    transaction_element_data = None
                else:
                    if self._index in transaction_registry:
                        transaction_element_data = transaction_registry[self._index]
                    else:
                        transaction_element_data = copy.copy(self._controller_element_data)
                    transaction_element_data.access_manager.acquire_write()
            except Exception:
                controller_element_data.access_manager.release_write()
                raise
        self._controller_element_data = controller_element_data
        self._transaction_element_data = transaction_element_data

    def commit(self):
        assert self._controller_element_data is not None
        with self._data.registry_lock:
            registry = self._data.registry_map[type(self._index)]
            if self._transaction_element_data is None:
                # Remove the controller's element data and release the write lock.
                if self._index in registry:
                    del registry[self._index]
                self._controller_element_data.access_manager.release_write()
            else:
                # Remove the transaction's copy of the data, add the index to the pending deletion map, and continue to
                # hold the write lock of the controller's copy.
                if self._index in registry:
                    del registry[self._index]
                self._data.pending_deletion_map[type(self._index)].add(self._index)
                self._transaction_element_data.access_manager.release_write()
        self._controller_element_data = self._transaction_element_data = None

    def rollback(self):
        assert self._controller_element_data is not None
        with self._data.registry_lock:
            # Release the write locks and discard the changes.
            if self._transaction_element_data is not None:
                self._transaction_element_data.access_manager.release_write()
            self._controller_element_data.access_manager.release_write()
        self._controller_element_data = self._transaction_element_data = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        self.begin()
        assert self._controller_element_data is not None
        if self._transaction_element_data is None:
            return self._controller_element_data
        else:
            return self._transaction_element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
