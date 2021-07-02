from unittest import TestCase

from semantics.data_structs.controller_data import ControllerData
from semantics.data_structs.element_data import RoleData
from semantics.data_structs.interface import DataInterface
from semantics.data_structs.operation_contexts import Adding, Reading, Finding, Updating, Removing
from semantics.data_structs.transaction_data import TransactionData
from semantics.data_types.indices import RoleID


class MockException(Exception):
    pass


class TestAdding(TestCase):

    def do_test(self, data: DataInterface):
        with Adding(data, RoleID, 'role') as role_data_copy:
            role_id = role_data_copy.index
            self.assertIsInstance(role_data_copy, RoleData)
            self.assertEqual(role_data_copy.name, 'role')
            self.assertNotIn(role_id, data.registry_map[RoleID])
            role_data_copy.data['key'] = 'value'
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertEqual(role_data.data['key'], 'value')

        with self.assertRaises(MockException):
            with Adding(data, RoleID, 'another role') as role_data_copy:
                role_id = role_data_copy.index
                self.assertIsInstance(role_data_copy, RoleData)
                self.assertEqual(role_data_copy.name, 'another role')
                self.assertNotIn(role_id, data.registry_map[RoleID])
                role_data_copy.data['key'] = 'value'
                raise MockException()
        self.assertNotIn(role_id, data.registry_map[RoleID])

    def test_controller_data(self):
        data = ControllerData()
        self.do_test(data)

    def test_transaction_data(self):
        data = TransactionData(ControllerData())
        self.do_test(data)


class TestReading(TestCase):

    def do_test(self, data: DataInterface):
        with data.add(RoleID, 'role') as role_data:
            role_id = role_data.index

        with Reading(data, role_id) as role_data_copy:
            role_id = role_data_copy.index
            self.assertIsInstance(role_data_copy, RoleData)
            self.assertEqual(role_data_copy.name, 'role')
            self.assertIn(role_id, data.registry_map[RoleID])
            role_data_original = data.registry_map[RoleID][role_id]
            self.assertIsNot(role_data_copy, role_data_original)
            role_data_copy.data['key'] = 'value'
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertIsNone(role_data.data.get('key'))

        with self.assertRaises(MockException):
            with Reading(data, role_id) as role_data_copy:
                role_id = role_data_copy.index
                self.assertIsInstance(role_data_copy, RoleData)
                self.assertEqual(role_data_copy.name, 'role')
                self.assertIn(role_id, data.registry_map[RoleID])
                role_data_original = data.registry_map[RoleID][role_id]
                self.assertIsNot(role_data_copy, role_data_original)
                role_data_copy.data['key'] = 'value'
                raise MockException()
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertIsNone(role_data.data.get('key'))

    def test_controller_data(self):
        data = ControllerData()
        self.do_test(data)

    def test_transaction_data(self):
        data = TransactionData(ControllerData())
        self.do_test(data)


class TestFinding(TestCase):

    def do_test(self, data: DataInterface):
        with data.add(RoleID, 'role') as role_data:
            role_id = role_data.index
            data.name_allocator_map[RoleID].allocate('role', role_id)

        with Finding(data, RoleID, 'bad name') as role_data_copy:
            self.assertIsNone(role_data_copy)

        with Finding(data, RoleID, 'role') as role_data_copy:
            role_id = role_data_copy.index
            self.assertIsInstance(role_data_copy, RoleData)
            self.assertEqual(role_data_copy.name, 'role')
            self.assertIn(role_id, data.registry_map[RoleID])
            role_data_original = data.registry_map[RoleID][role_id]
            self.assertIsNot(role_data_copy, role_data_original)
            role_data_copy.data['key'] = 'value'
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertIsNone(role_data.data.get('key'))

        with self.assertRaises(MockException):
            with Finding(data, RoleID, 'role') as role_data_copy:
                role_id = role_data_copy.index
                self.assertIsInstance(role_data_copy, RoleData)
                self.assertEqual(role_data_copy.name, 'role')
                self.assertIn(role_id, data.registry_map[RoleID])
                role_data_original = data.registry_map[RoleID][role_id]
                self.assertIsNot(role_data_copy, role_data_original)
                role_data_copy.data['key'] = 'value'
                raise MockException()
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertIsNone(role_data.data.get('key'))

    def test_controller_data(self):
        data = ControllerData()
        self.do_test(data)

    def test_transaction_data(self):
        data = TransactionData(ControllerData())
        self.do_test(data)


