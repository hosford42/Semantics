from semantics.kb_layer.knowledge_base import KnowledgeBase
from test_semantics.test_kb_layer import base


class TestKnowledgeBase(base.KnowledgeBaseInterfaceTestCase):
    kb_interface_subclass = KnowledgeBase

    def test_db(self):
        self.fail()

    def test_connect(self):
        self.fail()

    def test_roles(self):
        super().test_roles()

    def test_get_word(self):
        super().test_get_word()

    def test_add_kind(self):
        super().test_add_kind()

    def test_add_instance(self):
        super().test_add_instance()

    def test_add_time(self):
        super().test_add_time()

    def test_add_manifestation(self):
        super().test_add_manifestation()
