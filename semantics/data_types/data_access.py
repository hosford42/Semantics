"""Locking- and thread safety-related classes for managing concurrent interactions with GraphElement
subtypes."""
import abc
import threading
import typing

from semantics.data_types import exceptions

if typing.TYPE_CHECKING:
    from semantics.data_types import indices


class AccessLock:
    """A context manager for acquiring and releasing a lock."""

    def __init__(self, enter, leave):
        self.enter = enter
        self.leave = leave

    def __enter__(self) -> 'AccessLock':
        self.enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.leave()


class ThreadAccessManagerInterface(abc.ABC):
    """Interface for managers for read and write access to a data element."""

    @property
    def read_lock(self) -> AccessLock:
        """A context manager for automatically acquiring and releasing the element's read lock.
        Read locks are non-exclusive with each other, but cannot be held at the same time that
        another thread holds a write lock."""
        return AccessLock(self.acquire_read, self.release_read)

    @property
    def write_lock(self) -> AccessLock:
        """A context manager for automatically acquiring and releasing the element's write lock.
        Write locks are exclusive."""
        return AccessLock(self.acquire_write, self.release_write)

    @property
    @abc.abstractmethod
    def index(self) -> 'indices.PersistentDataID':
        """The index of the data element whose access is being managed."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def is_read_locked(self) -> bool:
        """Whether the data element is currently locked for read access by any thread."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def is_write_locked(self) -> bool:
        """Whether the data element is currently locked for write access by any thread."""
        raise NotImplementedError()

    @abc.abstractmethod
    def acquire_read(self):
        """Acquire a read lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        raise NotImplementedError()

    @abc.abstractmethod
    def release_read(self):
        """Release a read lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        raise NotImplementedError()

    @abc.abstractmethod
    def acquire_write(self):
        """Acquire a write lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        raise NotImplementedError()

    @abc.abstractmethod
    def release_write(self):
        """Release a write lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        raise NotImplementedError()


class ControllerThreadAccessManager(ThreadAccessManagerInterface):
    """Manager for read and write access to a data element in a controller."""

    def __init__(self, index: 'indices.PersistentDataID'):
        self._index = index
        self._read_locked_by: typing.Dict[threading.Thread, int] = {}
        self._write_locked_by: typing.Optional[threading.Thread] = None

    @property
    def index(self) -> 'indices.PersistentDataID':
        return self._index

    @property
    def is_read_locked(self) -> bool:
        """Whether the data element is currently locked for read access by any thread."""
        return bool(self._read_locked_by)

    @property
    def is_write_locked(self) -> bool:
        """Whether the data element is currently locked for write access by any thread."""
        return self._write_locked_by is not None

    @property
    def write_locked_by(self) -> typing.Optional[threading.Thread]:
        """The thread that owns the currently held write lock, if any."""
        return self._write_locked_by

    def get_transaction_level_manager(self) -> 'TransactionThreadAccessManager':
        """Returns a transaction-level thread access manager for the same index."""
        return TransactionThreadAccessManager(self)

    def acquire_read(self):
        """Acquire a read lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        if self._write_locked_by:
            raise exceptions.ResourceUnavailableError(self.index)
        thread = threading.current_thread()
        self._read_locked_by[thread] = self._read_locked_by.get(thread, 0) + 1

    def release_read(self):
        """Release a read lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        thread = threading.current_thread()
        reads_held = self._read_locked_by.get(thread, 0)
        assert reads_held > 0
        if reads_held > 1:
            self._read_locked_by[thread] = reads_held - 1
        else:
            del self._read_locked_by[thread]

    def acquire_write(self):
        """Acquire a write lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        thread = threading.current_thread()
        if self._read_locked_by and (len(self._read_locked_by) > 1 or
                                     thread not in self._read_locked_by):
            raise exceptions.ResourceUnavailableError(self.index)
        if self._write_locked_by:
            raise exceptions.ResourceUnavailableError(self.index)
        self._write_locked_by = thread

    def release_write(self):
        """Release a write lock on the element for the current thread."""
        # This is guaranteed to only be called while the registry lock is held, so there won't be
        # any race conditions.
        thread = threading.current_thread()
        assert not self._read_locked_by or (len(self._read_locked_by) == 1 and
                                            thread in self._read_locked_by)
        assert self._write_locked_by is thread
        self._write_locked_by = None


class TransactionThreadAccessManager(ThreadAccessManagerInterface):
    """Manager for read and write access to a data element in a transaction.

    Sits on top of a controller thread access manager and implements *virtual* write
    locking/unlocking on behalf of the transaction, while the write lock in the underlying
    controller is continuously held.
    """

    def __init__(self, controller_manager: ControllerThreadAccessManager):
        self._controller_manager = controller_manager
        self._thread = threading.current_thread()
        self._read_locked = 0
        self._write_locked = False
        self._controller_read_lock_held = False
        self._controller_write_lock_held = False

    @property
    def index(self) -> 'indices.PersistentDataID':
        return self._controller_manager.index

    @property
    def is_read_locked(self) -> bool:
        """Whether the data element is currently locked for read access by any thread."""
        return self._read_locked > 0

    @property
    def is_write_locked(self) -> bool:
        """Whether the data element is currently locked for write access by any thread."""
        return self._write_locked

    @property
    def controller_read_lock_held(self) -> bool:
        """Whether the controller's read lock is held."""
        return self._controller_read_lock_held

    @property
    def controller_write_lock_held(self) -> bool:
        """Whether the controller's write lock is held."""
        return self._controller_write_lock_held

    def release_controller_read_lock(self) -> None:
        """Release the underlying controller read lock."""
        assert threading.current_thread() is self._thread
        assert self._controller_read_lock_held
        assert self._read_locked == 0, "%r is still read locked." % self._controller_manager.index
        self._controller_manager.release_read()
        self._controller_read_lock_held = False

    def release_controller_write_lock(self) -> None:
        """Release the underlying controller write lock."""
        assert threading.current_thread() is self._thread
        assert self._controller_write_lock_held
        assert not self._write_locked, "%r is still write locked." % self._controller_manager.index
        self._controller_manager.release_write()
        self._controller_write_lock_held = False

    def acquire_read(self):
        """Acquire a read lock on the element for the current thread."""
        assert threading.current_thread() is self._thread
        if not (self._controller_read_lock_held or self._controller_write_lock_held):
            # Acquire the controller-level lock, too. The controller-level lock won't be released,
            # however; instead it is held until a commit or rollback takes place.
            self._controller_manager.acquire_read()
            self._controller_read_lock_held = True
        self._read_locked += 1

    def release_read(self):
        """Release a read lock on the element for the current thread."""
        assert threading.current_thread() is self._thread
        assert self._read_locked > 0, "%r is not read locked." % self._controller_manager.index
        self._read_locked -= 1

    def acquire_write(self):
        """Acquire a write lock on the element for the current thread."""
        assert threading.current_thread() is self._thread
        if self._write_locked:
            raise exceptions.ResourceUnavailableError(self.index)
        if not self._controller_write_lock_held:
            # Acquire the controller-level lock, too. The controller-level lock won't be released,
            # however; instead it is held until a commit or rollback takes place.
            self._controller_manager.acquire_write()
            self._controller_write_lock_held = True
        self._write_locked = True

    def release_write(self):
        """Release a write lock on the element for the current thread."""
        assert threading.current_thread() is self._thread
        assert self._write_locked, "%r is not write locked." % self._controller_manager.index
        self._write_locked = False
