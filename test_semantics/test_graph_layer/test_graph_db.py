from semantics.graph_layer.connections import GraphDBConnection
from semantics.graph_layer.graph_db import GraphDB
from test_semantics.test_graph_layer import base


class TestGraphDB(base.GraphDBInterfaceTestCase):
    graph_db_interface_subclass = GraphDB

    def test_connect(self):
        db = GraphDB()
        connection = db.connect()
        self.assertIsInstance(connection, GraphDBConnection)

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

    def test_add_catalog(self):
        super().test_add_catalog()

    def test_get_catalog(self):
        super().test_get_catalog()
