from abc import ABC, abstractmethod
from typing import Type
from unittest import TestCase, SkipTest

from semantics.data_types import data_access
from semantics.data_types.indices import VertexID, EdgeID
from semantics.graph_layer.connections import GraphDBConnection
from semantics.graph_layer.elements import Vertex, Edge, Role, Label
from semantics.graph_layer.graph_db import GraphDB
from semantics.graph_layer.interface import GraphDBInterface


class GraphDBInterfaceTestCase(TestCase, ABC):

    graph_db_interface_subclass: Type[GraphDBInterface]

    @classmethod
    def setUpClass(cls) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if cls.__name__.startswith('GraphDBInterface') and cls.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % cls.__name__)
        assert hasattr(cls, 'graph_db_interface_subclass'), \
            "You need to define graph_db_interface_subclass in your unit test class %s" % \
            cls.__qualname__

    def setUp(self) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if self.__class__.__name__.startswith('GraphDBInterface') and \
                self.__class__.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % self.__class__.__name__)
        assert hasattr(self, 'graph_db_interface_subclass'), \
            "You need to define graph_db_interface_subclass in your unit test class %s" % \
            self.__class__.__qualname__

        self.db = GraphDB()
        self.connection = self.db.connect()

        if self.graph_db_interface_subclass is GraphDB:
            self.interface = self.db
        else:
            assert self.graph_db_interface_subclass is GraphDBConnection
            self.interface = self.connection

        # Populate the database with some pre-existing elements.
        self.preexisting_role = self.db.get_role('preexisting_role', add=True)
        self.preexisting_source = self.db.add_vertex(self.preexisting_role)
        self.preexisting_sink = self.db.add_vertex(self.preexisting_role)
        self.preexisting_label = self.db.get_label('preexisting_label', add=True)
        self.preexisting_edge = self.db.add_edge(self.preexisting_label,
                                                 self.preexisting_source,
                                                 self.preexisting_sink)

    @abstractmethod
    def test_repr(self):
        result = repr(self.interface)
        self.assertIsInstance(result, str)
        self.assertTrue(result)

    @abstractmethod
    def test_get_all_vertices(self):
        self.assertEqual({self.preexisting_source, self.preexisting_sink},
                         self.interface.get_all_vertices())

    @abstractmethod
    def test_get_vertex(self):
        invalid_id = VertexID(-1)
        with self.assertRaises(KeyError):
            self.interface.get_vertex(invalid_id)
        vertex = self.interface.get_vertex(self.preexisting_source.index)
        self.assertIsInstance(vertex, Vertex)
        self.assertEqual(self.preexisting_source, vertex)

    @abstractmethod
    def test_add_vertex(self):
        vertex = self.interface.add_vertex(self.preexisting_role)
        self.assertIsInstance(vertex, Vertex)
        self.assertIsNone(vertex.name)

    @abstractmethod
    def test_find_vertex(self):
        self.assertIsNone(self.interface.find_vertex('vertex'))
        vertex = self.interface.add_vertex(self.preexisting_role)
        vertex.name = 'vertex'
        self.assertEqual(self.interface.find_vertex('vertex'), vertex)

    @abstractmethod
    def test_get_edge(self):
        invalid_id = EdgeID(-1)
        with self.assertRaises(KeyError):
            self.interface.get_edge(invalid_id)
        edge = self.interface.get_edge(self.preexisting_edge.index)
        self.assertIsInstance(edge, Edge)
        self.assertEqual(edge, self.preexisting_edge)

    @abstractmethod
    def test_add_edge(self):
        # We have to reverse the source and sink since there's already an edge in that direction.
        source = self.preexisting_sink
        sink = self.preexisting_source
        edge = self.interface.add_edge(self.preexisting_label, source, sink)
        self.assertIsInstance(edge, Edge)
        self.assertEqual(edge.label, self.preexisting_label)
        self.assertEqual(edge.source, source)
        self.assertEqual(edge.sink, sink)

    @abstractmethod
    def test_find_edge(self):
        self.assertIsNone(self.interface.find_edge(self.preexisting_label, self.preexisting_source,
                                                   self.preexisting_source))
        self.assertIsNone(self.interface.find_edge(self.preexisting_label, self.preexisting_sink,
                                                   self.preexisting_sink))
        self.assertIsNone(self.interface.find_edge(self.preexisting_label, self.preexisting_sink,
                                                   self.preexisting_source))
        another_label = self.db.get_label('another_label', add=True)
        self.assertIsNone(self.interface.find_edge(another_label, self.preexisting_source,
                                                   self.preexisting_sink))
        self.assertEqual(self.preexisting_edge,
                         self.interface.find_edge(self.preexisting_label, self.preexisting_source,
                                                  self.preexisting_sink))

    @abstractmethod
    def test_get_label(self):
        self.assertIsNone(self.interface.get_label('label'))
        label = self.interface.get_label('label', add=True)
        self.assertEqual(label, self.interface.get_label('label'))
        self.assertEqual(label, self.interface.get_label('label', add=True))
        self.assertEqual(label.name, 'label')

    @abstractmethod
    def test_get_role(self):
        self.assertIsNone(self.interface.get_role('role'))
        role = self.interface.get_role('role', add=True)
        self.assertEqual(role, self.interface.get_role('role'))
        self.assertEqual(role, self.interface.get_role('role', add=True))
        self.assertEqual(role.name, 'role')

    @abstractmethod
    def test_get_audit(self):
        # Audits should initially be blank since we haven't turned auditing on anywhere.
        self.assertEqual([], self.interface.get_audit(Vertex))

        vertex1 = self.interface.add_vertex(self.preexisting_role)
        vertex2 = self.interface.add_vertex(self.preexisting_role, audit=True)
        vertex1.audit = True
        self.interface.add_vertex(self.preexisting_role)

        self.assertEqual([vertex2, vertex1], self.interface.get_audit(Vertex))

    @abstractmethod
    def test_get_audit_count(self):
        # Audits should initially be blank since we haven't turned auditing on anywhere.
        self.assertEqual(0, self.interface.get_audit_count(Vertex))

        self.interface.add_vertex(self.preexisting_role, audit=True)
        self.interface.add_vertex(self.preexisting_role, audit=True)
        self.interface.add_vertex(self.preexisting_role)

        self.assertEqual(2, self.interface.get_audit_count(Vertex))

    @abstractmethod
    def test_clear_audit(self):
        self.interface.add_vertex(self.preexisting_role, audit=True)
        self.interface.add_vertex(self.preexisting_role, audit=True)
        self.interface.add_vertex(self.preexisting_role)

        self.interface.clear_audit(Vertex)

        self.assertEqual(0, self.interface.get_audit_count(Vertex))
        self.assertEqual([], self.interface.get_audit(Vertex))

    @abstractmethod
    def test_pop_most_recently_audited(self):
        self.assertIsNone(self.interface.pop_most_recently_audited(Vertex))

        vertex1 = self.interface.add_vertex(self.preexisting_role)
        self.interface.add_vertex(self.preexisting_role, audit=True)
        vertex1.audit = True
        self.interface.add_vertex(self.preexisting_role)

        self.assertEqual(vertex1, self.interface.pop_most_recently_audited(Vertex))

    @abstractmethod
    def test_pop_least_recently_audited(self):
        self.assertIsNone(self.interface.pop_least_recently_audited(Vertex))

        vertex1 = self.interface.add_vertex(self.preexisting_role)
        vertex2 = self.interface.add_vertex(self.preexisting_role, audit=True)
        vertex1.audit = True
        self.interface.add_vertex(self.preexisting_role)

        self.assertEqual(vertex2, self.interface.pop_least_recently_audited(Vertex))
