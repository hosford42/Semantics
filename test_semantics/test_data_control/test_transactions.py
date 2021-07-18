from typing import Callable

from semantics.data_control.transactions import Transaction
from semantics.data_types.exceptions import ResourceUnavailableError
from semantics.data_types.indices import PersistentDataID
from test_semantics.test_data_control import base


class TestTransactionCommit(base.BaseControllerTestCase):
    """
    Verify:
        * On success, but not before then:
            * New roles, vertices, labels, and edges are added to the controller data.
            * Changes to existing roles, vertices, labels, and edges, are applied to the
              controller data.
            * Roles, vertices, labels, and edges that are waiting to be deleted are removed from
              the controller data.
            * Newly allocated names of roles, vertices, and labels are allocated in the controller
              data.
            * Newly deallocated names of roles, vertices, and labels are deallocated in the
              controller data.
        * On success:
            * Any controller data locks acquired by the transaction are released.
            * The transaction is reset to its initial state.
    """

    base_controller_subclass = Transaction

    def do_add_test(self, new_index: PersistentDataID):
        self.transaction.set_data_key(new_index, 'key', 'value')
        with self.assertRaises(KeyError):
            # Changes in transaction don't affect controller until commit.
            self.controller.get_data_key(new_index, 'key')
        # Changes are visible in the transaction.
        self.assertEqual(self.transaction.get_data_key(new_index, 'key'), 'value')
        self.transaction.commit()
        # After the commit, they are visible in both.
        self.assertEqual(self.controller.get_data_key(new_index, 'key'), 'value')
        self.assertEqual(self.transaction.get_data_key(new_index, 'key'), 'value')
        # And the element is not locked.
        self.controller.set_data_key(new_index, 'key', 'a different value')

    def test_add_role(self):
        self.do_add_test(self.transaction.add_role('test'))

    def test_add_vertex(self):
        self.do_add_test(self.transaction.add_vertex(self.preexisting_role_id))

    def test_add_label(self):
        self.do_add_test(self.transaction.add_label('test'))

    def test_add_edge(self):
        # We have to use the source as the sink and vice versa so we don't clash with the
        # pre-existing edge created in setUp().
        self.do_add_test(
            self.transaction.add_edge(
                self.preexisting_label_id,
                self.preexisting_sink_id,
                self.preexisting_source_id
            )
        )

    def do_update_test(self, index: PersistentDataID):
        self.transaction.set_data_key(index, 'key', 'value')
        # The write lock in the controller is held once we access the element with write access
        # in the transaction.
        with self.assertRaises(ResourceUnavailableError):
            self.controller.get_data_key(index, 'key')
        # Changes are visible in the transaction.
        self.assertEqual(self.transaction.get_data_key(index, 'key'), 'value')
        self.transaction.commit()
        # After the commit, they are visible in both.
        self.assertEqual(self.controller.get_data_key(index, 'key'), 'value')
        self.assertEqual(self.transaction.get_data_key(index, 'key'), 'value')
        # And the element is not locked.
        self.controller.set_data_key(index, 'key', 'a different value')

    def test_update_role(self):
        self.do_update_test(self.preexisting_role_id)

    def test_update_vertex(self):
        self.do_update_test(self.preexisting_source_id)

    def test_update_label(self):
        self.do_update_test(self.preexisting_label_id)

    def test_update_edge(self):
        self.do_update_test(self.preexisting_edge_id)

    def do_remove_test(self, index: PersistentDataID, remove: Callable[[PersistentDataID], None]):
        self.controller.set_data_key(index, 'key', 'value')
        remove(index)
        # The write lock in the controller is held once we access the element with write access
        # in the transaction.
        with self.assertRaises(ResourceUnavailableError):
            self.controller.get_data_key(index, 'key')
        # Changes are visible in the transaction.
        with self.assertRaises(KeyError):
            self.transaction.get_data_key(index, 'key')
        self.transaction.commit()
        # After the commit the element is removed in both.
        with self.assertRaises(KeyError):
            self.controller.get_data_key(index, 'key')
        with self.assertRaises(KeyError):
            self.transaction.get_data_key(index, 'key')

    def test_remove_role(self):
        index = self.controller.add_role('test')
        self.do_remove_test(index, self.transaction.remove_role)

    def test_remove_vertex(self):
        index = self.controller.add_vertex(self.preexisting_role_id)
        self.do_remove_test(index, self.transaction.remove_vertex)

    def test_remove_label(self):
        index = self.controller.add_label('test')
        self.do_remove_test(index, self.transaction.remove_label)

    def test_remove_edge(self):
        # We have to use the source as the sink and vice versa so we don't clash with the
        # pre-existing edge created in setUp().
        index = self.controller.add_edge(
            self.preexisting_label_id,
            self.preexisting_sink_id,
            self.preexisting_source_id
        )
        self.do_remove_test(index, self.transaction.remove_edge)

    def test_reference_release_after_commit(self):
        """When a reference to an element is acquired before the commit, and released after the
        commit, this should not cause an issue."""
        vertex_id = self.transaction.add_vertex(self.preexisting_role_id)
        reference_id = self.transaction.new_reference_id()
        self.transaction.acquire_reference(reference_id, vertex_id)
        print(self.transaction._data.held_references)
        with self.transaction._data.registry_lock:
            print(self.transaction._data.access(vertex_id).is_read_locked)
        self.transaction.commit()
        with self.transaction._data.registry_lock:
            print(self.transaction._data.access(vertex_id).is_read_locked)
        print(self.transaction._data.held_references)
        for call in self.call_sequence:
            print("Call:", call)
        self.transaction.release_reference(reference_id, vertex_id)


