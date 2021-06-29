from unittest import TestCase

from semantics.data_structs.transaction_data import TransactionData
from test_semantics.test_data_structs import base as base


class TestTransactionData(TestCase):

    def test_allocate_name(self):
        self.fail()

    def test_deallocate_name(self):
        self.fail()

    def test_allocate_time_stamp(self):
        self.fail()


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