class TestUpdating(TestCase):

    def do_test(self, data: DataInterface):
        with data.add(RoleID, 'role') as role_data:
            role_id = role_data.index
            data.name_allocator_map[RoleID].allocate('role', role_id)

        with self.assertRaises(MockException):
            with Updating(data, role_id) as role_data_copy:
                role_id = role_data_copy.index
                self.assertIsInstance(role_data_copy, RoleData)
                self.assertEqual(role_data_copy.name, 'role')
                self.assertIn(role_id, data.registry_map[RoleID])
                role_data_original = data.registry_map[RoleID][role_id]
                self.assertIsNot(role_data_copy, role_data_original)
                role_data_copy.data['key'] = 'value'
                raise MockException()
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIs(role_data, role_data_original)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertIsNone(role_data.data.get('key'))

        with Updating(data, role_id) as role_data_copy:
            role_id = role_data_copy.index
            self.assertIsInstance(role_data_copy, RoleData)
            self.assertEqual(role_data_copy.name, 'role')
            self.assertIn(role_id, data.registry_map[RoleID])
            role_data_original = data.registry_map[RoleID][role_id]
            self.assertIsNot(role_data_copy, role_data_original)
            role_data_copy.data['key'] = 'value'
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertEqual(role_data.data.get('key'), 'value')

    def test_controller_data(self):
        data = ControllerData()
        self.do_test(data)

    def test_transaction_data(self):
        data = TransactionData(ControllerData())
        self.do_test(data)


class TestRemoving(TestCase):

    def do_test(self, data: DataInterface):
        with data.add(RoleID, 'role') as role_data:
            role_id = role_data.index
            data.name_allocator_map[RoleID].allocate('role', role_id)

        with self.assertRaises(MockException):
            with Removing(data, role_id) as role_data_copy:
                role_id = role_data_copy.index
                self.assertIsInstance(role_data_copy, RoleData)
                self.assertEqual(role_data_copy.name, 'role')
                self.assertIn(role_id, data.registry_map[RoleID])
                role_data_original = data.registry_map[RoleID][role_id]
                self.assertIsNot(role_data_copy, role_data_original)
                role_data_copy.data['key'] = 'value'
                raise MockException()
        self.assertIn(role_id, data.registry_map[RoleID])
        role_data = data.registry_map[RoleID][role_id]
        self.assertIsInstance(role_data, RoleData)
        self.assertIs(role_data, role_data_original)
        self.assertIsNot(role_data, role_data_copy)
        self.assertEqual(role_data.index, role_id)
        self.assertEqual(role_data.name, 'role')
        self.assertIsNone(role_data.data.get('key'))

        with Removing(data, role_id) as role_data_copy:
            role_id = role_data_copy.index
            self.assertIsInstance(role_data_copy, RoleData)
            self.assertEqual(role_data_copy.name, 'role')
            self.assertIn(role_id, data.registry_map[RoleID])
            role_data_original = data.registry_map[RoleID][role_id]
            self.assertIsNot(role_data_copy, role_data_original)
            role_data_copy.data['key'] = 'value'
        self.assertNotIn(role_id, data.registry_map[RoleID])

    def test_controller_data(self):
        data = ControllerData()
        self.do_test(data)

    def test_transaction_data(self):
        data = TransactionData(ControllerData())
        self.do_test(data)