class TestTransactionRollback(base.BaseControllerTestCase):
    """
    Verify:
        * Before and after success:
            * New roles, vertices, labels, and edges are not added to the controller data.
            * Changes to existing roles, vertices, labels, and edges, are not applied to the
              controller data.
            * Roles, vertices, labels, and edges that are waiting to be deleted are not removed
              from the controller data.
            * Newly allocated names of roles, vertices, and labels are not allocated in the
              controller data.
            * Newly deallocated names of roles, vertices, and labels are not deallocated in the
              controller data.
        * On success:
            * Any controller data locks acquired by the transaction are released.
            * The transaction is reset to its initial state.
    """

    base_controller_subclass = Transaction

    def do_add_test(self, new_index: PersistentDataID):
        self.transaction.set_data_key(new_index, 'key', 'value')
        with self.assertRaises(KeyError):
            # Changes in transaction don't affect controller until commit.
            self.controller.get_data_key(new_index, 'key')
        # Changes are visible in the transaction.
        self.assertEqual(self.transaction.get_data_key(new_index, 'key'), 'value')
        self.transaction.rollback()
        # After the rollback, they are visible in neither.
        with self.assertRaises(KeyError):
            self.controller.get_data_key(new_index, 'key')
        with self.assertRaises(KeyError):
            self.transaction.get_data_key(new_index, 'key')

    def test_add_role(self):
        self.do_add_test(self.transaction.add_role('test'))

    def test_add_vertex(self):
        self.do_add_test(self.transaction.add_vertex(self.preexisting_role_id))

    def test_add_label(self):
        self.do_add_test(self.transaction.add_label('test'))

    def test_add_edge(self):
        # We have to use the source as the sink and vice versa so we don't clash with the
        # pre-existing edge created in setUp().
        self.do_add_test(
            self.transaction.add_edge(
                self.preexisting_label_id,
                self.preexisting_sink_id,
                self.preexisting_source_id
            )
        )

    def do_update_test(self, index: PersistentDataID):
        self.transaction.set_data_key(index, 'key', 'value')
        # The write lock in the controller is held once we access the element with write access
        # in the transaction.
        with self.assertRaises(ResourceUnavailableError):
            self.controller.get_data_key(index, 'key')
        # Changes are visible in the transaction.
        self.assertEqual(self.transaction.get_data_key(index, 'key'), 'value')
        self.transaction.rollback()
        # After the rollback, they are visible in neither.
        self.assertIsNone(self.controller.get_data_key(index, 'key'))
        self.assertIsNone(self.transaction.get_data_key(index, 'key'))
        # And the element is not locked.
        self.controller.set_data_key(index, 'key', 'a different value')

    def test_update_role(self):
        self.do_update_test(self.preexisting_role_id)

    def test_update_vertex(self):
        self.do_update_test(self.preexisting_source_id)

    def test_update_label(self):
        self.do_update_test(self.preexisting_label_id)

    def test_update_edge(self):
        self.do_update_test(self.preexisting_edge_id)

    def do_remove_test(self, index: PersistentDataID, remove: Callable[[PersistentDataID], None]):
        self.controller.set_data_key(index, 'key', 'value')
        remove(index)
        # The write lock in the controller is held once we access the element with write access
        # in the transaction.
        with self.assertRaises(ResourceUnavailableError):
            self.controller.get_data_key(index, 'key')
        # Changes are visible in the transaction.
        with self.assertRaises(KeyError):
            self.transaction.get_data_key(index, 'key')
        self.transaction.rollback()
        # After the rollback the element is removed in neither.
        self.assertEqual(self.controller.get_data_key(index, 'key'), 'value')
        self.assertEqual(self.transaction.get_data_key(index, 'key'), 'value')

    def test_remove_role(self):
        index = self.controller.add_role('test')
        self.do_remove_test(index, self.transaction.remove_role)

    def test_remove_vertex(self):
        index = self.controller.add_vertex(self.preexisting_role_id)
        self.do_remove_test(index, self.transaction.remove_vertex)

    def test_remove_label(self):
        index = self.controller.add_label('test')
        self.do_remove_test(index, self.transaction.remove_label)

    def test_remove_edge(self):
        # We have to use the source as the sink and vice versa so we don't clash with the
        # pre-existing edge created in setUp().
        index = self.controller.add_edge(
            self.preexisting_label_id,
            self.preexisting_sink_id,
            self.preexisting_source_id
        )
        self.do_remove_test(index, self.transaction.remove_edge)


