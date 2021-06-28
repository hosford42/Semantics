from semantics.data_control.transactions import Transaction
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

    def test_add_role(self):
        self.fail()

    def test_add_vertex(self):
        self.fail()

    def test_add_label(self):
        self.fail()

    def test_add_edge(self):
        self.fail()

    def test_update_role(self):
        self.fail()

    def test_update_vertex(self):
        self.fail()

    def test_update_label(self):
        self.fail()

    def test_update_edge(self):
        self.fail()

    def test_remove_role(self):
        self.fail()

    def test_remove_vertex(self):
        self.fail()

    def test_remove_label(self):
        self.fail()

    def test_remove_edge(self):
        self.fail()


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

    def test_add_role(self):
        self.fail()

    def test_add_vertex(self):
        self.fail()

    def test_add_label(self):
        self.fail()

    def test_add_edge(self):
        self.fail()

    def test_update_role(self):
        self.fail()

    def test_update_vertex(self):
        self.fail()

    def test_update_label(self):
        self.fail()

    def test_update_edge(self):
        self.fail()

    def test_remove_role(self):
        self.fail()

    def test_remove_vertex(self):
        self.fail()

    def test_remove_label(self):
        self.fail()

    def test_remove_edge(self):
        self.fail()


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

    def test_get_name(self):
        super().test_get_name()

    def test_find(self):
        super().test_find()


class TestTransactionLabels(base.BaseControllerLabelsTestCase):
    base_controller_subclass = Transaction

    def test_add(self):
        super().test_add()

    def test_remove(self):
        super().test_remove()

    def test_get_name(self):
        super().test_get_name()

    def test_find(self):
        super().test_find()


class TestTransactionVertices(base.BaseControllerVerticesTestCase):
    base_controller_subclass = Transaction

    def test_add_vertex(self):
        super().test_add_vertex()

    def test_get_vertex_preferred_role(self):
        super().test_get_vertex_preferred_role()

    def test_get_vertex_name(self):
        super().test_get_vertex_name()

    def test_set_vertex_name(self):
        super().test_set_vertex_name()

    def test_get_vertex_time_stamp(self):
        super().test_get_vertex_time_stamp()

    def test_set_vertex_time_stamp(self):
        super().test_set_vertex_time_stamp()

    def test_find_vertex(self):
        super().test_find_vertex()

    def test_count_vertex_outbound(self):
        super().test_count_vertex_outbound()

    def test_iter_vertex_inbound(self):
        super().test_iter_vertex_outbound()

    def test_count_vertex_inbound(self):
        super().test_count_vertex_inbound()

    def test_iter_vertex_outbound(self):
        super().test_iter_vertex_inbound()


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

    def test_remove_edge(self):
        super().test_remove_edge()

    def test_get_edge_label(self):
        super().test_get_edge_label()

    def test_get_edge_source(self):
        super().test_get_edge_source()

    def test_get_edge_sink(self):
        super().test_get_edge_sink()
