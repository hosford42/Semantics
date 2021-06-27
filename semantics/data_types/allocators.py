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
        return self._index_type

    @property
    def total_allocated(self) -> int:
        return self._next_id

    def new_id(self) -> IndexType:
        with self._lock:
            allocated_id = self._next_id
            self._next_id += 1
        return self._index_type(allocated_id)


class MapAllocator(typing.Generic[KeyType, IndexType], typing.MutableMapping[KeyType, IndexType]):
    """Assigns names to indices in a guaranteed one-to-one mapping. Thread-safe."""

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
        return self._key_type

    @property
    def index_type(self) -> typing.Type[IndexType]:
        return self._index_type

    def __setitem__(self, key: KeyType, index: IndexType) -> None:
        self.allocate(key, index)

    def __delitem__(self, key: KeyType) -> None:
        self.deallocate(key)

    def __getitem__(self, key: KeyType) -> IndexType:
        return self.get_index(key)

    def __len__(self) -> int:
        return len(self._key_map)

    def __iter__(self) -> typing.Iterator[KeyType]:
        return iter(self._key_map)

    def reserve(self, key: KeyType, owner: typing.Any) -> None:
        with self._lock:
            if self._reserved.get(key, owner) is not owner:
                raise KeyError("Key %r is already reserved." % (key,))
            if key in self._key_map:
                raise KeyError("Key %r is already allocated." % (key,))
            self._reserved[key] = owner

    def cancel_reservation(self, key: KeyType, owner: typing.Any) -> None:
        with self._lock:
            if self._reserved.get(key, None) is not owner:
                raise KeyError("Key %r is not reserved by this owner." % (key,))
            del self._reserved[key]

    def cancel_all_reservations(self, owner: typing.Any) -> None:
        with self._lock:
            keys = []
            for key, reservation_owner in self._reserved.items():
                if reservation_owner is owner:
                    keys.append(key)
            for key in keys:
                del self._reserved[key]

    def allocate(self, key: KeyType, index: IndexType, owner: typing.Any = None):
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
        with self._lock:
            if key not in self._key_map:
                raise KeyError("Key %r is not allocated." % (key,))
            index = self._key_map.pop(key)
            del self._index_map[index]
        return index

    def get_index(self, key: KeyType) -> typing.Optional[IndexType]:
        return self._key_map.get(key, None)

    def get_key(self, index: IndexType) -> typing.Optional[KeyType]:
        return self._index_map.get(index, None)

    def update(self, other: 'MapAllocator', owner: typing.Any = None) -> None:
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
                if old_index != new_index:
                    raise KeyError("Key %r is already reserved." % (key,))
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
        with self._lock:
            self._key_map.clear()
            self._index_map.clear()
            self._reserved.clear()
