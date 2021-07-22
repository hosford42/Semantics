from semantics.data_types.exceptions import ConnectionClosedError
from semantics.graph_layer.connections import GraphDBConnection
from test_semantics.test_graph_layer import base


class FakeException(Exception):
    pass


class TestGraphDBConnection(base.GraphDBInterfaceTestCase):
    graph_db_interface_subclass = GraphDBConnection

    def test_context_manager_protocol_normal_exit(self):
        """
        Verify:
            * The context manager returns an open connection on entering the with block.
            * When exiting the `with` block normally:
                * Pending changes are committed.
                * The connection is automatically closed.
                * Any held references cannot be used.
        """
        with GraphDBConnection(self.db) as connection:
            self.assertIsInstance(connection, GraphDBConnection)
            self.assertTrue(connection.is_open)
            new_role = connection.get_role('new_role', add=True)
            self.assertIsNotNone(new_role)
            self.assertIsNone(self.db.get_role('new_role'))
        self.assertFalse(connection.is_open)
        self.assertIsNotNone(self.db.get_role('new_role'))
        with self.assertRaises(ConnectionClosedError):
            _name = new_role.name

    def test_context_manager_protocol_unhandled_exception(self):
        """
        Verify:
            * When exiting the `with` block due to exception:
                * Pending changes are rolled back.
                * The connection is automatically closed.
        """
        with self.assertRaises(FakeException):
            with GraphDBConnection(self.db) as connection:
                self.assertIsInstance(connection, GraphDBConnection)
                self.assertTrue(connection.is_open)
                new_role = connection.get_role('new_role', add=True)
                self.assertIsNotNone(new_role)
                self.assertIsNone(self.db.get_role('new_role'))
                raise FakeException()
        self.assertFalse(connection.is_open)
        self.assertIsNone(self.db.get_role('new_role'))
        with self.assertRaises(ConnectionClosedError):
            _name = new_role.name

    def test_commit(self):
        """
        Verify:
            * Changes are not applied to the database before the commit.
            * Changes are applied to the database after the commit.
            * There are no pending changes after the commit.
            * The connection is still open.
        """
        with GraphDBConnection(self.db) as connection:
            self.assertIsInstance(connection, GraphDBConnection)
            self.assertTrue(connection.is_open)
            new_role = connection.get_role('new_role', add=True)
            self.assertIsNotNone(new_role)
            self.assertIsNone(self.db.get_role('new_role'))
            connection.commit()
            self.assertTrue(connection.is_open)
            self.assertIsNotNone(self.db.get_role('new_role'))
            _name = new_role.name
            # TODO: Verify that the change audit contents are added to the database on commit.
        self.assertFalse(connection.is_open)
        self.assertIsNotNone(self.db.get_role('new_role'))
        with self.assertRaises(ConnectionClosedError):
            _name = new_role.name

    def test_rollback(self):
        """
        Verify:
            * Changes are not applied to the database before the rollback.
            * Changes are not applied to the database after the rollback.
            * There are no pending changes after the rollback.
            * The connection is still open.
        """
        with GraphDBConnection(self.db) as connection:
            self.assertIsInstance(connection, GraphDBConnection)
            self.assertTrue(connection.is_open)
            new_role = connection.get_role('new_role', add=True)
            self.assertIsNotNone(new_role)
            self.assertIsNone(self.db.get_role('new_role'))
            connection.rollback()
            self.assertTrue(connection.is_open)
            self.assertIsNone(self.db.get_role('new_role'))
            with self.assertRaises(KeyError):
                _name = new_role.name
            # TODO: Verify that the change audit contents are cleared and not added to the database
            #       on rollback.
        self.assertFalse(connection.is_open)
        self.assertIsNone(self.db.get_role('new_role'))
        with self.assertRaises(ConnectionClosedError):
            _name = new_role.name

    def test_del(self):
        """
        Verify:
            * When the connection is garbage-collected:
                * Any pending changes are rolled back.
                * The connection is automatically closed.
        """
        connection = GraphDBConnection(self.db)
        self.assertIsInstance(connection, GraphDBConnection)
        self.assertTrue(connection.is_open)
        new_role = connection.get_role('new_role', add=True)
        self.assertIsNotNone(new_role)
        new_vertex = connection.add_vertex(new_role)
        self.assertIsNotNone(new_vertex)
        self.assertIsNone(self.db.get_role('new_role'))
        with self.assertRaises(KeyError):
            self.db.get_vertex(new_vertex.index)
        connection.__del__()
        self.assertIsNone(self.db.get_role('new_role'))
        with self.assertRaises(KeyError):
            self.db.get_vertex(new_vertex.index)

    def test_closed_connection(self):
        with GraphDBConnection(self.db) as connection:
            connection.close()  # Can close early in with block w/o error
        self.assertFalse(connection.is_open)
        connection.close()  # Can close it twice w/o error
        with self.assertRaises(ConnectionClosedError):
            connection.commit()
        with self.assertRaises(ConnectionClosedError):
            connection.rollback()

    def test_del_after_failed_init(self):
        connection = GraphDBConnection(self.db)
        # Simulate __init__ being interrupted before transaction is created.
        connection._transaction = None
        # Simulate garbage collection of connection after interrupted init.
        connection.__del__()  # Should not cause an exception.

    def test_repr(self):
        super().test_repr()

    def test_get_all_vertices(self):
        super().test_get_all_vertices()

    def test_get_vertex(self):
        super().test_get_vertex()

    def test_add_vertex(self):
        super().test_add_vertex()

    def test_find_vertex(self):
        super().test_find_vertex()

    def test_get_edge(self):
        super().test_get_edge()

    def test_add_edge(self):
        super().test_add_edge()

    def test_find_edge(self):
        super().test_find_edge()

    def test_get_label(self):
        super().test_get_label()

    def test_get_role(self):
        super().test_get_role()

    def test_get_audit(self):
        super().test_get_audit()

    def test_get_audit_count(self):
        super().test_get_audit_count()

    def test_clear_audit(self):
        super().test_clear_audit()

    def test_pop_most_recently_audited(self):
        super().test_pop_most_recently_audited()

    def test_pop_least_recently_audited(self):
        super().test_pop_least_recently_audited()
