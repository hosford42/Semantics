"""Context managers for safely interacting with DataInterface contents. These classes are meant to
ensure that the appropriate locks are held and data constraints are met when the ControllerInterface
interacts with its data. They also serve as convenient generalizations across GraphElement subtypes
for the various operations the ControllerInterface needs to perform on them."""

import abc
import copy
import typing

from semantics.data_structs import element_data
from semantics.data_types import exceptions
from semantics.data_types import indices
from semantics.data_types import data_access

if typing.TYPE_CHECKING:
    from semantics.data_structs import interface


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Adding(typing.Generic[PersistentIDType]):
    """Context manager for adding an element to the database."""

    def __init__(self, data: 'interface.DataInterface', index_type: typing.Type[PersistentIDType],
                 *args, **kwargs):
        self._data = data
        self._index_type = index_type
        self._element_data: typing.Optional[element_data.ElementData[PersistentIDType]] = None
        self._args = args
        self._kwargs = kwargs

    def _begin(self):
        """Begin adding an element to the database or transaction."""
        assert self._element_data is None
        index = self._data.id_allocator_map[self._index_type].new_id()
        self._element_data = self._data.element_type_map[self._index_type](index, *self._args,
                                                                           **self._kwargs)

    def _commit(self):
        """Add the new element to the database or transaction."""
        assert self._element_data
        with self._data.registry_lock:
            registry = self._data.registry_map[self._index_type]
            assert self._element_data.index not in registry
            access = self._data.access_map[self._index_type]
            assert self._element_data.index not in access
            # Put a copy into the registry so that if someone misbehaves and keeps a reference to
            # the data returned by the context manager, they can't affect the registry with it.
            registry[self._element_data.index] = copy.copy(self._element_data)
            # It doesn't matter if it's a controller or a transaction. There is no pre-existing
            # copy of the data, so we don't need an access manager overlay.
            access[self._element_data.index] = \
                data_access.ControllerThreadAccessManager(self._element_data.index)
        self._element_data = None

    def _rollback(self):
        """Cancel adding the new element to the database or transaction."""
        self._element_data = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        self._begin()
        assert self._element_data is not None
        return self._element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._commit()
        else:
            self._rollback()


class Reading(typing.Generic[PersistentIDType]):
    """Context manager for gaining read access to an element in the database using index lookup."""

    def __init__(self, data: 'interface.DataInterface', index: PersistentIDType):
        self._data = data
        self._index = index
        self._element_data: typing.Optional[element_data.ElementData] = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        with self._data.registry_lock:
            if self._data.pending_deletion_map and \
                    self._index in self._data.pending_deletion_map[type(self._index)]:
                raise KeyError(self._index)
            self._data.access(self._index).acquire_read()
            registry_entry = self._data.registry_stack_map[type(self._index)][self._index]
        self._element_data = registry_entry
        # Ensures changes to the element data will have no lasting effect
        return copy.copy(registry_entry)

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._element_data is not None
        with self._data.registry_lock:
            self._data.access(self._element_data.index).release_read()
        self._element_data = None


class Finding(typing.Generic[PersistentIDType]):
    """Context manager for gaining read access to an element in the database using name lookup."""

    def __init__(self, data: 'interface.DataInterface', index_type: typing.Type[PersistentIDType],
                 name: str):
        self._data = data
        self._index_type = index_type
        self._name = name
        self._element_data = None

    def __enter__(self) -> typing.Optional[element_data.ElementData[PersistentIDType]]:
        assert self._element_data is None
        with self._data.registry_lock:
            if self._data.pending_name_deletion_map and \
                    self._name in self._data.pending_name_deletion_map[self._index_type]:
                return None
            index = self._data.name_allocator_stack_map[self._index_type].get(self._name)
            if index is None or (self._data.pending_deletion_map and
                                 index in self._data.pending_deletion_map[self._index_type]):
                return None
            self._data.access(index).acquire_read()
            registry_entry = self._data.registry_stack_map[self._index_type][index]
        self._element_data = registry_entry
        # Ensures changes to the element data will have no lasting effect
        return copy.copy(registry_entry)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # The element data can be None if there was no element found with the given name.
        if self._element_data is not None:
            with self._data.registry_lock:
                self._data.access(self._element_data.index).release_read()
        self._element_data = None


