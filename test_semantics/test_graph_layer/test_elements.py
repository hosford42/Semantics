from unittest import TestCase

from semantics.data_types.exceptions import InvalidatedReferenceError, ResourceUnavailableError
from semantics.graph_layer.elements import Role
from semantics.graph_layer.graph_db import GraphDB
from test_semantics.test_data_types.test_data_access import threaded_call


class TestElement(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

    def test_copy(self):
        element = self.db.get_role('role', add=True)
        element.set_data_key('key', 'value')
        duplicate = element.copy()
        self.assertIsInstance(duplicate, Role)
        self.assertIsNot(element, duplicate)
        self.assertEqual(element, duplicate)
        duplicate.set_data_key('another key', 'another value')
        self.assertEqual(element.get_data_key('another key'), 'another value')
        self.assertEqual(duplicate.get_data_key('key'), 'value')
        element.remove()
        with self.assertRaises(KeyError):
            _name = duplicate.name

    def test_release(self):
        element = self.db.get_role('role', add=True)

        @threaded_call
        def _():
            duplicate = self.db.get_role('role')
            self.assertIsNotNone(duplicate)
            with self.assertRaises(ResourceUnavailableError):
                duplicate.set_data_key('key', 'value')

        element.release()
        with self.assertRaises(InvalidatedReferenceError):
            _name = element.name
        with self.assertRaises(InvalidatedReferenceError):
            element.get_data_key('key')

        @threaded_call
        def _():
            duplicate = self.db.get_role('role')
            self.assertIsNotNone(duplicate)
            duplicate.set_data_key('key', 'value')

        with self.assertRaises(InvalidatedReferenceError):
            _name = element.name
        with self.assertRaises(InvalidatedReferenceError):
            element.get_data_key('key')

    def test_get_data_key(self):
        element = self.db.get_role('role', add=True)
        self.assertIsNone(element.get_data_key('key'))
        element.set_data_key('key', 'value')
        self.assertEqual(element.get_data_key('key'), 'value')

    def test_set_data_key(self):
        element = self.db.get_role('role', add=True)
        self.assertIsNone(element.get_data_key('key'))
        element.set_data_key('key', 'value')
        self.assertEqual(element.get_data_key('key'), 'value')
        element.set_data_key('key', None)
        self.assertIsNone(element.get_data_key('key'))

    def test_clear_data_key(self):
        element = self.db.get_role('role', add=True)
        element.set_data_key('key', 'value')
        element.clear_data_key('key')
        self.assertIsNone(element.get_data_key('key'))
        element.clear_data_key('nonexistent key')
        self.assertIsNone(element.get_data_key('nonexistent key'))

    def test_has_data_key(self):
        element = self.db.get_role('role', add=True)
        self.assertFalse(element.has_data_key('key'))
        element.set_data_key('key', 'value')
        self.assertTrue(element.has_data_key('key'))
        element.set_data_key('key', None)
        self.assertFalse(element.has_data_key('key'))
        element.set_data_key('key', 'value')
        self.assertTrue(element.has_data_key('key'))
        element.clear_data_key('key')
        self.assertFalse(element.has_data_key('key'))

    def test_iter_data_keys(self):
        element = self.db.get_role('role', add=True)
        self.assertEqual(list(element.iter_data_keys()), [])
        element.set_data_key('key1', 'value1')
        element.set_data_key('key2', 'value2')
        self.assertEqual(sorted(element.iter_data_keys()), ['key1', 'key2'])
        element.clear_data_key('key1')
        self.assertEqual(list(element.iter_data_keys()), ['key2'])

    def test_count_data_keys(self):
        element = self.db.get_role('role', add=True)
        self.assertEqual(element.count_data_keys(), 0)
        element.set_data_key('key1', 'value1')
        element.set_data_key('key2', 'value2')
        self.assertEqual(element.count_data_keys(), 2)
        element.clear_data_key('key1')
        self.assertEqual(element.count_data_keys(), 1)


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


class TestCatalog(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()
        self.role = self.db.get_role('role', add=True)

    def test_name(self) -> None:
        catalog = self.db.get_catalog('catalog', add=True)
        self.assertEqual('catalog', catalog.name)

    def test_remove(self) -> None:
        catalog = self.db.get_catalog('catalog', add=True)
        catalog.remove()
        with self.assertRaises(InvalidatedReferenceError):
            _name = catalog.name
        self.assertIsNone(self.db.get_catalog('catalog'))

    def test_getitem(self):
        catalog = self.db.get_catalog('catalog', str, add=True)
        self.assertIsNone(catalog.get('vertex'))
        vertex = catalog['vertex'] = self.db.add_vertex(self.role)
        self.assertEqual(vertex, catalog['vertex'])

    def test_contains(self):
        catalog = self.db.get_catalog('catalog', str, add=True)
        self.assertNotIn('vertex', catalog)
        catalog['vertex'] = self.db.add_vertex(self.role)
        self.assertIn('vertex', catalog)

    def test_iter(self):
        catalog = self.db.get_catalog('catalog', str, ordered=True, add=True)
        self.assertEqual([], list(catalog))
        catalog['vertex2'] = self.db.add_vertex(self.role)
        catalog['vertex3'] = self.db.add_vertex(self.role)
        catalog['vertex1'] = self.db.add_vertex(self.role)
        self.assertEqual(['vertex1', 'vertex2', 'vertex3'], list(catalog))

    def test_len(self):
        catalog = self.db.get_catalog('catalog', str, add=True)
        self.assertEqual(0, len(catalog))
        catalog['vertex2'] = self.db.add_vertex(self.role)
        catalog['vertex3'] = self.db.add_vertex(self.role)
        catalog['vertex1'] = self.db.add_vertex(self.role)
        self.assertEqual(3, len(catalog))


class TestVertex(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()
        self.role = self.db.get_role('role', add=True)

    def test_preferred_role(self):
        vertex = self.db.add_vertex(self.role)
        self.assertEqual(vertex.preferred_role, self.role)

    def test_remove(self):
        vertex = self.db.add_vertex(self.role)
        self.assertIsNotNone(self.db.get_vertex(vertex.index))
        vertex.remove()
        with self.assertRaises(InvalidatedReferenceError):
            _name = vertex.get_data_key('name')
        with self.assertRaises(KeyError):
            self.db.get_vertex(vertex.index)

    def test_count_outbound(self):
        vertex = self.db.add_vertex(self.role)
        self.assertEqual(vertex.count_outbound(), 0)
        label = self.db.get_label('label', add=True)
        for _ in range(3):
            neighbor = self.db.add_vertex(self.role)
            vertex.add_edge_to(label, neighbor)
        self.assertEqual(vertex.count_outbound(), 3)

    def test_iter_outbound(self):
        vertex = self.db.add_vertex(self.role)
        self.assertEqual(list(vertex.iter_outbound()), [])
        label = self.db.get_label('label', add=True)
        edges = set()
        neighbors = set()
        for _ in range(3):
            neighbor = self.db.add_vertex(self.role)
            neighbors.add(neighbor)
            edges.add(vertex.add_edge_to(label, neighbor))
        self.assertEqual(set(vertex.iter_outbound()), edges)
        self.assertEqual({edge.sink for edge in vertex.iter_outbound()}, neighbors)
        self.assertEqual(len(list(vertex.iter_outbound())), len(edges))

    def test_count_inbound(self):
        vertex = self.db.add_vertex(self.role)
        self.assertEqual(vertex.count_inbound(), 0)
        label = self.db.get_label('label', add=True)
        for _ in range(3):
            neighbor = self.db.add_vertex(self.role)
            vertex.add_edge_from(label, neighbor)
        self.assertEqual(vertex.count_inbound(), 3)

    def test_iter_inbound(self):
        vertex = self.db.add_vertex(self.role)
        self.assertEqual(list(vertex.iter_inbound()), [])
        label = self.db.get_label('label', add=True)
        edges = set()
        neighbors = set()
        for _ in range(3):
            neighbor = self.db.add_vertex(self.role)
            neighbors.add(neighbor)
            edges.add(vertex.add_edge_from(label, neighbor))
        self.assertEqual(set(vertex.iter_inbound()), edges)
        self.assertEqual({edge.source for edge in vertex.iter_inbound()}, neighbors)
        self.assertEqual(len(list(vertex.iter_inbound())), len(edges))

    def test_add_edge_to(self):
        source = self.db.add_vertex(self.role)
        sink = self.db.add_vertex(self.role)
        label = self.db.get_label('label', add=True)
        edge = source.add_edge_to(label, sink)
        self.assertEqual(edge.label, label)
        self.assertEqual(edge.source, source)
        self.assertEqual(edge.sink, sink)
        self.assertEqual(source.count_inbound(), 0)
        self.assertEqual(source.count_outbound(), 1)
        self.assertEqual(sink.count_inbound(), 1)
        self.assertEqual(sink.count_outbound(), 0)

    def test_add_edge_from(self):
        source = self.db.add_vertex(self.role)
        sink = self.db.add_vertex(self.role)
        label = self.db.get_label('label', add=True)
        edge = sink.add_edge_from(label, source)
        self.assertEqual(edge.label, label)
        self.assertEqual(edge.source, source)
        self.assertEqual(edge.sink, sink)
        self.assertEqual(source.count_inbound(), 0)
        self.assertEqual(source.count_outbound(), 1)
        self.assertEqual(sink.count_inbound(), 1)
        self.assertEqual(sink.count_outbound(), 0)

    def test_add_edge(self):
        source = self.db.add_vertex(self.role)
        sink = self.db.add_vertex(self.role)
        label = self.db.get_label('label', add=True)
        edge = source.add_edge(label, sink, outbound=True)
        self.assertEqual(edge.label, label)
        self.assertEqual(edge.source, source)
        self.assertEqual(edge.sink, sink)
        self.assertEqual(source.count_inbound(), 0)
        self.assertEqual(source.count_outbound(), 1)
        self.assertEqual(sink.count_inbound(), 1)
        self.assertEqual(sink.count_outbound(), 0)
        edge.remove()
        edge = sink.add_edge(label, source, outbound=False)
        self.assertEqual(edge.label, label)
        self.assertEqual(edge.source, source)
        self.assertEqual(edge.sink, sink)
        self.assertEqual(source.count_inbound(), 0)
        self.assertEqual(source.count_outbound(), 1)
        self.assertEqual(sink.count_inbound(), 1)
        self.assertEqual(sink.count_outbound(), 0)


class TestLabel(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()

    def test_name(self):
        label = self.db.get_label('label', add=True)
        self.assertEqual(label.name, 'label')

    def test_remove(self):
        label = self.db.get_label('label', add=True)
        self.assertIsNotNone(self.db.get_label('label'))
        label.remove()
        with self.assertRaises(InvalidatedReferenceError):
            _name = label.name
        self.assertIsNone(self.db.get_label('label'))


class TestEdge(TestCase):

    def setUp(self) -> None:
        self.db = GraphDB()
        self.label = self.db.get_label('label', add=True)
        self.role = self.db.get_role('role', add=True)
        self.source = self.db.add_vertex(self.role)
        self.sink = self.db.add_vertex(self.role)

    def test_label(self):
        edge = self.db.add_edge(self.label, self.source, self.sink)
        self.assertEqual(edge.label, self.label)

    def test_source(self):
        edge = self.db.add_edge(self.label, self.source, self.sink)
        self.assertEqual(edge.source, self.source)

    def test_sink(self):
        edge = self.db.add_edge(self.label, self.source, self.sink)
        self.assertEqual(edge.sink, self.sink)

    def test_remove(self):
        edge = self.db.add_edge(self.label, self.source, self.sink)
        self.assertIsNotNone(self.db.get_edge(edge.index))
        edge.remove()
        with self.assertRaises(InvalidatedReferenceError):
            _source = edge.source
        with self.assertRaises(KeyError):
            self.db.get_edge(edge.index)
