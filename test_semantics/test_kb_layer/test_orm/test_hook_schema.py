from unittest import TestCase
from unittest.mock import MagicMock, patch

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Kind


def fake_hook1():
    pass


def fake_hook2():
    pass


class TestHook(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_repr(self):
        hook1 = self.kb.get_hook(fake_hook1)
        hook1_repr = repr(hook1)
        self.assertIsInstance(hook1_repr, str)
        self.assertTrue(hook1_repr)
        hook2 = self.kb.get_hook(fake_hook2)
        self.assertNotEqual(hook1_repr, repr(hook2))

    def test_module_name(self):
        hook = self.kb.get_hook(fake_hook1)
        self.assertEqual(__name__, hook.module_name)
        hook.vertex.set_data_key('module_name', '')
        self.assertIsNone(hook.module_name)

    def test_function_name(self):
        hook = self.kb.get_hook(fake_hook1)
        self.assertEqual('fake_hook1', hook.function_name)
        hook.vertex.set_data_key('function_name', '')
        self.assertIsNone(hook.function_name)

    def test_get_module(self):
        hook = self.kb.get_hook(fake_hook1)
        import sys
        this_module = sys.modules[__name__]
        self.assertIs(this_module, hook.get_module())
        hook.vertex.set_data_key('module_name', 'bad module name')
        self.assertIsNone(hook.get_module())

    def test_get_function(self):
        hook1 = self.kb.get_hook(fake_hook1)
        self.assertIs(fake_hook1, hook1.get_function())
        hook1.vertex.set_data_key('module_name', 'bad module name')
        self.assertIsNone(hook1.get_function())
        hook2 = self.kb.get_hook(fake_hook2)
        hook2.vertex.set_data_key('function_name', 'bad function name')
        self.assertIsNone(hook2.get_function())

    def test_call(self):
        hook = self.kb.get_hook(fake_hook1)
        with patch(__name__ + '.fake_hook1') as mock_hook:
            mock_hook.return_value = 'test result'
            result = hook('this', 'is', a='test')
            self.assertEqual('test result', result)
            mock_hook.assert_called_with('this', 'is', a='test')
