from semantics.kb_layer.connections import KnowledgeBaseConnection
from semantics.kb_layer.knowledge_base import KnowledgeBase
from test_semantics.test_kb_layer import base


class TestKnowledgeBase(base.KnowledgeBaseInterfaceTestCase):
    kb_interface_subclass = KnowledgeBase

    def test_connect(self):
        connection = self.kb.connect()
        self.assertIsInstance(connection, KnowledgeBaseConnection)
        self.assertTrue(connection.is_open)

    def test_get_word(self):
        super().test_get_word()

    def test_get_kind(self):
        super().test_get_kind()

    def test_add_instance(self):
        super().test_add_instance()

    def test_add_time(self):
        super().test_add_time()

    def test_add_observation(self):
        super().test_add_observation()
