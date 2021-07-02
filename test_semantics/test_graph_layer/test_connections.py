from unittest import TestCase

from semantics.data_types.exceptions import ConnectionClosedError
from semantics.graph_layer.connections import GraphDBConnection
from semantics.graph_layer.graph_db import GraphDB


class MockException(Exception):
    pass


class TestGraphDBConnection(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

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
        with self.assertRaises(MockException):
            with GraphDBConnection(self.db) as connection:
                self.assertIsInstance(connection, GraphDBConnection)
                self.assertTrue(connection.is_open)
                new_role = connection.get_role('new_role', add=True)
                self.assertIsNotNone(new_role)
                self.assertIsNone(self.db.get_role('new_role'))
                raise MockException()
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
        del connection
        import gc
        gc.collect()
        self.assertIsNone(self.db.get_role('new_role'))
        with self.assertRaises(KeyError):
            self.db.get_vertex(new_vertex.index)
