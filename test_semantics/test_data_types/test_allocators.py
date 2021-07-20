from unittest import TestCase

from semantics.data_types.allocators import IndexAllocator, MapAllocator, OrderedMapAllocator
from semantics.data_types.indices import VertexID, EdgeID

from test_semantics.test_data_types import base


class TestIndexAllocator(TestCase):

    def test_index_type(self):
        allocator1 = IndexAllocator(VertexID)
        allocator2 = IndexAllocator(EdgeID)
        self.assertIs(allocator1.index_type, VertexID)
        self.assertIs(allocator2.index_type, EdgeID)

    def test_new_id(self):
        allocator = IndexAllocator(VertexID)
        index1 = allocator.new_id()
        self.assertIsInstance(index1, VertexID)
        index2 = allocator.new_id()
        self.assertIsInstance(index2, VertexID)
        self.assertNotEqual(index1, index2)

    def test_total_allocated(self):
        allocator = IndexAllocator(VertexID)
        self.assertEqual(allocator.total_allocated, 0)
        allocator.new_id()
        self.assertEqual(allocator.total_allocated, 1)
        allocator.new_id()
        self.assertEqual(allocator.total_allocated, 2)


class TestMapAllocator(base.MapAllocatorTestCase):
    
    map_allocator_type = MapAllocator

    def test_key_type(self):
        super().test_key_type()

    def test_index_type(self):
        super().test_index_type()

    def test_set_item(self):
        super().test_set_item()

    def test_del_item(self):
        super().test_del_item()

    def test_get_item(self):
        super().test_get_item()

    def test_is_reserved(self):
        super().test_is_reserved()

    def test_reserve(self):
        super().test_reserve()

    def test_cancel_reservation(self):
        super().test_cancel_reservation()

    def test_cancel_all_reservations(self):
        super().test_cancel_all_reservations()

    def test_allocate(self):
        super().test_allocate()

    def test_deallocate(self):
        super().test_deallocate()

    def test_deallocate_nonexistent_key(self):
        super().test_deallocate_nonexistent_key()

    def test_get_index(self):
        super().test_get_index()

    def test_get_key(self):
        super().test_get_key()

    def test_update(self):
        super().test_update()

    def test_update_from_self(self):
        super().test_update_from_self()

    def test_clear(self):
        super().test_clear()


class TestOrderedMapAllocator(base.MapAllocatorTestCase):

    map_allocator_type = OrderedMapAllocator

    # TODO: Tests specific to OrderedMapAllocator

    def test_key_type(self):
        super().test_key_type()

    def test_index_type(self):
        super().test_index_type()

    def test_set_item(self):
        super().test_set_item()

    def test_del_item(self):
        super().test_del_item()

    def test_get_item(self):
        super().test_get_item()

    def test_is_reserved(self):
        super().test_is_reserved()

    def test_reserve(self):
        super().test_reserve()

    def test_cancel_reservation(self):
        super().test_cancel_reservation()

    def test_cancel_all_reservations(self):
        super().test_cancel_all_reservations()

    def test_allocate(self):
        super().test_allocate()

    def test_deallocate(self):
        super().test_deallocate()

    def test_deallocate_nonexistent_key(self):
        super().test_deallocate_nonexistent_key()

    def test_get_index(self):
        super().test_get_index()

    def test_get_key(self):
        super().test_get_key()

    def test_update(self):
        super().test_update()

    def test_update_from_self(self):
        super().test_update_from_self()

    def test_clear(self):
        super().test_clear()
