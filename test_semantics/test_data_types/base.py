from abc import ABC, abstractmethod
from unittest import TestCase, SkipTest

import typing

from semantics.data_types.allocators import MapAllocator
from semantics.data_types.indices import VertexID, EdgeID


class MapAllocatorTestCase(TestCase, ABC):

    map_allocator_type: typing.Type[MapAllocator]

    @classmethod
    def setUpClass(cls) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if cls.__name__.startswith('MapAllocator') and cls.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % cls.__name__)
        assert hasattr(cls, 'map_allocator_type'), \
            "You need to define map_allocator_type in your unit test class %s" % \
            cls.__qualname__

    @abstractmethod
    def test_key_type(self):
        allocator1 = self.map_allocator_type(str, VertexID)
        allocator2 = self.map_allocator_type(int, EdgeID)
        self.assertIs(allocator1.key_type, str)
        self.assertIs(allocator2.key_type, int)

    @abstractmethod
    def test_index_type(self):
        allocator1 = self.map_allocator_type(str, VertexID)
        allocator2 = self.map_allocator_type(str, EdgeID)
        self.assertIs(allocator1.index_type, VertexID)
        self.assertIs(allocator2.index_type, EdgeID)

    @abstractmethod
    def test_set_item(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator['a'] = VertexID(0)
        allocator[VertexID(1)] = 'b'
        self.assertEqual(VertexID(0), allocator.get_index('a'))
        self.assertEqual(VertexID(1), allocator.get_index('b'))

    @abstractmethod
    def test_del_item(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.allocate('b', VertexID(1))
        del allocator['a']
        del allocator[VertexID(1)]
        self.assertEqual(0, len(allocator))

    @abstractmethod
    def test_get_item(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.allocate('b', VertexID(1))
        self.assertEqual(VertexID(0), allocator['a'])
        self.assertEqual('b', allocator[VertexID(1)])

    @abstractmethod
    def test_is_reserved(self):
        allocator = self.map_allocator_type(str, VertexID)
        self.assertFalse(allocator.is_reserved('a'))
        allocator.reserve('a', 'A')
        self.assertTrue(allocator.is_reserved('a'))

    @abstractmethod
    def test_reserve(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.reserve('a', 'A')
        with self.assertRaises(KeyError):
            # Once it's reserved for one owner, another owner cannot reserve it.
            allocator.reserve('a', 'B')
        allocator.reserve('a', 'A')  # Multiple requests for the same reservation will succeed
        with self.assertRaises(KeyError):
            # Reservation blocks another owner from allocating it
            allocator.allocate('a', VertexID(0), 'B')
        with self.assertRaises(KeyError):
            # Reservation blocks an anonymous owner from allocating it
            allocator.allocate('a', VertexID(0))
        # Reservation does not block same owner from allocating it
        allocator.allocate('a', VertexID(0), 'A')
        with self.assertRaises(KeyError):
            # When it's allocated, it cannot be reserved by a different owner
            allocator.reserve('a', 'B')
        with self.assertRaises(KeyError):
            # When it's allocated, it cannot be reserved again by the same owner
            allocator.reserve('a', 'A')

    @abstractmethod
    def test_cancel_reservation(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.reserve('a', 'A')
        with self.assertRaises(KeyError):
            # Reservation by one owner cannot be canceled by another owner
            allocator.cancel_reservation('a', 'B')
        with self.assertRaises(KeyError):
            # Reservation for an unreserved resource cannot be canceled
            allocator.cancel_reservation('b', 'A')
        allocator.cancel_reservation('a', 'A')
        # Canceling reservation does not block allocation by same owner
        allocator.allocate('a', VertexID(0), 'a')
        allocator.reserve('b', 'A')
        allocator.cancel_reservation('b', 'A')
        # Canceling reservation enables allocation by another owner
        allocator.allocate('b', VertexID(1), 'B')
        allocator.reserve('c', 'A')
        allocator.cancel_reservation('c', 'A')
        allocator.reserve('c', 'A')  # Canceling reservation allows re-reservation by same owner
        allocator.reserve('d', 'A')
        allocator.cancel_reservation('d', 'A')
        allocator.reserve('d', 'B')  # Canceling reservation allows reservation by another owner

    @abstractmethod
    def test_cancel_all_reservations(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.reserve('a', 'A')
        allocator.reserve('b', 'A')
        allocator.reserve('c', 'B')
        allocator.cancel_all_reservations('A')
        allocator.reserve('a', 'B')  # Canceling all reservations allows reservation by another
        allocator.reserve('b', 'B')  # Canceling all reservations allows reservation by another
        with self.assertRaises(KeyError):
            allocator.reserve('c', 'A')  # Other owners are unaffected

    @abstractmethod
    def test_allocate(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.allocate('b', VertexID(1))  # Allocation succeeds for new name and new ID
        with self.assertRaises(KeyError):
            allocator.allocate('a', VertexID(2))  # Names must be unique
        with self.assertRaises(KeyError):
            allocator.allocate('c', VertexID(0))  # IDs must be unique
        allocator.allocate('a', VertexID(0))  # Identical repeat of existing allocation succeeds

    @abstractmethod
    def test_deallocate(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.deallocate('a')
        allocator.allocate('a', VertexID(1))  # Deallocated name can be reallocated
        allocator.allocate('b', VertexID(0))  # Deallocated ID can be reallocated

    @abstractmethod
    def test_deallocate_nonexistent_key(self):
        allocator = self.map_allocator_type(str, VertexID)
        with self.assertRaises(KeyError):
            allocator.deallocate('a')

    @abstractmethod
    def test_get_index(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.allocate('b', VertexID(1))
        self.assertEqual(allocator.get_index('a'), VertexID(0))  # Returns previously assigned index
        self.assertEqual(allocator.get_index('b'), VertexID(1))  # Returns previously assigned index
        # Rejects request for name with no assigned index
        self.assertIsNone(allocator.get_index('c'))
        allocator.deallocate('a')
        # Deallocation causes index assignment to be revoked
        self.assertIsNone(allocator.get_index('a'))
        # Unaffected by deallocation of a different name
        self.assertEqual(allocator.get_index('b'), VertexID(1))

    @abstractmethod
    def test_get_key(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.allocate('b', VertexID(1))
        # Returns previously assigned name for index
        self.assertEqual(allocator.get_key(VertexID(0)), 'a')
        # Returns previously assigned name for index
        self.assertEqual(allocator.get_key(VertexID(1)), 'b')
        # Rejects request for name with no assigned index
        self.assertIsNone(allocator.get_key(VertexID(2)))
        allocator.deallocate('a')
        # Deallocation causes index assignment to be revoked
        self.assertIsNone(allocator.get_key(VertexID(0)))
        # Unaffected by deallocation of a different name
        self.assertEqual(allocator.get_key(VertexID(1)), 'b')

    @abstractmethod
    def test_update(self):
        allocator1 = self.map_allocator_type(str, VertexID)
        allocator1.allocate('a', VertexID(0))
        allocator1.allocate('b', VertexID(2))
        allocator1.allocate('c', VertexID(3))
        allocator2 = self.map_allocator_type(str, VertexID)
        allocator2.allocate('b', VertexID(3))
        allocator2.allocate('c', VertexID(2))
        allocator2.allocate('d', VertexID(4))
        allocator1.update(allocator2)
        self.assertEqual(allocator1.get_index('a'), VertexID(0))  # 'a' is not overwritten
        self.assertEqual(allocator1.get_index('b'), VertexID(3))  # 'b' is overwritten
        self.assertEqual(allocator1.get_index('c'), VertexID(2))  # 'c' is overwritten
        self.assertEqual(allocator1.get_index('d'), VertexID(4))  # 'd' is added
        self.assertEqual(allocator1.get_key(VertexID(0)), 'a')  # 0 is not overwritten
        self.assertEqual(allocator1.get_key(VertexID(3)), 'b')  # 3 is overwritten
        self.assertEqual(allocator1.get_key(VertexID(2)), 'c')  # 0 is overwritten
        self.assertEqual(allocator1.get_key(VertexID(4)), 'd')  # 4 is added

        allocator1 = self.map_allocator_type(str, VertexID)
        allocator1.allocate('a', VertexID(0))
        allocator2 = self.map_allocator_type(str, VertexID)
        allocator2.allocate('b', VertexID(0))
        with self.assertRaises(KeyError):
            allocator1.update(allocator2)  # 2 names cannot be assigned to same index

        allocator1 = self.map_allocator_type(str, VertexID)
        allocator1.allocate('a', VertexID(0))
        allocator2 = self.map_allocator_type(str, VertexID)
        allocator2.allocate('a', VertexID(1))
        with self.assertRaises(KeyError):
            allocator1.update(allocator2)  # 2 indices cannot be assigned to same name

    @abstractmethod
    def test_update_from_self(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.update(allocator)
        self.assertEqual(VertexID(0), allocator['a'])
        self.assertEqual(1, len(allocator))

    @abstractmethod
    def test_clear(self):
        allocator = self.map_allocator_type(str, VertexID)
        allocator.allocate('a', VertexID(0))
        allocator.reserve('c', 'C')
        allocator.clear()
        allocator.allocate('a', VertexID(1))  # After clear, all names are no longer allocated
        allocator.allocate('b', VertexID(0))  # After clear, all indices are no longer allocated
        allocator.allocate('c', VertexID(2), 'A')  # After clear, all reservations are canceled
