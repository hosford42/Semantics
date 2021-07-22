from unittest import TestCase

from semantics.data_control.controllers import Controller
from semantics.data_control.transactions import Transaction
from semantics.data_structs.controller_data import ControllerData
from semantics.data_structs.transaction_data import TransactionData
from semantics.data_types.indices import VertexID, RoleID
from semantics.data_types.typedefs import TimeStamp
from test_semantics.test_data_structs import base as base


class TestTransactionData(TestCase):

    def setUp(self) -> None:
        controller_data = ControllerData()
        controller = Controller(data=controller_data)
        self.controller = controller
        self.transaction = Transaction(controller)
        self.data = self.transaction._data

    def test_access_to_deleted_item(self):
        role_id = self.controller.add_role('role')
        self.transaction.remove_role(role_id)
        with self.data.registry_lock:
            with self.assertRaises(KeyError):
                self.data.access(role_id)

    def test_allocate_name(self):
        self.data.allocate_name('name', VertexID(100))
        self.assertEqual(self.data.name_allocator_map[VertexID]['name'], VertexID(100))

    def test_allocate_unavailable_name(self):
        self.controller.add_role('role')
        with self.assertRaises(KeyError):
            self.data.allocate_name('role', self.data.id_allocator_map[RoleID].new_id())
        self.assertNotIn('role', self.data.name_allocator_map[RoleID].keys())
        self.assertFalse(self.data.name_allocator_map[RoleID].is_reserved('role'))
        self.assertIn('role', self.data.controller_data.name_allocator_map[RoleID].keys())

    def test_deallocate_name(self):
        self.data.allocate_name('name', VertexID(100))
        with self.assertRaises(AssertionError):
            self.data.deallocate_name('name', VertexID(1000))
        with self.assertRaises(AssertionError):
            self.data.deallocate_name('another name', VertexID(100))
        self.data.deallocate_name('name', VertexID(100))
        with self.data.find(VertexID, 'name') as data:
            self.assertIsNone(data)

    def test_allocate_time_stamp(self):
        self.data.allocate_time_stamp(TimeStamp(3.14159), VertexID(100))
        self.assertEqual(self.data.vertex_time_stamp_allocator[TimeStamp(3.14159)], VertexID(100))

    def test_allocate_unavailable_time_stamp(self):
        time_stamp = TimeStamp(3.14159)
        self.data.controller_data.allocate_time_stamp(time_stamp,
                                                      self.data.id_allocator_map[VertexID].new_id())
        with self.assertRaises(KeyError):
            self.data.allocate_time_stamp(time_stamp, self.data.id_allocator_map[VertexID].new_id())
        self.assertNotIn(time_stamp, self.data.vertex_time_stamp_allocator.keys())
        self.assertFalse(self.data.vertex_time_stamp_allocator.is_reserved(time_stamp))
        self.assertIn(time_stamp, self.data.controller_data.vertex_time_stamp_allocator.keys())


class TestDataInterfaceForTransactionData(base.DataInterfaceTestCase):

    data_interface_subclass = TransactionData

    def test_add(self):
        super().test_add()

    def test_read(self):
        super().test_read()

    def test_update(self):
        super().test_update()

    def test_find(self):
        super().test_find()

    def test_remove(self):
        super().test_remove()

    def test_get_data(self):
        super().test_get_data()
