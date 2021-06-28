"""Context managers for safely interacting with DataInterface contents. These classes are meant to ensure that the
appropriate locks are held and data constraints are met when the ControllerInterface interacts with its data. They also
serve as convenient generalizations across GraphElement subtypes for the various operations the ControllerInterface
needs to perform on them."""
import abc
import copy
import typing

if typing.TYPE_CHECKING:
    import semantics.data_structs.interface as interface
import semantics.data_structs.element_data as element_data
import semantics.data_types.exceptions as exceptions
import semantics.data_types.indices as indices


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Addition(typing.Generic[PersistentIDType]):

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
        return copy.copy(element_data)  # Ensures changes to the element data will have no lasting effect

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
        return copy.copy(element_data)  # Ensures changes to the element data will have no lasting effect

    def __exit__(self, exc_type, exc_val, exc_tb):
        # The element data can be None if there was no element found with the given name.
        if self._element_data is not None:
            with self._data.registry_lock:
                self._element_data.access_manager.release_read()
        self._element_data = None


class WriteAccessContextBase(typing.Generic[PersistentIDType], abc.ABC):

    def __init__(self, data: 'interface.DataInterface', index: PersistentIDType):
        self._data = data
        self._index = index
        self._controller_element_data: typing.Optional[element_data.ElementData] = None
        self._transaction_element_data: typing.Optional[element_data.ElementData] = None
        self._temporary_element_data: typing.Optional[element_data.ElementData] = None

    @abc.abstractmethod
    def _early_validation(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _do_commit(self):
        raise NotImplementedError()

    def begin(self):
        with self._data.registry_lock:
            if self._data.pending_deletion_map and self._index in self._data.pending_deletion_map[type(self._index)]:
                raise KeyError(self._index)
            self._early_validation()
            # Grab the controller data and/or transaction data and write lock them.
            if self._data.controller_data is None:
                # It's a raw controller
                controller_data = self._data.registry_map[type(self._index)][self._index]
                controller_data.access_manager.acquire_write()
                transaction_data = None
            else:
                # It's a transaction
                controller_data = self._data.controller_data.registry_map[type(self._index)].get(self._index, None)
                if controller_data is not None:
                    controller_data.access_manager.acquire_write()
                transaction_data = self._data.registry_map[type(self._index)].get(self._index, None)
                if controller_data is None and transaction_data is None:
                    raise KeyError(self._index)
                if transaction_data is not None:
                    try:
                        transaction_data.access_manager.acquire_write()
                    except exceptions.ResourceUnavailableError:
                        if controller_data is not None:
                            controller_data.access_manager.release_write()
                        raise
            # We use copy-on-write semantics for the updated element if it's a transaction. If the data is in the
            # underlying controller and not the transaction, we need to make a copy of it in the transaction and modify
            # that instead. In any case, we should grab and hold the controller copy's write lock to make sure nobody
            # else tries to modify it until the transaction is terminated.
            temporary_data = copy.copy(transaction_data or controller_data)
        assert isinstance(temporary_data, element_data.ElementData)
        self._controller_element_data = controller_data
        self._transaction_element_data = transaction_data
        self._temporary_element_data = temporary_data

    def commit(self):
        assert self._temporary_element_data is not None
        with self._data.registry_lock:
            self._do_commit()
            if self._data.controller_data is None:
                # For raw controllers, we just release the write lock to the original copy.
                self._controller_element_data.access_manager.release_write()
            else:
                # For transactions, we continue holding the write lock in the controller. If there was a copy
                # copy of the data already in the transaction, we release its write lock.
                if self._transaction_element_data is not None:
                    self._transaction_element_data.access_manager.release_write()
        self._controller_element_data = self._transaction_element_data = self._temporary_element_data = None

    def rollback(self):
        assert self._temporary_element_data is not None
        # Just release the write locks and discard the changes.
        with self._data.registry_lock:
            if self._transaction_element_data is not None:
                self._transaction_element_data.access_manager.release_write()
            if self._controller_element_data is not None:
                self._controller_element_data.access_manager.release_write()
        self._controller_element_data = self._transaction_element_data = self._temporary_element_data = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        self.begin()
        assert self._temporary_element_data is not None
        return self._temporary_element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


class Update(WriteAccessContextBase[PersistentIDType]):

    def _early_validation(self):
        pass

    def _do_commit(self):
        # Doesn't matter if it's a transaction or a raw controller.
        self._data.registry_map[type(self._index)][self._index] = self._temporary_element_data


class Removal(WriteAccessContextBase[PersistentIDType]):

    def _early_validation(self):
        # This can be expensive for roles and labels, because the entire database is scanned for uses.
        # For vertices and edges, though, it's cheap.
        if self._data.is_in_use(self._index):
            raise exceptions.ResourceUnavailableError(self._index)

    def _do_commit(self):
        # Doesn't matter if it's a transaction or a raw controller.
        registry = self._data.registry_map[type(self._index)]
        if self._index in registry:
            del registry[self._index]
