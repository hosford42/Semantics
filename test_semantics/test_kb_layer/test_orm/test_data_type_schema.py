from unittest import TestCase

from semantics.kb_layer.orm import Kind

from semantics.kb_layer.knowledge_base import KnowledgeBase


# TODO: None of this is implemented yet. Once it is, subsume Time with the new framework.

class TestNumberKind(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_type_is_kind(self):
        kind = self.kb.get_data_type(float, add=True)
        self.assertIsInstance(kind, Kind)

    def test_value_type(self):
        kind = self.kb.get_data_type(float, add=True)
        self.assertIs(float, kind.value_type)

    def test_name(self):
        kind = self.kb.get_data_type(float, 'number', add=True)
        self.assertEqual(self.kb.get_word('number', add=True), kind.name.get())
