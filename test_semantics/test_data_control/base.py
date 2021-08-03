"""
Test case base classes for shared functionality defined in BaseController.
"""

import contextlib
import uuid
from abc import ABC, abstractmethod
from collections import deque
from functools import wraps
from typing import Callable, Type, Optional
from unittest import TestCase, SkipTest

from semantics.data_control.base import BaseController
from semantics.data_control.controllers import Controller
from semantics.data_control.transactions import Transaction
from semantics.data_structs.controller_data import ControllerData
from semantics.data_types import data_access
from semantics.data_types.exceptions import ResourceUnavailableError
from semantics.data_types.indices import LabelID, RoleID, PersistentDataID, ReferenceID, VertexID, \
    EdgeID
from test_semantics.test_data_types.test_data_access import threaded_call, threaded_context

ORIGINAL_CONTROLLER_THREAD_ACCESS_MANAGER = data_access.ControllerThreadAccessManager
ORIGINAL_TRANSACTION_THREAD_ACCESS_MANAGER = data_access.TransactionThreadAccessManager


def check_ref_lock(method: Callable[['BaseControllerTestCase'], None]) \
        -> Callable[[], None]:
    """
    Decorator for BaseControllerTestCase tests to verify:
        * The registry lock is not held before the method call.
        * The registry lock is not held after the method call.
    """

    # We could technically accomplish the same thing in the setUp() and tearDown methods, but then
    # we wouldn't be able to tell which test caused the problem. And who wants to debug a test suite
    # when the message can just tell you?

    @wraps(method)
    def wrapper(self):
        # The registry lock is not held before the method call.
        self.assertFalse(self.data_interface.registry_lock.locked(),
                         "Registry lock was not released before %s() began." % method.__name__)
        method(self)
        # The registry lock is not held after the method call.
        self.assertFalse(self.data_interface.registry_lock.locked(),
                         "Registry lock was still held after %s() completed." % method.__name__)

    return wrapper