class TestTransactionReferences(base.BaseControllerReferencesTestCase):
    base_controller_subclass = Transaction

    def test_new_reference_id(self):
        super().test_new_reference_id()

    def test_acquire_reference(self):
        super().test_acquire_reference()

    def test_release_reference(self):
        super().test_release_reference()


class TestTransactionRoles(base.BaseControllerRolesTestCase):
    base_controller_subclass = Transaction

    def test_add(self):
        super().test_add()

    def test_remove(self):
        super().test_remove()

    def test_remove_locked(self):
        super().test_remove_locked()

    def test_get_name(self):
        super().test_get_name()

    def test_get_name_locked(self):
        super().test_get_name_locked()

    def test_find(self):
        super().test_find()


class TestTransactionLabels(base.BaseControllerLabelsTestCase):
    base_controller_subclass = Transaction

    def test_add(self):
        super().test_add()

    def test_remove(self):
        super().test_remove()

    def test_remove_locked(self):
        super().test_remove_locked()

    def test_get_name(self):
        super().test_get_name()

    def test_get_name_locked(self):
        super().test_get_name_locked()

    def test_find(self):
        super().test_find()


class TestTransactionVertices(base.BaseControllerVerticesTestCase):
    base_controller_subclass = Transaction

    def test_add_vertex(self):
        super().test_add_vertex()

    def test_add_vertex_locked_role(self):
        super().test_add_vertex_locked_role()

    def test_get_vertex_preferred_role(self):
        super().test_get_vertex_preferred_role()

    def test_get_locked_vertex_preferred_role(self):
        super().test_get_locked_vertex_preferred_role()

    def test_get_vertex_name(self):
        super().test_get_vertex_name()

    def test_get_locked_vertex_name(self):
        super().test_get_locked_vertex_name()

    def test_set_vertex_name(self):
        super().test_set_vertex_name()

    def test_set_locked_vertex_name(self):
        super().test_set_locked_vertex_name()

    def test_get_vertex_time_stamp(self):
        super().test_get_vertex_time_stamp()

    def test_get_locked_vertex_time_stamp(self):
        super().test_get_locked_vertex_time_stamp()

    def test_set_vertex_time_stamp(self):
        super().test_set_vertex_time_stamp()

    def test_set_locked_vertex_time_stamp(self):
        super().test_set_locked_vertex_time_stamp()

    def test_find_vertex(self):
        super().test_find_vertex()

    def test_count_vertex_outbound(self):
        super().test_count_vertex_outbound()

    def test_count_locked_vertex_outbound(self):
        super().test_count_locked_vertex_outbound()

    def test_iter_vertex_inbound(self):
        super().test_iter_vertex_outbound()

    def test_iter_locked_vertex_outbound(self):
        super().test_iter_locked_vertex_outbound()

    def test_count_vertex_inbound(self):
        super().test_count_vertex_inbound()

    def test_count_locked_vertex_inbound(self):
        super().test_count_locked_vertex_inbound()

    def test_iter_vertex_outbound(self):
        super().test_iter_vertex_inbound()

    def test_iter_locked_vertex_inbound(self):
        super().test_iter_locked_vertex_inbound()


