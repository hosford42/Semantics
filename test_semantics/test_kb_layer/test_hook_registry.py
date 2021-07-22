from unittest import TestCase

from semantics.kb_layer.hook_registry import register, iter_hooks


def fake_module_level_function():
    pass


class TestFunctions(TestCase):

    def test_register(self):
        with self.assertRaises(ValueError):
            register(lambda: None)

        def fake_locally_defined_function():
            pass

        with self.assertRaises(ValueError):
            register(fake_locally_defined_function)

        class FakeCallable:
            def __call__(self):
                pass

        with self.assertRaises(ValueError):
            register(FakeCallable())

        register(fake_module_level_function)

    def test_iter_hooks(self):
        register(fake_module_level_function)
        self.assertIn(fake_module_level_function, iter_hooks())