class BaseControllerTestCase(TestCase, ABC):
    """Base class for test cases of BaseController and its subtypes."""

    base_controller_subclass: Type[BaseController]

    @classmethod
    def setUpClass(cls) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if cls.__name__.startswith('BaseController') and cls.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % cls.__name__)
        assert hasattr(cls, 'base_controller_subclass'), \
            "You need to define base_controller_subclass in your unit test class %s" % \
            cls.__qualname__

    def setUp(self) -> None:
        """Set up before each test begins."""

        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if self.__class__.__name__.startswith('BaseController') and \
                self.__class__.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % self.__class__.__name__)
        assert hasattr(self, 'base_controller_subclass'), \
            "You need to define base_controller_subclass in your unit test class %s" % \
            self.__class__.__qualname__

        # Monkey patch the ThreadAccessManager class to verify that data element locks are never
        # acquired or released without holding the registry lock. Also, track the call sequence in
        # case we need to see it in the tests.

        self.call_sequence = deque()  # Thread-safe (unlike list type?)
        test_case = self

        class VerifiedControllerThreadAccessManager(ORIGINAL_CONTROLLER_THREAD_ACCESS_MANAGER):

            def acquire_read(self):
                test_case.call_sequence.append(('controller', self.index, 'acquire_read'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().acquire_read()

            def release_read(self):
                test_case.call_sequence.append(('controller', self.index, 'release_read'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_read()

            def acquire_write(self):
                test_case.call_sequence.append(('controller', self.index, 'acquire_write'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().acquire_write()

            def release_write(self):
                test_case.call_sequence.append(('controller', self.index, 'release_write'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_write()

        class VerifiedTransactionThreadAccessManager(ORIGINAL_TRANSACTION_THREAD_ACCESS_MANAGER):

            def release_controller_read_lock(self) -> None:
                test_case.call_sequence.append(('transaction', self.index,
                                                'release_controller_read_lock'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_controller_read_lock()

            def release_controller_write_lock(self) -> None:
                test_case.call_sequence.append(('transaction', self.index,
                                                'release_controller_write_lock'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_controller_write_lock()

            def acquire_read(self):
                test_case.call_sequence.append(('transaction', self.index, 'acquire_read'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().acquire_read()

            def release_read(self):
                test_case.call_sequence.append(('transaction', self.index, 'release_read'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_read()

            def acquire_write(self):
                test_case.call_sequence.append(('transaction', self.index, 'acquire_write'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().acquire_write()

            def release_write(self):
                test_case.call_sequence.append(('transaction', self.index, 'release_write'))
                test_case.assertTrue(test_case.data_interface.registry_lock.locked())
                super().release_write()

        data_access.ControllerThreadAccessManager = VerifiedControllerThreadAccessManager
        data_access.TransactionThreadAccessManager = VerifiedTransactionThreadAccessManager

        # Create the data and controller *after* monkey patching is done.
        self.data = ControllerData()
        self.controller = Controller(data=self.data)
        self.transaction = Transaction(self.controller)
        self.transaction_data = self.transaction._data
        if self.base_controller_subclass is Controller:
            self.data_interface = self.data
            self.controller_interface = self.controller
            self.interface_name = 'controller'
        else:
            assert self.base_controller_subclass is Transaction
            self.data_interface = self.transaction_data
            self.controller_interface = self.transaction
            self.interface_name = 'transaction'

        # Populate the database with some pre-existing elements.
        self.preexisting_role_id: RoleID = self.controller.add_role('preexisting_role')
        self.preexisting_source_id: VertexID = self.controller.add_vertex(self.preexisting_role_id)
        self.preexisting_sink_id: VertexID = self.controller.add_vertex(self.preexisting_role_id)
        self.preexisting_label_id: LabelID = self.controller.add_label('preexisting_label')
        self.preexisting_edge_id: EdgeID = self.controller.add_edge(self.preexisting_label_id,
                                                                    self.preexisting_source_id,
                                                                    self.preexisting_sink_id)

        self.call_sequence.clear()

    def tearDown(self) -> None:
        """Tear down after each test is completed."""

        # Undo our monkey-patching of the ThreadAccessManager class
        data_access.ControllerThreadAccessManager = ORIGINAL_CONTROLLER_THREAD_ACCESS_MANAGER
        data_access.TransactionThreadAccessManager = ORIGINAL_TRANSACTION_THREAD_ACCESS_MANAGER

    @contextlib.contextmanager
    def in_use(self, element_id):
        """Create temporary elements to ensure that the given element index is in use.
        Only valid for role and label indices."""
        assert isinstance(element_id, (RoleID, LabelID))
        if isinstance(element_id, RoleID):
            temp_role = None
            temp_vertex = self.controller_interface.add_vertex(element_id)
            temp_edge = None
        else:
            temp_role = self.controller_interface.add_role(str(uuid.uuid4()))
            temp_vertex = self.controller_interface.add_vertex(temp_role)
            temp_edge = self.controller_interface.add_edge(element_id, temp_vertex, temp_vertex)
        try:
            yield
        finally:
            if temp_edge is not None:
                self.controller_interface.remove_edge(temp_edge)
            self.controller_interface.remove_vertex(temp_vertex)
            if temp_role is not None:
                self.controller_interface.remove_role(temp_role)

    @contextlib.contextmanager
    def read_locked(self, element_id, level='controller'):
        if level == 'controller':
            data_interface = self.data
        else:
            self.assertEqual('transaction', level)
            data_interface = self.transaction_data
        with data_interface.registry_lock:
            access_manager = data_interface.access(element_id)
            access_manager.acquire_read()
        try:
            yield
        finally:
            with data_interface.registry_lock:
                access_manager.release_read()

    @contextlib.contextmanager
    def write_locked(self, element_id, level='controller'):
        if level == 'controller':
            data_interface = self.data
        else:
            self.assertEqual('transaction', level)
            data_interface = self.transaction_data
        with data_interface.registry_lock:
            access_manager = data_interface.access(element_id)
            access_manager.acquire_write()
        try:
            yield
        finally:
            with data_interface.registry_lock:
                access_manager.release_write()


class BaseControllerReferencesTestCase(BaseControllerTestCase):

    @check_ref_lock
    @abstractmethod
    def test_new_reference_id(self):
        """
        Verify:
            * On success, returns new reference ID.
            * New reference IDs are never equal to previous ones
        """
        previous_ids = set()
        for _ in range(1000):
            new_id = self.controller_interface.new_reference_id()
            self.assertIsInstance(new_id, ReferenceID)
            self.assertNotIn(new_id, previous_ids)
            previous_ids.add(new_id)

    @check_ref_lock
    @abstractmethod
    def test_acquire_reference(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * Reference ID is already acquired and has not been released.
            * Succeeds if:
                * Reference ID has never been acquired.
                * Reference ID was released since it was last acquired.
                * Other reference IDs to the same element have been acquired.
            * On success:
                * The element's read lock is acquired and not released.
        """
        invalid_id = LabelID(-1)
        valid_id = self.controller_interface.add_label('test_label')
        reference_id = self.controller_interface.new_reference_id()
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            self.controller_interface.acquire_reference(reference_id, invalid_id)
        # Succeed if reference ID has never been acquired.
        self.controller_interface.acquire_reference(reference_id, valid_id)
        # On success, the element's read lock is acquired and not released.
        self.assertIn((self.interface_name, valid_id, 'acquire_read'), self.call_sequence)
        self.assertNotIn((self.interface_name, valid_id, 'release_read'), self.call_sequence)
        # AssertionError because this represents a programming bug in the graph layer.
        with self.assertRaises(AssertionError):
            # Fail if reference ID is already acquired and has not been released.
            self.controller_interface.acquire_reference(reference_id, valid_id)
        # Succeed if reference ID was released since it was last acquired.
        self.controller_interface.release_reference(reference_id, valid_id)
        self.controller_interface.acquire_reference(reference_id, valid_id)
        # Succeed if other reference IDs to the same element have been acquired.
        second_reference_id = self.controller_interface.new_reference_id()
        self.controller_interface.acquire_reference(second_reference_id, valid_id)

    @check_ref_lock
    @abstractmethod
    def test_release_reference(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * Reference ID has never been acquired.
                * Reference ID was released since it was last acquired.
                * Attempting to release the wrong element ID in association with the given reference
                  ID.
            * Succeeds if:
                * Reference ID has been acquired and has never been released.
                * Reference ID was re-acquired after it was last released.
                * Other reference IDs to the same element have already been released.
            * On success:
                * The element's read lock is released.
        """
        invalid_id = LabelID(-1)
        valid_id = self.controller_interface.add_label('test_label')
        wrong_valid_id = self.controller_interface.add_label('test_label_2')
        reference_id = self.controller_interface.new_reference_id()
        # AssertionError because this represents a programming bug in the graph layer.
        with self.assertRaises(AssertionError):
            # Fail if reference ID has never been acquired.
            self.controller_interface.release_reference(reference_id, valid_id)
        self.controller_interface.acquire_reference(reference_id, valid_id)
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            self.controller_interface.release_reference(reference_id, invalid_id)
        # AssertionError because this represents a programming bug in the graph layer.
        with self.assertRaises(AssertionError):
            # Attempting to release the wrong element ID in association with the given reference ID.
            self.controller_interface.release_reference(reference_id, wrong_valid_id)
        # Succeed if reference ID has been acquired and has never been released.
        self.controller_interface.release_reference(reference_id, valid_id)
        # On success, the element's read lock is released.
        self.assertIn((self.interface_name, valid_id, 'release_read'), self.call_sequence)
        # AssertionError because this represents a programming bug in the graph layer.
        with self.assertRaises(AssertionError):
            # Fail if reference ID was released since it was last acquired.
            self.controller_interface.release_reference(reference_id, valid_id)
        # Succeed if reference ID was re-acquired after it was last released.
        self.controller_interface.acquire_reference(reference_id, valid_id)
        self.controller_interface.release_reference(reference_id, valid_id)
        # Succeed if other reference IDs to the same element have already been released.
        self.controller_interface.acquire_reference(reference_id, valid_id)
        other_reference_id = self.controller_interface.new_reference_id()
        self.controller_interface.acquire_reference(other_reference_id, valid_id)
        self.controller_interface.release_reference(other_reference_id, valid_id)
        self.controller_interface.release_reference(reference_id, valid_id)


class CategoricalElementBaseControllerTestCase(BaseControllerTestCase):
    """Base class for test cases for base controller interactions with categorical
    graph elements -- roles and labels. They work pretty much identically, so the
    tests are combined."""

    tested_element_type_name: str
    other_element_type_name: str
    tested_element_index_type: Type[PersistentDataID]

    def add(self, name: str, *, level=None) -> PersistentDataID:
        if level is None:
            controller_interface = self.controller_interface
        elif level == 'controller':
            controller_interface = self.controller
        else:
            assert level == 'transaction'
            controller_interface = self.transaction
        method = getattr(controller_interface, 'add_%s' % self.tested_element_type_name)
        return method(name)

    def add_other_type(self, name: str) -> PersistentDataID:
        method = getattr(self.controller_interface, 'add_%s' % self.other_element_type_name)
        return method(name)

    def remove(self, index: PersistentDataID) -> None:
        method = getattr(self.controller_interface, 'remove_%s' % self.tested_element_type_name)
        method(index)

    def get_name(self, index: PersistentDataID) -> Optional[str]:
        method = getattr(self.controller_interface, 'get_%s_name' % self.tested_element_type_name)
        return method(index)

    def find(self, name: str) -> Optional[PersistentDataID]:
        method = getattr(self.controller_interface, 'find_%s' % self.tested_element_type_name)
        return method(name)

    @check_ref_lock
    @abstractmethod
    def test_add(self):
        """
        Verify:
            * Fails if:
                * An element of the same type and name exists.
            * Succeeds if:
                * Elements of another type with the same name already exist.
            * On success:
                * Returns the new element's ID.
                * The new element exists.
                * The element has the given name.
        """
        # Succeeds if elements of another type with the same name already exist.
        self.add_other_type('test')
        index = self.add('test')
        # On success, returns the new ID.
        self.assertIsInstance(index, self.tested_element_index_type)
        # Fails if an element with the same type and name exists.
        with self.assertRaises(KeyError):
            self.add('test')
        # On success, the new element exists and has the given name.
        self.assertEqual('test', self.get_name(index))

    @check_ref_lock
    @abstractmethod
    def test_remove(self):
        """
        Verify:
            * Fails if:
                * The element doesn't exist.
                * The element is in use.
                * Any of the element's locks are held by another thread.
            * On success:
                * Element no longer exists.
        """
        index = self.add('test')
        with self.in_use(index):
            # Fail if the element is in use.
            with self.assertRaises(ResourceUnavailableError):
                self.remove(index)
        self.remove(index)
        # On success, element no longer exists.
        with self.assertRaises(KeyError):
            self.get_name(index)
        # Fail if the element doesn't exist.
        with self.assertRaises(KeyError):
            self.remove(index)

    @check_ref_lock
    @abstractmethod
    def test_remove_locked(self):
        index = self.add('test', level='controller')

        # Fail if the element's read lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(index)):
                self.remove(index)

        # Fail if the element's write lock is held by another thread..
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(index)):
                self.remove(index)

    @check_ref_lock
    @abstractmethod
    def test_get_name(self):
        """
        Verify:
            * Fails if:
                * The element doesn't exist.
                * A write lock to the element is held elsewhere.
            * On success:
                * The correct name is returned.
        """
        invalid_id = self.tested_element_index_type(-1)
        # Fail if the element doesn't exist.
        with self.assertRaises(KeyError):
            self.get_name(invalid_id)
        index = self.add('test')
        # On success, the correct name is returned.
        self.assertEqual('test', self.get_name(index))

    @check_ref_lock
    @abstractmethod
    def test_get_name_locked(self):
        index = self.add('test', level='controller')
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(index)):
                # Fail if a write lock to the element is held by another thread.
                self.get_name(index)

    @check_ref_lock
    @abstractmethod
    def test_find(self):
        """
        Verify:
            * Succeeds if:
                * An element of a different type with the same name exists.
                * No element with the same type and name exists.
            * On success:
                * If element with the given name exists, returns it.
                * If no element with the given name exists, returns None.
        """
        self.add_other_type('test')
        index = self.add('test')
        # Succeed if an element of a different type with the same name exists.
        result = self.find('test')
        # On success, if element with the given name exists, returns it.
        self.assertEqual(result, index)
        # Succeed if no element with the given name exists.
        result = self.find('nonexistent')
        # On success, if no element with the given name exists, return None.
        self.assertIsNone(result)


class BaseControllerRolesTestCase(CategoricalElementBaseControllerTestCase, ABC):

    tested_element_type_name: str = 'role'
    other_element_type_name: str = 'label'
    tested_element_index_type: Type[PersistentDataID] = RoleID


class BaseControllerLabelsTestCase(CategoricalElementBaseControllerTestCase, ABC):

    tested_element_type_name: str = 'label'
    other_element_type_name: str = 'role'
    tested_element_index_type: Type[PersistentDataID] = LabelID


class BaseControllerVerticesTestCase(BaseControllerTestCase):

    @check_ref_lock
    @abstractmethod
    def test_add_vertex(self):
        """
        Verify:
            * Fails if:
                * Preferred role does not exist.
                * Preferred role is locked for write by another thread.
            * On success:
                * New vertex has:
                    * No name, time stamp, or edges.
                    * A unique vertex id.
                    * Correct preferred role.
        """
        invalid_role_id = RoleID(-1)
        # Fail if preferred role does not exist.
        with self.assertRaises(KeyError):
            self.controller_interface.add_vertex(invalid_role_id)
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        # On success, new vertex has no edges.
        self.assertEqual(self.controller_interface.count_vertex_inbound(vertex_id), 0)
        self.assertEqual(self.controller_interface.count_vertex_outbound(vertex_id), 0)
        # On success, vertex has correct preferred role.
        self.assertEqual(self.controller_interface.get_vertex_preferred_role(vertex_id), role_id)

    @check_ref_lock
    @abstractmethod
    def test_add_vertex_locked_role(self):
        role_id = self.controller.add_role('test_role')
        _vertex_id = self.controller.add_vertex(role_id)

        # Fail if preferred role is locked for write by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(role_id)):
                self.controller_interface.add_vertex(role_id)

    @check_ref_lock
    @abstractmethod
    def test_get_vertex_preferred_role(self):
        """
        Verify:
            * Fails if:
                * The vertex does not exist.
                * The vertex's write lock is held elsewhere.
            * On success:
                * Returns the correct role.
        """
        invalid_id = VertexID(-1)
        with self.assertRaises(KeyError):
            # Fails if the vertex does not exist.
            self.controller_interface.get_vertex_preferred_role(invalid_id)
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        # On success, returns the correct role.
        self.assertEqual(role_id, self.controller_interface.get_vertex_preferred_role(vertex_id))

    @check_ref_lock
    @abstractmethod
    def test_get_locked_vertex_preferred_role(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if the vertex's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(vertex_id)):
                self.controller_interface.get_vertex_preferred_role(vertex_id)

    @check_ref_lock
    @abstractmethod
    def test_find_in_catalog(self):
        """
        Verify:
            * Succeeds if:
                * Another element of a different type with the same name exists.
                * No vertex with the given name exists.
            * On success:
                * If vertex with the given name exists, returns it.
                * If no vertex with the given name exists, returns None.
        """
        self.controller_interface.add_label('test_vertex')
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        catalog_id = self.controller_interface.add_catalog('test_catalog', str)
        self.controller_interface.add_catalog_entry(catalog_id, 'test_vertex', vertex_id)
        # Succeed if an element of a different type with the same name exists.
        result = self.controller_interface.find_in_catalog(catalog_id, 'test_vertex')
        # On success, if vertex with the given name exists, returns it.
        self.assertEqual(result, vertex_id)
        # Succeed if no vertex with the given name exists.
        result = self.controller_interface.find_in_catalog(catalog_id, 'nonexistent_vertex')
        # On success, if no vertex with the given name exists, return None.
        self.assertIsNone(result)

    @check_ref_lock
    @abstractmethod
    def test_count_vertex_outbound(self):
        """
        Verify:
            * Fails if:
                * The vertex does not exist.
                * The vertex's write lock is held elsewhere.
            * On success:
                * Returns the number of outbound edges from the vertex.
        """
        invalid_id = VertexID(-1)
        with self.assertRaises(KeyError):
            # Fails if the vertex does not exist.
            self.controller_interface.count_vertex_outbound(invalid_id)
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        adjacent_vertex1 = self.controller_interface.add_vertex(role_id)
        adjacent_vertex2 = self.controller_interface.add_vertex(role_id)
        label_id = self.controller_interface.add_label('test_label')
        self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex1)
        self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex2)
        self.controller_interface.add_edge(label_id, adjacent_vertex1, vertex_id)
        # On success, returns the number of outbound edges from the vertex.
        self.assertEqual(2, self.controller_interface.count_vertex_outbound(vertex_id))

    @check_ref_lock
    @abstractmethod
    def test_count_locked_vertex_outbound(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if the vertex's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(vertex_id)):
                self.controller_interface.count_vertex_outbound(vertex_id)

    @check_ref_lock
    @abstractmethod
    def test_iter_vertex_outbound(self):
        """
        Verify:
            * Fails if:
                * The vertex does not exist.
                * The vertex's write lock is held elsewhere.
            * On success:
                * Returns an iterator over the outbound edges from the vertex.
            * The registry lock is not held:
                * During iteration.
                * After iteration or unhandled exception.
            * The vertex's read lock:
                * Is not held after iteration or unhandled exception.
                * Is held during iteration.
        """
        invalid_id = VertexID(-1)
        with self.assertRaises(KeyError):
            # Fails if the vertex does not exist.
            next(self.controller_interface.iter_vertex_outbound(invalid_id))
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        adjacent_vertex1 = self.controller_interface.add_vertex(role_id)
        adjacent_vertex2 = self.controller_interface.add_vertex(role_id)
        label_id = self.controller_interface.add_label('test_label')
        edge1 = self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex1)
        edge2 = self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex2)
        self.controller_interface.add_edge(label_id, adjacent_vertex1, vertex_id)
        yielded = []
        for edge_id in self.controller_interface.iter_vertex_outbound(vertex_id):
            self.assertIn(edge_id, (edge1, edge2))
            yielded.append(edge_id)
            # The registry lock is not held during iteration.
            self.assertFalse(self.data_interface.registry_lock.locked())
            # The vertex's read lock is held during iteration.
            with self.data_interface.registry_lock:
                self.assertTrue(self.data_interface.access(vertex_id).is_read_locked)
        # The registry lock is not held after iteration.
        self.assertFalse(self.data_interface.registry_lock.locked())
        # The vertex's read lock is not held after iteration.
        with self.data_interface.registry_lock:
            self.assertFalse(self.data_interface.access(vertex_id).is_read_locked)
        # On success, returns an iterator over the outbound edges from the vertex.
        self.assertEqual(len(yielded), 2)
        self.assertEqual(set(yielded), {edge1, edge2})
        with self.assertRaises(Exception):
            for _edge_id in self.controller_interface.iter_vertex_outbound(vertex_id):
                raise Exception()  # Force an unhandled exception that terminates iteration early.
        # The registry lock is not held after unhandled exception.
        self.assertFalse(self.data_interface.registry_lock.locked())
        # The vertex's read lock is not held after unhandled exception.
        with self.data_interface.registry_lock:
            self.assertFalse(self.data_interface.access(vertex_id).is_read_locked)

    @check_ref_lock
    @abstractmethod
    def test_iter_locked_vertex_outbound(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if the vertex's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(vertex_id)):
                next(self.controller_interface.iter_vertex_outbound(vertex_id))

    @check_ref_lock
    @abstractmethod
    def test_count_vertex_inbound(self):
        """
        Verify:
            * Fails if:
                * The vertex does not exist.
                * The vertex's write lock is held elsewhere.
            * On success:
                * Returns the number of inbound edges to the vertex.
        """
        invalid_id = VertexID(-1)
        with self.assertRaises(KeyError):
            # Fails if the vertex does not exist.
            self.controller_interface.count_vertex_inbound(invalid_id)
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        adjacent_vertex1 = self.controller_interface.add_vertex(role_id)
        adjacent_vertex2 = self.controller_interface.add_vertex(role_id)
        label_id = self.controller_interface.add_label('test_label')
        self.controller_interface.add_edge(label_id, adjacent_vertex1, vertex_id)
        self.controller_interface.add_edge(label_id, adjacent_vertex2, vertex_id)
        self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex1)
        # On success, returns the number of inbound edges from the vertex.
        self.assertEqual(2, self.controller_interface.count_vertex_inbound(vertex_id))

    @check_ref_lock
    @abstractmethod
    def test_count_locked_vertex_inbound(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if the vertex's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(vertex_id)):
                self.controller_interface.count_vertex_inbound(vertex_id)

    @check_ref_lock
    @abstractmethod
    def test_iter_vertex_inbound(self):
        """
        Verify:
            * Fails if:
                * The vertex does not exist.
                * The vertex's write lock is held elsewhere.
            * On success:
                * Returns an iterator over the inbound edges from the vertex.
            * The registry lock is not held:
                * Before the method call.
                * During iteration.
                * After iteration or failure.
            * The vertex's read lock:
                * Is not held:
                    * Before the method call.
                    * After iteration or failure.
                * Is held during iteration.
        """
        invalid_id = VertexID(-1)
        with self.assertRaises(KeyError):
            # Fails if the vertex does not exist.
            next(self.controller_interface.iter_vertex_inbound(invalid_id))
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        adjacent_vertex1 = self.controller_interface.add_vertex(role_id)
        adjacent_vertex2 = self.controller_interface.add_vertex(role_id)
        label_id = self.controller_interface.add_label('test_label')
        edge1 = self.controller_interface.add_edge(label_id, adjacent_vertex1, vertex_id)
        edge2 = self.controller_interface.add_edge(label_id, adjacent_vertex2, vertex_id)
        self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex1)
        yielded = []
        for edge_id in self.controller_interface.iter_vertex_inbound(vertex_id):
            self.assertIn(edge_id, (edge1, edge2))
            yielded.append(edge_id)
            # The registry lock is not held during iteration.
            self.assertFalse(self.data_interface.registry_lock.locked())
            # The vertex's read lock is held during iteration.
            with self.data_interface.registry_lock:
                self.assertTrue(self.data_interface.access(vertex_id).is_read_locked)
        # The registry lock is not held after iteration.
        self.assertFalse(self.data_interface.registry_lock.locked())
        # The vertex's read lock is not held after iteration.
        with self.data_interface.registry_lock:
            self.assertFalse(self.data_interface.access(vertex_id).is_read_locked)
        # On success, returns an iterator over the inbound edges to the vertex.
        self.assertEqual(len(yielded), 2)
        self.assertEqual(set(yielded), {edge1, edge2})
        with self.assertRaises(Exception):
            for _edge_id in self.controller_interface.iter_vertex_inbound(vertex_id):
                raise Exception()  # Force an unhandled exception that terminates iteration early.
        # The registry lock is not held after unhandled exception.
        self.assertFalse(self.data_interface.registry_lock.locked())
        # The vertex's read lock is not held after unhandled exception.
        with self.data_interface.registry_lock:
            self.assertFalse(self.data_interface.access(vertex_id).is_read_locked)

    @check_ref_lock
    @abstractmethod
    def test_iter_locked_vertex_inbound(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if the vertex's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(vertex_id)):
                next(self.controller_interface.iter_vertex_inbound(vertex_id))


class BaseControllerRemoveVertexMethodTestCase(BaseControllerTestCase):
    """
    Verify:
        * Fails if:
            * Vertex does not exist.
            * The vertex has a name or time stamp.
            * Any of the vertex's locks are held elsewhere.
            * There are adjacent edges and adjacent_edges is False.
            * Any of the adjacent edges' locks are held elsewhere.
            * Any of the adjacent vertices' locks are held elsewhere.
        * On failure:
            * No adjacent edges are removed.
        * On success:
            * Adjacent edges no longer exist.
            * Formerly adjacent vertices continue to exist.
            * Formerly adjacent vertices no longer hold references to the removed edges.
            * Vertex no longer exists.
    """

    @contextlib.contextmanager
    def edges_remain(self, *edge_ids: EdgeID):
        try:
            yield
        finally:
            for edge_id in edge_ids:
                # Check that edge still exists.
                self.controller_interface.get_edge_label(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_vertex_does_not_exist(self):
        invalid_vertex_id = VertexID(-1)
        # Fails if vertex does not exist.
        with self.assertRaises(KeyError):
            self.controller_interface.remove_vertex(invalid_vertex_id)

    @check_ref_lock
    @abstractmethod
    def test_vertex_is_read_locked(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if another thread holds the vertex's read lock.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(vertex_id)):
                self.controller_interface.remove_vertex(vertex_id)

    @check_ref_lock
    @abstractmethod
    def test_vertex_is_write_locked(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)

        # Fails if another thread holds the vertex's write lock.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(vertex_id)):
                self.controller_interface.remove_vertex(vertex_id)

    @check_ref_lock
    @abstractmethod
    def test_adjacent_edges_is_false(self):
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        adjacent_vertex = self.controller_interface.add_vertex(role_id)
        label_id = self.controller_interface.add_label('test_label')
        edge_id = self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex)
        with self.edges_remain(edge_id):
            with self.assertRaises(ResourceUnavailableError):
                # Fails if there are adjacent edges and adjacent_edges is False.
                self.controller_interface.remove_vertex(vertex_id, adjacent_edges=False)

    @check_ref_lock
    @abstractmethod
    def test_edge_is_read_locked(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)
        adjacent_vertex = self.controller.add_vertex(role_id)
        label_id = self.controller.add_label('test_label')
        edge_id = self.controller.add_edge(label_id, vertex_id, adjacent_vertex)

        # Fails if adjacent_edges is True and any edge's read lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with self.edges_remain(edge_id):
                with threaded_context(self.read_locked(edge_id)):
                    self.controller_interface.remove_vertex(vertex_id, adjacent_edges=True)

    @check_ref_lock
    @abstractmethod
    def test_edge_is_write_locked(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)
        adjacent_vertex = self.controller.add_vertex(role_id)
        label_id = self.controller.add_label('test_label')
        edge_id = self.controller.add_edge(label_id, vertex_id, adjacent_vertex)

        # Fails if adjacent_edges is True and any edge's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with self.edges_remain(edge_id):
                with threaded_context(self.write_locked(edge_id)):
                    self.controller_interface.remove_vertex(vertex_id, adjacent_edges=True)

    @check_ref_lock
    @abstractmethod
    def test_adjacent_vertex_is_read_locked(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)
        adjacent_vertex = self.controller.add_vertex(role_id)
        label_id = self.controller.add_label('test_label')
        edge_id = self.controller.add_edge(label_id, vertex_id, adjacent_vertex)

        # Fails if adjacent_edges is True and any adjacent vertex's read lock is held by another
        # thread.
        with self.assertRaises(ResourceUnavailableError):
            with self.edges_remain(edge_id):
                with threaded_context(self.read_locked(adjacent_vertex)):
                    self.controller_interface.remove_vertex(vertex_id, adjacent_edges=True)

    @check_ref_lock
    @abstractmethod
    def test_adjacent_vertex_is_write_locked(self):
        role_id = self.controller.add_role('test_role')
        vertex_id = self.controller.add_vertex(role_id)
        adjacent_vertex = self.controller.add_vertex(role_id)
        label_id = self.controller.add_label('test_label')
        edge_id = self.controller.add_edge(label_id, vertex_id, adjacent_vertex)
        # Fails if adjacent_edges is True and any adjacent vertex's write lock is held
        # by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with self.edges_remain(edge_id):
                with threaded_context(self.write_locked(adjacent_vertex)):
                    self.controller_interface.remove_vertex(vertex_id, adjacent_edges=True)

    @check_ref_lock
    @abstractmethod
    def test_happy_path(self):
        role_id = self.controller_interface.add_role('test_role')
        vertex_id = self.controller_interface.add_vertex(role_id)
        adjacent_vertex1 = self.controller_interface.add_vertex(role_id)
        adjacent_vertex2 = self.controller_interface.add_vertex(role_id)
        label_id = self.controller_interface.add_label('test_label')
        outbound_edge_id = self.controller_interface.add_edge(label_id, vertex_id, adjacent_vertex1)
        inbound_edge_id = self.controller_interface.add_edge(label_id, adjacent_vertex2, vertex_id)
        looped_edge_id = self.controller_interface.add_edge(label_id, vertex_id, vertex_id)

        # The moment of truth.
        self.controller_interface.remove_vertex(vertex_id, adjacent_edges=True)

        # Adjacent edges no longer exist.
        with self.assertRaises(KeyError):
            self.controller_interface.get_edge_label(outbound_edge_id)
        with self.assertRaises(KeyError):
            self.controller_interface.get_edge_label(inbound_edge_id)
        with self.assertRaises(KeyError):
            self.controller_interface.get_edge_label(looped_edge_id)
        # Formerly adjacent vertices continue to exist.
        self.controller_interface.get_vertex_preferred_role(adjacent_vertex1)
        self.controller_interface.get_vertex_preferred_role(adjacent_vertex2)
        # Formerly adjacent vertices no longer hold references to the removed edges.
        self.assertNotIn(outbound_edge_id,
                         self.controller_interface.iter_vertex_inbound(adjacent_vertex1))
        self.assertNotIn(inbound_edge_id,
                         self.controller_interface.iter_vertex_outbound(adjacent_vertex2))
        # Vertex no longer exists.
        with self.assertRaises(KeyError):
            self.controller_interface.get_vertex_preferred_role(vertex_id)


class BaseControllerEdgesTestCase(BaseControllerTestCase):

    @check_ref_lock
    @abstractmethod
    def test_add_edge(self):
        """
        Verify:
            * Fails if:
                * Label does not exist.
                * Label is locked for write.
                * Source does not exist.
                * Source is locked for read or write.
                * Sink does not exist.
                * Sink is locked for read or write.
                * Edge with the same label, source, and sink already exists.
            * On success:
                * New edge has:
                    * Correct label.
                    * Correct source and sink.
                * New edge appears in source's outbound edges.
                * New edge appears in sink's inbound edges.
        """
        invalid_label_id = LabelID(-1)
        label_id = self.controller_interface.add_label('test')
        invalid_vertex_id = VertexID(-1)
        role_id = self.controller_interface.add_role('test')
        source_id = self.controller_interface.add_vertex(role_id)
        sink_id = self.controller_interface.add_vertex(role_id)
        with self.assertRaises(KeyError):
            # Fails if label does not exist.
            self.controller_interface.add_edge(invalid_label_id, source_id, sink_id)
        with self.assertRaises(KeyError):
            # Fails if source does not exist.
            self.controller_interface.add_edge(label_id, invalid_vertex_id, sink_id)
        with self.assertRaises(KeyError):
            # Fails if sink does not exist.
            self.controller_interface.add_edge(label_id, source_id, invalid_vertex_id)
        edge_id = self.controller_interface.add_edge(label_id, source_id, sink_id)
        # On success, edge has correct label, source, and sink.
        self.assertEqual(label_id, self.controller_interface.get_edge_label(edge_id))
        self.assertEqual(source_id, self.controller_interface.get_edge_source(edge_id))
        self.assertEqual(sink_id, self.controller_interface.get_edge_sink(edge_id))
        # On success, new edge appears in source's outbound edges and sink's inbound edges
        self.assertIn(edge_id, self.controller_interface.iter_vertex_outbound(source_id))
        self.assertIn(edge_id, self.controller_interface.iter_vertex_inbound(sink_id))
        with self.assertRaises(KeyError):
            # Fails if edge with the same label, source, and sink already exists.
            self.controller_interface.add_edge(label_id, source_id, sink_id)

    @check_ref_lock
    @abstractmethod
    def test_add_edge_label_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        with self.write_locked(label_id):
            with self.assertRaises(ResourceUnavailableError):
                # Fails if label is write-locked.
                threaded_call(self.controller_interface.add_edge, label_id, source_id, sink_id)

    @check_ref_lock
    @abstractmethod
    def test_add_edge_source_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)

        # Fails if source is read-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(source_id)):
                self.controller_interface.add_edge(label_id, source_id, sink_id)

        # Fails if source is write-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(source_id)):
                self.controller_interface.add_edge(label_id, source_id, sink_id)

    @check_ref_lock
    @abstractmethod
    def test_add_edge_sink_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)

        # Fails if sink is read-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(sink_id)):
                self.controller_interface.add_edge(label_id, source_id, sink_id)

        # Fails if sink is write-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(sink_id)):
                self.controller_interface.add_edge(label_id, source_id, sink_id)

    @check_ref_lock
    @abstractmethod
    def test_remove_edge(self):
        """
        Verify:
            * Fails if:
                * Edge does not exist.
                * Edge is locked for read or write by another thread.
                * Source is locked for read or write by another thread.
                * Sink is locked for read or write by another thread.
            * On success:
                * Edge no longer exists.
                * Edge no longer appears in source's outbound edges.
                * Edge no longer appears in sink's inbound edges.
        """
        invalid_id = EdgeID(-1)
        with self.assertRaises(KeyError):
            # Fails if the edge does not exist.
            self.controller_interface.remove_edge(invalid_id)
        label_id = self.controller_interface.add_label('test')
        role_id = self.controller_interface.add_role('test')
        source_id = self.controller_interface.add_vertex(role_id)
        sink_id = self.controller_interface.add_vertex(role_id)
        edge_id = self.controller_interface.add_edge(label_id, source_id, sink_id)
        self.controller_interface.remove_edge(edge_id)
        # On success, edge no longer exists.
        with self.assertRaises(KeyError):
            self.controller_interface.get_edge_label(edge_id)
        # On success, edge no longer appears in source's outbound edges or sink's inbound edges.
        self.assertNotIn(edge_id, self.controller_interface.iter_vertex_outbound(source_id))
        self.assertNotIn(edge_id, self.controller_interface.iter_vertex_inbound(sink_id))

    @check_ref_lock
    @abstractmethod
    def test_remove_locked_edge(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Fails if edge is read-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(edge_id)):
                self.controller_interface.remove_edge(edge_id)

        # Fails if edge is write-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(edge_id)):
                self.controller_interface.remove_edge(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_remove_edge_label_read_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Doesn't fail if label is read-locked.
        with threaded_context(self.read_locked(label_id)):
            self.controller_interface.remove_edge(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_remove_edge_label_write_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Doesn't fail if label is write-locked.
        with threaded_context(self.write_locked(label_id)):
            self.controller_interface.remove_edge(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_remove_edge_source_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Fails if source is read-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(source_id)):
                self.controller_interface.remove_edge(edge_id)

        # Fails if source is write-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(source_id)):
                self.controller_interface.remove_edge(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_remove_edge_sink_locked(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Fails if sink is read-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.read_locked(sink_id)):
                self.controller_interface.remove_edge(edge_id)

        # Fails if sink is write-locked.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(sink_id)):
                self.controller_interface.remove_edge(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_get_edge_label(self):
        """
        Verify:
            * Fails if:
                * The edge does not exist.
                * The edge's write lock is held elsewhere.
            * On success:
                * Returns the correct label.
        """
        invalid_id = EdgeID(-1)
        with self.assertRaises(KeyError):
            # Fails if the edge does not exist.
            self.controller_interface.get_edge_label(invalid_id)
        label_id = self.controller_interface.add_label('test')
        role_id = self.controller_interface.add_role('test')
        source_id = self.controller_interface.add_vertex(role_id)
        sink_id = self.controller_interface.add_vertex(role_id)
        edge_id = self.controller_interface.add_edge(label_id, source_id, sink_id)
        # On success, returns the correct label.
        self.assertEqual(label_id, self.controller_interface.get_edge_label(edge_id))

    @check_ref_lock
    @abstractmethod
    def test_get_locked_edge_label(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Fails if the edge's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(edge_id)):
                self.controller_interface.get_edge_label(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_get_edge_source(self):
        """
        Verify:
            * Fails if:
                * The edge does not exist.
                * The edge's write lock is held elsewhere.
            * On success:
                * Returns the correct vertex.
        """
        invalid_id = EdgeID(-1)
        with self.assertRaises(KeyError):
            # Fails if the edge does not exist.
            self.controller_interface.get_edge_source(invalid_id)
        label_id = self.controller_interface.add_label('test')
        role_id = self.controller_interface.add_role('test')
        source_id = self.controller_interface.add_vertex(role_id)
        sink_id = self.controller_interface.add_vertex(role_id)
        edge_id = self.controller_interface.add_edge(label_id, source_id, sink_id)
        # On success, returns the correct vertex.
        self.assertEqual(source_id, self.controller_interface.get_edge_source(edge_id))

    @check_ref_lock
    @abstractmethod
    def test_get_locked_edge_source(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Fails if the edge's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(edge_id)):
                self.controller_interface.get_edge_source(edge_id)

    @check_ref_lock
    @abstractmethod
    def test_get_edge_sink(self):
        """
        Verify:
            * Fails if:
                * The edge does not exist.
                * The edge's write lock is held elsewhere.
            * On success:
                * Returns the correct vertex.
        """
        invalid_id = EdgeID(-1)
        with self.assertRaises(KeyError):
            # Fails if the edge does not exist.
            self.controller_interface.get_edge_sink(invalid_id)
        label_id = self.controller_interface.add_label('test')
        role_id = self.controller_interface.add_role('test')
        source_id = self.controller_interface.add_vertex(role_id)
        sink_id = self.controller_interface.add_vertex(role_id)
        edge_id = self.controller_interface.add_edge(label_id, source_id, sink_id)
        # On success, returns the correct vertex.
        self.assertEqual(sink_id, self.controller_interface.get_edge_sink(edge_id))

    @check_ref_lock
    @abstractmethod
    def test_get_locked_edge_sink(self):
        label_id = self.controller.add_label('test')
        role_id = self.controller.add_role('test')
        source_id = self.controller.add_vertex(role_id)
        sink_id = self.controller.add_vertex(role_id)
        edge_id = self.controller.add_edge(label_id, source_id, sink_id)

        # Fails if the edge's write lock is held by another thread.
        with self.assertRaises(ResourceUnavailableError):
            with threaded_context(self.write_locked(edge_id)):
                self.controller_interface.get_edge_sink(edge_id)


class BaseControllerDataKeysTestCase(BaseControllerTestCase):

    def call_with_write_locked_index(self, function, initial_keys=None, final_keys=None):
        """Call the function on an element index that is write-locked by another thread. If
        initial_keys is supplied, use it to populate the index's data keys before acquiring the
        lock. If final_keys is supplied, use it to verify the index's data keys are correct after
        the lock is released."""
        index = self.controller.add_role('do_write_lock_held_test.test_role')
        if initial_keys is not None:
            for key, value in initial_keys.items():
                self.controller.set_data_key(index, key, value)
        try:
            with threaded_context(self.write_locked(index, level='controller')):
                result = function(index)
        finally:
            try:
                self.controller.remove_role(index)
            except KeyError:
                pass
        if final_keys is not None:
            for controller_interface in self.controller, self.transaction:
                for key, value in final_keys.items():
                    self.assertTrue(controller_interface.has_data_key(index, key))
                    self.assertEqual(value, controller_interface.get_data_key(index, key))
                for key in controller_interface.iter_data_keys(index):
                    self.assertIn(key, final_keys)
                    self.assertEqual(final_keys[key], controller_interface.get_data_key(index, key))
                self.assertEqual(len(final_keys), controller_interface.count_data_keys(index))
        return result

    @check_ref_lock
    @abstractmethod
    def test_get_data_key(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * The element's write lock is held elsewhere.
            * Succeeds if:
                * The element does not have data assigned to the key.
            * On success:
                * If the element has a value assigned to the key, returns the value assigned to the
                  key.
                * If the element has no value assigned to the key, returns the default value, or
                  None if no default.
                * Providing a default does not affect the key's assigned value.
            * Unaffected by presence or absence of the same key or value in another element.
        """
        invalid_index = RoleID(-1)
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            self.controller_interface.get_data_key(invalid_index, 'key')
        index = self.controller_interface.add_role('test')
        # Succeeds if the element does not have data assigned to the key.
        # On success, returns the default value if there is no value assigned to the key and a
        # default is provided.
        self.assertEqual('default', self.controller_interface.get_data_key(index, 'key', 'default'))
        # On success, returns None if there is no value assigned to the key and no default is
        # provided. Providing a default does not affect the key's assigned value.
        self.assertIsNone(self.controller_interface.get_data_key(index, 'key'))
        self.controller_interface.set_data_key(index, 'key', 'value')
        # On success, returns the value assigned to the key if one has been assigned.
        self.assertEqual('value', self.controller_interface.get_data_key(index, 'key'))
        another_index = self.controller_interface.add_role('test2')
        self.controller_interface.set_data_key(another_index, 'key', 'a different value')
        # Unaffected by presence or absence of the same key or value in another element.
        self.assertEqual('value', self.controller_interface.get_data_key(index, 'key'))
        # Fail if the element's write lock is held elsewhere.
        with self.assertRaises(ResourceUnavailableError):
            self.call_with_write_locked_index(
                function=lambda i: self.controller_interface.get_data_key(i, 'key')
            )

    @check_ref_lock
    @abstractmethod
    def test_set_data_key(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * The element's read or write lock is held elsewhere.
            * On success:
                * The element has the given value assigned to the key.
                * Any previous value assigned to the key for that element is overwritten.
                * If the value was set to None, the key is cleared.
            * Unaffected by presence or absence of the same key or value in another element.
        """
        invalid_index = RoleID(-1)
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            self.controller_interface.set_data_key(invalid_index, 'key', 'value')
        index = self.controller_interface.add_role('test')
        self.controller_interface.set_data_key(index, 'key', 'value')
        # On success, the element has the given value assigned to the key.
        self.assertEqual('value', self.controller_interface.get_data_key(index, 'key'))
        another_index = self.controller_interface.add_role('test2')
        self.controller_interface.set_data_key(another_index, 'key', 'a different value')
        # Unaffected by presence or absence of the same key or value in another element.
        self.assertEqual('value', self.controller_interface.get_data_key(index, 'key'))
        self.controller_interface.set_data_key(index, 'key', 'another value')
        # On success, any previous value assigned to the key for that element is overwritten.
        self.assertEqual('another value', self.controller_interface.get_data_key(index, 'key'))
        self.controller_interface.set_data_key(index, 'key', None)
        # If the value was set to None, the key is cleared.
        self.assertEqual('default', self.controller_interface.get_data_key(index, 'key', 'default'))
        # Fail if the element's write lock is held elsewhere.
        # On failure, any previous value assigned to the key for that element is not overwritten.
        with self.assertRaises(ResourceUnavailableError):
            self.call_with_write_locked_index(
                function=lambda i: self.controller_interface.set_data_key(i, 'key', 'new value'),
                initial_keys={'key': 'value'},
                final_keys={'key': 'value'}
            )

    @check_ref_lock
    @abstractmethod
    def test_clear_data_key(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * The element's read or write lock is held elsewhere.
            * On failure:
                * Any previous value assigned to the key for that element is not cleared.
            * Succeeds if:
                * The element does not have a value assigned to it.
            * On success:
                * Any previous value assigned to the key for that element is cleared.
            * Does not affect presence or absence of the same key or value in another element.
        """
        invalid_index = RoleID(-1)
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            self.controller_interface.set_data_key(invalid_index, 'key', 'value')
        index = self.controller_interface.add_role('test')
        self.controller_interface.set_data_key(index, 'key', 'value')
        another_index = self.controller_interface.add_role('test2')
        self.controller_interface.set_data_key(another_index, 'key', 'a different value')
        self.controller_interface.clear_data_key(index, 'key')
        # On success, any previous value assigned to the key for that element is cleared.
        self.assertFalse(self.controller_interface.has_data_key(index, 'key'))
        # Succeeds if the element does not have a value assigned to it.
        self.controller_interface.clear_data_key(index, 'key')
        # Does not affect presence or absence of the same key or value in another element.
        self.assertEqual('a different value',
                         self.controller_interface.get_data_key(another_index, 'key'))
        # Fail if the element's write lock is held elsewhere.
        # On failure, any previous value assigned to the key for that element is not cleared.
        with self.assertRaises(ResourceUnavailableError):
            self.call_with_write_locked_index(
                function=lambda i: self.controller_interface.clear_data_key(i, 'key'),
                initial_keys={'key': 'value'},
                final_keys={'key': 'value'}
            )

    @check_ref_lock
    @abstractmethod
    def test_has_data_key(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * The element's write lock is held elsewhere.
            * On success:
                * Returns True if a value is assigned to the key for the element, or False if no
                  value is assigned.
            * Unaffected by presence or absence of the same key or value in another element.
        """
        invalid_index = RoleID(-1)
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            self.controller_interface.has_data_key(invalid_index, 'key')
        index = self.controller_interface.add_role('test')
        # On success, returns False if no value is assigned.
        self.assertFalse(self.controller_interface.has_data_key(index, 'key'))
        another_index = self.controller_interface.add_role('test2')
        self.controller_interface.set_data_key(another_index, 'key', 'a different value')
        # Unaffected by presence or absence of the same key or value in another element.
        self.assertFalse(self.controller_interface.has_data_key(index, 'key'))
        self.controller_interface.set_data_key(index, 'key', 'value')
        # On success, returns True if a value is assigned to the key for the element.
        self.assertTrue(self.controller_interface.has_data_key(index, 'key'))
        # Fail if the element's write lock is held elsewhere.
        with self.assertRaises(ResourceUnavailableError):
            self.call_with_write_locked_index(
                function=lambda i: self.controller_interface.has_data_key(i, 'key')
            )

    @check_ref_lock
    @abstractmethod
    def test_iter_data_keys(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * The element's write lock is held elsewhere.
            * On success:
                * Returns an iterator over the data keys of the element with non-None values
                  assigned to them.
            * The registry lock is not held:
                * Before the method call.
                * During iteration.
                * After iteration or failure.
            * The element's read lock:
                * Is not held:
                    * Before the method call.
                    * After iteration or failure.
                * Is held during iteration.
        """
        invalid_index = RoleID(-1)
        with self.assertRaises(KeyError):
            # Fail if the element does not exist.
            next(self.controller_interface.iter_data_keys(invalid_index))
        index = self.controller_interface.add_role('test')
        expected = {'key1': 'value1', 'key2': 'value2'}
        for key, value in expected.items():
            self.controller_interface.set_data_key(index, key, value)
        yielded = []
        for key in self.controller_interface.iter_data_keys(index):
            self.assertIn(key, expected)
            yielded.append(key)
            # The registry lock is not held during iteration.
            self.assertFalse(self.data_interface.registry_lock.locked())
            # The element's read lock is held during iteration.
            with self.data_interface.registry_lock:
                self.assertTrue(self.data_interface.access(index).is_read_locked)
        # The registry lock is not held after iteration.
        self.assertFalse(self.data_interface.registry_lock.locked())
        # The element's read lock is not held after iteration.
        with self.data_interface.registry_lock:
            self.assertFalse(self.data_interface.access(index).is_read_locked)
        # On success, returns an iterator over the data keys of the element.
        self.assertEqual(len(yielded), len(expected))
        self.assertEqual(set(yielded), expected.keys())
        with self.assertRaises(Exception):
            for _key in self.controller_interface.iter_data_keys(index):
                raise Exception()  # Force an unhandled exception that terminates iteration early.
        # The registry lock is not held after unhandled exception.
        self.assertFalse(self.data_interface.registry_lock.locked())
        # The element's read lock is not held after unhandled exception.
        with self.data_interface.registry_lock:
            self.assertFalse(self.data_interface.access(index).is_read_locked)
        # Fail if the element's write lock is held elsewhere.
        with self.assertRaises(ResourceUnavailableError):
            self.call_with_write_locked_index(
                function=lambda i: next(self.controller_interface.iter_data_keys(i))
            )

    @check_ref_lock
    @abstractmethod
    def test_count_data_keys(self):
        """
        Verify:
            * Fails if:
                * The element does not exist.
                * The element's write lock is held elsewhere.
            * On success:
                * Returns the number of data keys stored in the element with non-None values.
        """
        invalid_index = RoleID(-1)
        with self.assertRaises(KeyError):
            # Fails if the element does not exist.
            self.controller_interface.count_data_keys(invalid_index)
        index = self.controller_interface.add_role('test')
        expected = {'key1': 'value1', 'key2': 'value2'}
        for key, value in expected.items():
            self.controller_interface.set_data_key(index, key, value)
        # On success, returns the number of data keys of the element.
        self.assertEqual(len(expected), self.controller_interface.count_data_keys(index))
        # Fail if the element's write lock is held elsewhere.
        with self.assertRaises(ResourceUnavailableError):
            self.call_with_write_locked_index(
                function=lambda i: self.controller_interface.count_data_keys(i)
            )
