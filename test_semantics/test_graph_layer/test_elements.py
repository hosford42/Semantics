from unittest import TestCase

from semantics.data_types.exceptions import InvalidatedReferenceError
from semantics.graph_layer.graph_db import GraphDB


class TestElement(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

    def test_copy(self):
        self.fail()

    def test_release(self):
        self.fail()

    def test_remove(self):
        self.fail()

    def test_get_data_key(self):
        self.fail()

    def test_set_data_key(self):
        self.fail()

    def test_clear_data_key(self):
        self.fail()

    def test_has_data_key(self):
        self.fail()

    def test_iter_data_keys(self):
        self.fail()

    def test_count_data_keys(self):
        self.fail()


class TestRole(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

    def test_name(self):
        role = self.db.get_role('role', add=True)
        self.assertEqual(role.name, 'role')

    def test_remove(self):
        role = self.db.get_role('role', add=True)
        self.assertIsNotNone(self.db.get_role('role'))
        role.remove()
        with self.assertRaises(InvalidatedReferenceError):
            _name = role.name
        self.assertIsNone(self.db.get_role('role'))


class TestVertex(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()
        self.role = self.db.get_role('role', add=True)

    def test_preferred_role(self):
        vertex = self.db.add_vertex(self.role)
        self.assertEqual(vertex.preferred_role, self.role)

    def test_name(self):
        vertex = self.db.add_vertex(self.role)
        import threading
        self.assertIsNone(vertex.name, None)
        vertex.name = 'vertex'
        self.assertEqual(vertex.name, 'vertex')
        self.assertEqual(self.db.find_vertex('vertex'), vertex)

    def test_time_stamp(self):
        self.fail()

    def test_remove(self):
        self.fail()

    def test_count_outbound(self):
        self.fail()

    def test_iter_outbound(self):
        self.fail()

    def test_count_inbound(self):
        self.fail()

    def test_iter_inbound(self):
        self.fail()

    def test_add_edge_to(self):
        self.fail()

    def test_add_edge_from(self):
        self.fail()

    def test_add_edge(self):
        self.fail()


class TestLabel(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

    def test_name(self):
        self.fail()

    def test_remove(self):
        self.fail()


class TestEdge(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

    def test_label(self):
        self.fail()

    def test_source(self):
        self.fail()

    def test_sink(self):
        self.fail()

    def test_remove(self):
        self.fail()
