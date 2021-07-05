from unittest import TestCase

from semantics.kb_layer.connections import KnowledgeBaseConnection
from semantics.kb_layer.knowledge_base import KnowledgeBase


class MockException(Exception):
    pass


class TestKnowledgeBaseConnection(TestCase):

    def test_context_manager_protocol(self):
        kb = KnowledgeBase()
        with kb.connect() as connection:
            self.assertIsInstance(connection, KnowledgeBaseConnection)
            self.assertTrue(connection.is_open)
            word = connection.get_word('word', add=True)
        self.assertFalse(connection.is_open)
        # Changes committed automatically if there is no exception.
        self.assertEqual(kb.get_word('word'), word)
        with self.assertRaises(MockException):
            with kb.connect() as connection:
                self.assertIsInstance(connection, KnowledgeBaseConnection)
                self.assertTrue(connection.is_open)
                connection.get_word('word2', add=True)
                raise MockException()
        self.assertFalse(connection.is_open)
        # Changes rolled back automatically if there is an exception.
        self.assertIsNone(kb.get_word('word2'))

    def test_commit(self):
        kb = KnowledgeBase()
        connection = kb.connect()
        word = connection.get_word('word', add=True)
        self.assertIsNone(kb.get_word('word'))
        self.assertEqual(connection.get_word('word'), word)
        connection.commit()
        self.assertEqual(kb.get_word('word'), word)
        self.assertEqual(connection.get_word('word'), word)

    def test_rollback(self):
        kb = KnowledgeBase()
        connection = kb.connect()
        word = connection.get_word('word', add=True)
        self.assertIsNone(kb.get_word('word'))
        self.assertEqual(connection.get_word('word'), word)
        connection.rollback()
        self.assertIsNone(kb.get_word('word'))
        self.assertIsNone(connection.get_word('word'))
