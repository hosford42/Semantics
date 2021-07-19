from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Word


class TestWord(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_has_spelling(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertFalse(word.has_spelling())
        vertex.name = 'vertex'
        self.assertTrue(word.has_spelling())

    def test_spelling(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertIsNone(word.spelling)
        vertex.name = 'vertex'
        self.assertEqual(word.spelling, 'vertex')

    def test_kinds(self):
        kind1 = self.kb.add_kind('word')
        kind2 = self.kb.add_kind('word')
        kind3 = self.kb.add_kind('a different word')
        word = self.kb.get_word('word')
        self.assertIn(kind1, word.kinds)
        self.assertIn(kind2, word.kinds)
        self.assertNotIn(kind3, word.kinds)
        self.assertEqual(2, len(word.kinds))
