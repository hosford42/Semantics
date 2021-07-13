"""
Allocators for various simple resources, e.g., unique indices and name/index assignments.
"""
import bisect
import threading
import typing

KeyType = typing.TypeVar('KeyType', bound=typing.Hashable)
IndexType = typing.TypeVar('IndexType', bound=int)


class IndexAllocator(typing.Generic[IndexType]):
    """Generates unique IDs of a given integer type. Thread-safe."""

    def __init__(self, index_type: typing.Type[IndexType]):
        self._next_id = 0
        self._index_type = index_type
        self._lock = threading.Lock()

    def __getstate__(self):
        return self._next_id, self._index_type

    def __setstate__(self, state):
        self._next_id, self._index_type = state
        self._lock = threading.Lock()

    @property
    def index_type(self) -> typing.Type[IndexType]:
        """The type of index returned by the allocator."""
        return self._index_type

    @property
    def total_allocated(self) -> int:
        """The total number of unique indices that have been allocated."""
        return self._next_id

    def new_id(self) -> IndexType:
        """Allocate and return a new unique index."""
        with self._lock:
            allocated_id = self._next_id
            self._next_id += 1
        return self._index_type(allocated_id)


class MapAllocator(typing.MutableMapping[KeyType, IndexType]):
    """Assigns keys to indices in a guaranteed one-to-one mapping. Thread-safe."""

    def __init__(self, key_type: typing.Type[KeyType], index_type: typing.Type[IndexType]):
        self._key_type = key_type
        self._index_type = index_type
        self._key_map: typing.Dict[KeyType, IndexType] = {}
        self._index_map: typing.Dict[IndexType, KeyType] = {}
        self._reserved: typing.Dict[KeyType, typing.Any] = {}
        self._lock = threading.Lock()

    def __getstate__(self):
        return self._key_type, self._index_type, self._key_map

    def __setstate__(self, state):
        self._key_type, self._index_type, self._key_map = state
        self._index_map = {index: key for key, index in self._key_map.items()}
        self._reserved = {}
        self._lock = threading.Lock()

    @property
    def key_type(self) -> typing.Type[KeyType]:
        """The type of key the allocator maps to indices."""
        return self._key_type

    @property
    def index_type(self) -> typing.Type[IndexType]:
        """The type of index that the allocator maps keys to."""
        return self._index_type

    def __setitem__(self, value1: typing.Union[KeyType, IndexType],
                    value2: typing.Union[KeyType, IndexType]) -> None:
        if isinstance(value1, self._key_type):
            self.allocate(value1, value2)
        else:
            self.allocate(value2, value1)

    def __delitem__(self, value: typing.Union[KeyType, IndexType]) -> None:
        if isinstance(value, self._key_type):
            self.deallocate(value)
        else:
            self.deallocate(self[value])

    def __getitem__(self, value: typing.Union[KeyType, IndexType]) \
            -> typing.Union[KeyType, IndexType]:
        if isinstance(value, self._key_type):
            result = self.get_index(value)
        else:
            result = self.get_key(value)
        if result is None:
            raise KeyError(value)
        return result

    def __len__(self) -> int:
        return len(self._key_map)

    def __iter__(self) -> typing.Iterator[KeyType]:
        return iter(self._key_map)

    def is_reserved(self, key: KeyType) -> bool:
        """Return whether the key is currently reserved."""
        with self._lock:
            return key in self._reserved

    def reserve(self, key: KeyType, owner: typing.Any) -> None:
        """Prevent a key from being mapped to an index, except by the given owner."""
        with self._lock:
            if self._reserved.get(key, owner) is not owner:
                raise KeyError("Key %r is already reserved." % (key,))
            if key in self._key_map:
                raise KeyError("Key %r is already allocated." % (key,))
            self._reserved[key] = owner

    def cancel_reservation(self, key: KeyType, owner: typing.Any) -> None:
        """Cancel a previously made key reservation by the given owner."""
        with self._lock:
            if self._reserved.get(key, None) is not owner:
                raise KeyError("Key %r is not reserved by this owner." % (key,))
            del self._reserved[key]

    def cancel_all_reservations(self, owner: typing.Any) -> None:
        """Cancel all previously made key reservations by the given owner."""
        with self._lock:
            keys = []
            for key, reservation_owner in self._reserved.items():
                if reservation_owner is owner:
                    keys.append(key)
            for key in keys:
                del self._reserved[key]

    def allocate(self, key: KeyType, index: IndexType, owner: typing.Any = None):
        """Map the given key to the given index. If the key is reserved by a different owner, or
        is reserved by any owner and no owner is provided, raise an exception. If the key is already
        mapped to another index, or another key already maps to the index, raise an exception."""
        assert index is not None
        with self._lock:
            if self._reserved.get(key, owner) is not owner:
                raise KeyError("Key %r is already reserved." % (key,))
            if self._key_map.get(key, index) != index:
                raise KeyError("Key %r is already allocated." % (key,))
            if self._index_map.get(index, key) != key:
                raise KeyError("Index %r is already mapped." % (index,))
            if key in self._reserved:
                del self._reserved[key]
            self._key_map[key] = index
            self._index_map[index] = key

    def deallocate(self, key: KeyType) -> IndexType:
        """Remove and return the mapped index for the given key."""
        with self._lock:
            if key not in self._key_map:
                raise KeyError("Key %r is not allocated." % (key,))
            index = self._key_map.pop(key)
            del self._index_map[index]
        return index

    def get_index(self, key: KeyType) -> typing.Optional[IndexType]:
        """Return the index the key is mapped to, if any."""
        assert isinstance(key, self._key_type)
        return self._key_map.get(key, None)

    def get_key(self, index: IndexType) -> typing.Optional[KeyType]:
        """Return the key that maps to the index, if any."""
        assert isinstance(index, self._index_type)
        return self._index_map.get(index, None)

    # Pylint doesn't understand that other has the same type as self, and no amount of type
    # annotations or assertions seems to change that.
    # pylint: disable=W0212
    def update(self, other: 'MapAllocator', owner: typing.Any = None) -> None:
        """Update the mapping to incorporate the contents of another mapping. Similar in effect to
        dict.update(), except that reservations and mapping conflicts are accounted for."""
        assert self._key_type is other._key_type
        assert self._index_type is other._index_type
        if other is self:
            return
        with self._lock:
            for key, reservation_owner in self._reserved.items():
                if reservation_owner is owner:
                    continue
                old_index = self._key_map.get(key, None)
                new_index = other._key_map.get(key, None)
                if old_index is not None and old_index != new_index:
                    raise KeyError("Key %r is already reserved for %s." % (key, old_index))
            updated_keys = self._key_map.copy()
            updated_keys.update(other._key_map)
            updated_indices = self._index_map.copy()
            updated_indices.update(other._index_map)
            if len(updated_keys) < len(updated_indices):
                raise KeyError("Two or more indices would be assigned to the same key.")
            if len(updated_keys) > len(updated_indices):
                raise KeyError("Two or more keys would be assigned to the same index.")
            self._key_map = updated_keys
            self._index_map = updated_indices

    def clear(self):
        """Remove all key/index mappings and key reservations, returning the allocator to its
        initial state."""
        with self._lock:
            self._key_map.clear()
            self._index_map.clear()
            self._reserved.clear()


