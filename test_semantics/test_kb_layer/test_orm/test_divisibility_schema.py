import unittest

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Divisibility


class TestDivisibility(unittest.TestCase):

    def test_divisible_property(self):
        kb = KnowledgeBase()
        vertex = kb.database.add_vertex(kb.roles.divisibility)
        divisibility = Divisibility(vertex, kb.database)
        with self.assertRaises(AttributeError):
            _divisible = divisibility.divisible
        vertex.set_data_key('divisible', True)
        self.assertTrue(divisibility.divisible)
        vertex.set_data_key('divisible', False)
        self.assertFalse(divisibility.divisible)

    def test_countable_property(self):
        kb = KnowledgeBase()
        vertex = kb.database.add_vertex(kb.roles.divisibility)
        divisibility = Divisibility(vertex, kb.database)
        with self.assertRaises(AttributeError):
            _countable = divisibility.countable
        vertex.set_data_key('countable', True)
        self.assertTrue(divisibility.countable)
        vertex.set_data_key('countable', False)
        self.assertFalse(divisibility.countable)