class WriteAccessContextBase(typing.Generic[PersistentIDType], abc.ABC):
    """Base class for context managers for gaining write access to an element in the database."""

    def __init__(self, data: 'interface.DataInterface', index: PersistentIDType):
        assert index is not None
        self._data = data
        self._index = index
        self._controller_element_data: typing.Optional[element_data.ElementData] = None
        self._transaction_element_data: typing.Optional[element_data.ElementData] = None
        self._temporary_element_data: typing.Optional[element_data.ElementData] = None

    @abc.abstractmethod
    def _early_validation(self):
        """Perform early checks to verify that the requested access can be granted. Raise an
        exception if access should not be granted."""
        raise NotImplementedError()

    @abc.abstractmethod
    def _do_commit(self):
        """Apply the actual change to the underlying data."""
        raise NotImplementedError()

    def _begin(self):
        """Begin providing the requested access."""
        with self._data.registry_lock:
            if self._data.pending_deletion_map and \
                    self._index in self._data.pending_deletion_map[type(self._index)]:
                raise KeyError(self._index)
            self._early_validation()
            # Grab the controller data and/or transaction data and write lock them.
            if self._data.controller_data is None:
                controller_data = None
            else:
                controller_data = self._data.controller_data.registry_map[type(self._index)] \
                    .get(self._index, None)
            transaction_data = self._data.registry_map[type(self._index)].get(self._index, None)
            if controller_data is None and transaction_data is None:
                raise KeyError(self._index)
            self._data.access(self._index).acquire_write()
            # We use copy-on-write semantics for the updated element if it's a transaction. If the
            # data is in the underlying controller and not the transaction, we need to make a copy
            # of it in the transaction and modify that instead. In any case, we should grab and hold
            # the controller copy's write lock to make sure nobody else tries to modify it until the
            # transaction is terminated.
            temporary_data = copy.copy(transaction_data or controller_data)
        assert isinstance(temporary_data, element_data.ElementData)
        self._controller_element_data = controller_data
        self._transaction_element_data = transaction_data
        self._temporary_element_data = temporary_data

    def _commit(self):
        """Apply the changes to the data."""
        assert self._temporary_element_data is not None
        with self._data.registry_lock:
            access = self._data.access(self._index)
            self._do_commit()
            access.release_write()
        self._controller_element_data = self._transaction_element_data = \
            self._temporary_element_data = None

    def _rollback(self):
        """Cancel the changes to the data."""
        assert self._temporary_element_data is not None
        # Just release the write locks and discard the changes.
        with self._data.registry_lock:
            self._data.access(self._index).release_write()
        self._controller_element_data = self._transaction_element_data = \
            self._temporary_element_data = None

    def __enter__(self) -> 'element_data.ElementData[PersistentIDType]':
        self._begin()
        assert self._temporary_element_data is not None
        return self._temporary_element_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._commit()
        else:
            self._rollback()


class Updating(WriteAccessContextBase[PersistentIDType]):
    """Context manager for gaining update (modify) access to an element in the database."""

    def _early_validation(self):
        """Perform early checks to verify that the requested access can be granted. Raise an
        exception if access should not be granted."""
        # Nothing needs to be checked here.

    def _do_commit(self):
        """Apply the actual change to the underlying data."""
        # Doesn't matter if it's a transaction or a raw controller. In either case, we assign
        # the new version of the element's data to the index in the registry. We make a copy first
        # so that if someone misbehaves and keeps a reference to the data returned by the context
        # manager, they can't affect the registry with it.
        self._data.registry_map[type(self._index)][self._index] = \
            copy.copy(self._temporary_element_data)


class Removing(WriteAccessContextBase[PersistentIDType]):
    """Context manager for gaining remove access to an element in the database."""

    def _early_validation(self):
        """Perform early checks to verify that the requested access can be granted. Raise an
        exception if access should not be granted."""
        # This can be expensive for roles and labels, because the entire database is scanned for
        # uses. For vertices and edges, though, it's cheap.
        if self._data.is_in_use(self._index):
            raise exceptions.ResourceUnavailableError(self._index)

    def _do_commit(self):
        """Apply the actual change to the underlying data."""
        # Doesn't matter if it's a transaction or a raw controller. We make sure there is no entry
        # for the index in the registry.
        registry = self._data.registry_map[type(self._index)]
        if self._index in registry:
            del registry[self._index]
        if self._data.pending_deletion_map is None:
            # For controllers only, we also remove it from the access map.
            del self._data.access_map[type(self._index)][self._index]
        else:
            # For transactions only, we also add it to the pending deletions, to prevent
            # pass-through to the underlying controller in future operations.
            self._data.pending_deletion_map[type(self._index)].add(self._index)