class TestTransactionRemoveVertexMethod(base.BaseControllerRemoveVertexMethodTestCase):
    base_controller_subclass = Transaction

    def test_vertex_does_not_exist(self):
        super().test_vertex_does_not_exist()

    def test_vertex_is_named(self):
        super().test_vertex_is_named()

    def test_vertex_is_time_stamped(self):
        super().test_vertex_is_time_stamped()

    def test_vertex_is_read_locked(self):
        super().test_vertex_is_read_locked()

    def test_vertex_is_write_locked(self):
        super().test_vertex_is_write_locked()

    def test_adjacent_edges_is_false(self):
        super().test_adjacent_edges_is_false()

    def test_edge_is_read_locked(self):
        super().test_edge_is_read_locked()

    def test_edge_is_write_locked(self):
        super().test_edge_is_write_locked()

    def test_adjacent_vertex_is_read_locked(self):
        super().test_adjacent_vertex_is_read_locked()

    def test_adjacent_vertex_is_write_locked(self):
        super().test_adjacent_vertex_is_write_locked()

    def test_happy_path(self):
        super().test_happy_path()


class TestTransactionEdges(base.BaseControllerEdgesTestCase):
    base_controller_subclass = Transaction

    def test_add_edge(self):
        super().test_add_edge()

    def test_add_edge_label_locked(self):
        super().test_add_edge_label_locked()

    def test_add_edge_source_locked(self):
        super().test_add_edge_source_locked()

    def test_add_edge_sink_locked(self):
        super().test_add_edge_sink_locked()

    def test_remove_edge(self):
        super().test_remove_edge()

    def test_remove_locked_edge(self):
        super().test_remove_locked_edge()

    def test_remove_edge_label_read_locked(self):
        super().test_remove_edge_label_read_locked()

    def test_remove_edge_label_write_locked(self):
        super().test_remove_edge_label_write_locked()

    def test_remove_edge_source_locked(self):
        super().test_remove_edge_source_locked()

    def test_remove_edge_sink_locked(self):
        super().test_remove_edge_sink_locked()

    def test_get_edge_label(self):
        super().test_get_edge_label()

    def test_get_locked_edge_label(self):
        super().test_get_locked_edge_label()

    def test_get_edge_source(self):
        super().test_get_edge_source()

    def test_get_locked_edge_source(self):
        super().test_get_locked_edge_source()

    def test_get_edge_sink(self):
        super().test_get_edge_sink()

    def test_get_locked_edge_sink(self):
        super().test_get_locked_edge_sink()


class TestTransactionDataKeys(base.BaseControllerDataKeysTestCase):
    base_controller_subclass = Transaction

    def test_get_data_key(self):
        super().test_get_data_key()

    def test_set_data_key(self):
        super().test_set_data_key()

    def test_clear_data_key(self):
        super().test_clear_data_key()

    def test_has_data_key(self):
        super().test_has_data_key()

    def test_iter_data_keys(self):
        super().test_iter_data_keys()

    def test_count_data_keys(self):
        super().test_count_data_keys()
