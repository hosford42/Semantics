from semantics.graph_layer.connections import GraphDBConnection
from semantics.graph_layer.graph_db import GraphDB
from test_semantics.test_graph_layer import base


class TestGraphDB(base.GraphDBInterfaceTestCase):
    graph_db_interface_subclass = GraphDB

    def test_connect(self):
        db = GraphDB()
        connection = db.connect()
        self.assertIsInstance(connection, GraphDBConnection)

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

    def test_get_label(self):
        super().test_get_label()

    def test_get_role(self):
        super().test_get_role()
