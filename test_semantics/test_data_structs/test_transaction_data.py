from unittest import TestCase

from semantics.data_control.controllers import Controller
from semantics.data_structs.controller_data import ControllerData
from semantics.data_structs.transaction_data import TransactionData
from semantics.data_types.indices import VertexID
from semantics.data_types.typedefs import TimeStamp
from test_semantics.test_data_structs import base as base


class TestTransactionData(TestCase):

    def setUp(self) -> None:
        controller_data = ControllerData()
        controller = Controller(data=controller_data)
        self.data = controller.new_transaction_data()

    def test_allocate_name(self):
        self.data.allocate_name('name', VertexID(100))
        self.assertEqual(self.data.name_allocator_map[VertexID]['name'], VertexID(100))

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
