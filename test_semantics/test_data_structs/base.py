from abc import ABC, abstractmethod
from collections import deque
from typing import Type
from unittest import TestCase, SkipTest

from semantics.data_control.controllers import Controller
from semantics.data_structs.controller_data import ControllerData
from semantics.data_structs.element_data import RoleData, EdgeData
from semantics.data_structs.interface import DataInterface
from semantics.data_structs.transaction_data import TransactionData
from semantics.data_types import data_access
from semantics.data_types.indices import RoleID, VertexID, LabelID, EdgeID

ORIGINAL_THREAD_ACCESS_MANAGER = data_access.ControllerThreadAccessManager


class DataInterfaceTestCase(TestCase, ABC):

    data_interface_subclass: Type[DataInterface]

    @classmethod
    def setUpClass(cls) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if cls.__name__.startswith('DataInterface') and cls.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % cls.__name__)
        assert hasattr(cls, 'data_interface_subclass'), \
            "You need to define data_interface_subclass in your unit test class %s" % \
            cls.__qualname__

    def setUp(self) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if self.__class__.__name__.startswith('DataInterface') and \
                self.__class__.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % self.__class__.__name__)
        assert hasattr(self, 'data_interface_subclass'), \
            "You need to define data_interface_subclass in your unit test class %s" % \
            self.__class__.__qualname__

        # Monkey patch the ThreadAccessManager class to verify that data element locks are never
        # acquired or released without holding the registry lock. Also, track the call sequence in
        # case we need to see it in the tests.

        self.call_sequence = deque()  # Thread-safe (unlike list type?)
        test_case = self

        class VerifiedThreadAccessManager(ORIGINAL_THREAD_ACCESS_MANAGER):

            def acquire_read(self):
                test_case.call_sequence.append((self.index, 'acquire_read'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().acquire_read()

            def release_read(self):
                test_case.call_sequence.append((self.index, 'release_read'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_read()

            def acquire_write(self):
                test_case.call_sequence.append((self.index, 'acquire_write'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().acquire_write()

            def release_write(self):
                test_case.call_sequence.append((self.index, 'release_write'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_write()

        data_access.ControllerThreadAccessManager = VerifiedThreadAccessManager

        # Create the data and controller *after* monkey patching is done.
        controller_data = ControllerData()
        controller = Controller(data=controller_data)

        self.controller_data = controller_data
        self.transaction_data = controller.new_transaction_data()

        if self.data_interface_subclass is ControllerData:
            self.data_interface = self.controller_data
        else:
            assert self.data_interface_subclass is TransactionData
            self.data_interface = self.transaction_data

        # Populate the database with some pre-existing elements.
        self.preexisting_role_id: RoleID = controller.add_role('preexisting_role')
        self.preexisting_source_id: VertexID = controller.add_vertex(self.preexisting_role_id)
        self.preexisting_sink_id: VertexID = controller.add_vertex(self.preexisting_role_id)
        self.preexisting_label_id: LabelID = controller.add_label('preexisting_label')
        self.preexisting_edge_id: EdgeID = controller.add_edge(self.preexisting_label_id,
                                                               self.preexisting_source_id,
                                                               self.preexisting_sink_id)

        self.call_sequence.clear()

    def tearDown(self) -> None:
        """Tear down after each test is completed."""

        # Undo our monkey-patching of the ThreadAccessManager class
        data_access.ControllerThreadAccessManager = ORIGINAL_THREAD_ACCESS_MANAGER

    @abstractmethod
    def test_add(self):
        registry_stack = self.data_interface.registry_stack_map[RoleID]
        with self.data_interface.add(RoleID, 'role') as data:
            role_id = data.index
            self.assertIsInstance(data, RoleData)
            self.assertEqual(data.name, 'role')
            self.assertNotIn(role_id, registry_stack)
        self.assertIn(role_id, registry_stack)
        data = registry_stack[role_id]
        self.assertIsInstance(data, RoleData)
        self.assertEqual(data.index, role_id)
        self.assertEqual(data.name, 'role')

    @abstractmethod
    def test_read(self):
        registry_stack = self.data_interface.registry_stack_map[RoleID]
        with self.data_interface.read(self.preexisting_role_id) as data:
            self.assertIsInstance(data, RoleData)
            self.assertEqual(self.preexisting_role_id, data.index)
            self.assertEqual(data.name, 'preexisting_role')
            self.assertIsNot(data, registry_stack[self.preexisting_role_id])
            data.data['key'] = 'value'
        self.assertIsNone(registry_stack[self.preexisting_role_id].data.get('key'))

    @abstractmethod
    def test_update(self):
        registry_stack = self.data_interface.registry_stack_map[RoleID]
        with self.data_interface.update(self.preexisting_role_id) as data:
            self.assertIsInstance(data, RoleData)
            self.assertEqual(self.preexisting_role_id, data.index)
            self.assertEqual(data.name, 'preexisting_role')
            self.assertIsNot(data, registry_stack[self.preexisting_role_id])
            data.data['key'] = 'value'
        self.assertEqual(registry_stack[self.preexisting_role_id].data.get('key'), 'value')

    @abstractmethod
    def test_find(self):
        registry_stack = self.data_interface.registry_stack_map[RoleID]
        with self.data_interface.find(RoleID, 'role') as data:
            self.assertIsNone(data)
        with self.data_interface.find(RoleID, 'preexisting_role') as data:
            self.assertIsInstance(data, RoleData)
            self.assertEqual(self.preexisting_role_id, data.index)
            self.assertEqual(data.name, 'preexisting_role')
            self.assertIsNot(data, registry_stack[self.preexisting_role_id])
            data.data['key'] = 'value'
        self.assertIsNone(registry_stack[self.preexisting_role_id].data.get('key'))

    @abstractmethod
    def test_remove(self):
        registry_stack = self.data_interface.registry_stack_map[EdgeID]
        with self.data_interface.remove(self.preexisting_edge_id) as data:
            self.assertIsInstance(data, EdgeData)
            self.assertEqual(self.preexisting_edge_id, data.index)
            self.assertEqual(data.label, self.preexisting_label_id)
            self.assertIsNot(data, registry_stack[self.preexisting_edge_id])
            data.data['key'] = 'value'
        with self.data_interface.registry_lock:
            with self.assertRaises(KeyError):
                self.data_interface.get_data(self.preexisting_edge_id)

    @abstractmethod
    def test_get_data(self):
        registry_stack = self.data_interface.registry_stack_map[EdgeID]
        with self.data_interface.registry_lock:
            data = self.data_interface.get_data(self.preexisting_edge_id)
        self.assertIs(data, registry_stack[self.preexisting_edge_id])
        with self.data_interface.remove(self.preexisting_edge_id):
            pass
        with self.data_interface.registry_lock:
            with self.assertRaises(KeyError):
                self.data_interface.get_data(self.preexisting_edge_id)
