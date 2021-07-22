from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Kind


class TestKind(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_repr(self):
        kind1 = self.kb.get_kind('kind1', 1, add=True)
        kind1_repr = repr(kind1)
        self.assertIsInstance(kind1_repr, str)
        self.assertTrue(kind1_repr)
        kind2 = self.kb.get_kind('kind2', 1, add=True)
        self.assertNotEqual(kind1_repr, repr(kind2))

    def test_has_name(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        kind = Kind(vertex, self.kb.database)
        self.assertFalse(kind.has_name())
        kind.name.set(self.kb.get_word('word', add=True))
        self.assertTrue(kind.has_name())

    def test_name(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        kind = Kind(vertex, self.kb.database)
        self.assertIsNone(kind.name.get())
        name1 = self.kb.get_word('name1', add=True)
        kind.name.set(name1)
        self.assertEqual(kind.name.get(), name1)
        name2 = self.kb.get_word('name2', add=True)
        kind.name.set(name2)
        self.assertEqual(kind.name.get(), name2)
        kind.name.set(name1)
        self.assertEqual(kind.name.get(), name1)
        kind.name.set(name2)
        self.assertEqual(kind.name.get(), name2)
        name3 = self.kb.get_word('name3', add=True)
        kind.name.set(name3)
        self.assertEqual(kind.name.get(), name3)

    def test_names(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        kind = Kind(vertex, self.kb.database)
        self.assertEqual([], list(kind.names))
        name1 = self.kb.get_word('name1', add=True)
        kind.names.add(name1)
        self.assertEqual([name1], list(kind.names))
        name2 = self.kb.get_word('name2', add=True)
        kind.names.add(name2)
        kind.names.add(name2)
        self.assertEqual([name2, name1], kind.names.descending())
        kind.names.add(name1)
        self.assertEqual([name1, name2], kind.names.descending())
        kind.names.add(name2)
        self.assertEqual([name2, name1], kind.names.descending())
        name3 = self.kb.get_word('name3', add=True)
        kind.names.add(name3)
        self.assertEqual([name2, name1, name3], kind.names.descending())

    def test_instances(self):
        kind = self.kb.get_kind('kind', 1, add=True)
        self.assertEqual([], list(kind.instances))
        instance1 = self.kb.add_instance(kind)
        self.assertEqual([instance1], list(kind.instances))
        instance2 = self.kb.add_instance(kind)
        self.assertEqual({instance1, instance2}, set(kind.instances))
        kind.instances.remove(instance1)
        # Doing it just once doesn't remove it, because we have a preference threshold of 0.5 and
        # preference of 0.5. One positive evidence sample perfectly balances one negative evidence
        # sample.
        self.assertEqual([instance2, instance1], kind.instances.descending())
        kind.instances.remove(instance1)
        # However, doing it twice drops the preference below the threshold, and the instance no
        # longer shows up when validation is used.
        self.assertEqual([instance2], list(kind.instances))