class OrderedMapAllocator(MapAllocator[KeyType, IndexType]):
    """Assigns ordered keys to indices in a guaranteed one-to-one mapping. Thread-safe."""

    def __init__(self, key_type: typing.Type[KeyType], index_type: typing.Type[IndexType]):
        super().__init__(key_type, index_type)
        self._sorted_keys = []

    def __setstate__(self, state):
        super().__setstate__(state)
        self._sorted_keys = sorted(self._key_map)

    def __iter__(self) -> typing.Iterator[KeyType]:
        return iter(self._sorted_keys)

    def get(self, key: KeyType, default: IndexType = None, *,
            nearest: bool = False) -> typing.Optional[IndexType]:
        exact = super().get(key)
        if exact is not None:
            return exact
        if nearest:
            sequence_index = bisect.bisect_left(self._sorted_keys, key)
            if sequence_index < len(self._sorted_keys):
                return self[self._sorted_keys[sequence_index]]
            if self._sorted_keys and sequence_index == len(self._sorted_keys):
                return self[self._sorted_keys[-1]]
        return default

    def allocate(self, key: KeyType, index: IndexType, owner: typing.Any = None):
        """Map the given key to the given index. If the key is reserved by a different owner, or
        is reserved by any owner and no owner is provided, raise an exception. If the key is already
        mapped to another index, or another key already maps to the index, raise an exception."""
        super().allocate(key, index, owner)

        assert index is not None
        with self._lock:
            if self._reserved.get(key, owner) is not owner:
                raise KeyError("Key %r is already reserved." % (key,))
            if self._key_map.get(key, index) != index:
                raise KeyError("Key %r is already allocated." % (key,))
            if self._index_map.get(index, key) != key:
                raise KeyError("Index %r is already mapped." % (index,))
            if key in self._reserved:
                del self._reserved[key]
            self._key_map[key] = index
            self._index_map[index] = key
            bisect.insort(self._sorted_keys, key)

    def deallocate(self, key: KeyType) -> IndexType:
        """Remove and return the mapped index for the given key."""
        with self._lock:
            if key not in self._key_map:
                raise KeyError("Key %r is not allocated." % (key,))
            index = self._key_map.pop(key)
            del self._index_map[index]
            sequence_index = bisect.bisect_left(self._sorted_keys, key)
            assert self._sorted_keys[sequence_index] == key
            del self._sorted_keys[sequence_index]
        return index

    # Pylint doesn't understand that other has the same type as self, and no amount of type
    # annotations or assertions seems to change that.
    # pylint: disable=W0212
    def update(self, other: 'MapAllocator', owner: typing.Any = None) -> None:
        """Update the mapping to incorporate the contents of another mapping. Similar in effect to
        dict.update(), except that reservations and mapping conflicts are accounted for."""
        assert self._key_type is other._key_type
        assert self._index_type is other._index_type
        if other is self:
            return
        with self._lock:
            for key, reservation_owner in self._reserved.items():
                if reservation_owner is owner:
                    continue
                old_index = self._key_map.get(key, None)
                new_index = other._key_map.get(key, None)
                if old_index is not None and old_index != new_index:
                    raise KeyError("Key %r is already reserved for %s." % (key, old_index))
            updated_keys = self._key_map.copy()
            updated_keys.update(other._key_map)
            updated_indices = self._index_map.copy()
            updated_indices.update(other._index_map)
            if len(updated_keys) < len(updated_indices):
                raise KeyError("Two or more indices would be assigned to the same key.")
            if len(updated_keys) > len(updated_indices):
                raise KeyError("Two or more keys would be assigned to the same index.")
            self._key_map = updated_keys
            self._index_map = updated_indices
            self._sorted_keys = sorted(self._key_map)

    def clear(self):
        """Remove all key/index mappings and key reservations, returning the allocator to its
        initial state."""
        with self._lock:
            self._key_map.clear()
            self._index_map.clear()
            self._reserved.clear()
            self._sorted_keys.clear()
