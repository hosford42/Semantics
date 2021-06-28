"""Locking- and thread safety-related classes for managing concurrent interactions with GraphElement
subtypes."""

import threading
import typing

import semantics.data_types.exceptions as exceptions

if typing.TYPE_CHECKING:
    import semantics.data_types.indices as indices


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


class ThreadAccessManager:
    """Manager for read and write access to a data element."""

    def __init__(self, index: 'indices.PersistentDataID'):
        self.index = index
        self._read_locked_by: typing.Dict[threading.Thread, int] = {}
        self._write_locked_by: typing.Optional[threading.Thread] = None

    @property
    def is_read_locked(self) -> bool:
        """Whether the data element is currently locked for read access by any thread."""
        return bool(self._read_locked_by)

    @property
    def is_write_locked(self) -> bool:
        """Whether the data element is currently locked for write access by any thread."""
        return self._write_locked_by is not None

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
