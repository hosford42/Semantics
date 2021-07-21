from unittest import TestCase

from semantics.data_types import language_ids
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
        self.assertFalse(word.has_spelling())
        vertex.set_data_key('spelling', 'spelling')
        self.assertTrue(word.has_spelling())

    def test_spelling(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertIsNone(word.spelling)
        vertex.name = 'vertex'
        self.assertIsNone(word.spelling)
        vertex.set_data_key('spelling', 'spelling')
        self.assertEqual('spelling', word.spelling)

    def test_has_language(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertFalse(word.has_language())
        vertex.set_data_key('language', language_ids.LanguageID('eng'))
        self.assertTrue(word.has_language())

    def test_language(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertIsNone(word.language)
        vertex.set_data_key('language', language_ids.LanguageID('eng'))
        self.assertEqual(language_ids.LanguageID('eng'), word.language)

    def test_kinds(self):
        kind1 = self.kb.get_kind('word', 1, add=True)
        kind2 = self.kb.get_kind('word', 2, add=True)
        kind3 = self.kb.get_kind('a different word', 1, add=True)
        word = self.kb.get_word('word')
        self.assertIn(kind1, word.kinds)
        self.assertIn(kind2, word.kinds)
        self.assertNotIn(kind3, word.kinds)
        self.assertEqual(2, len(word.kinds))
