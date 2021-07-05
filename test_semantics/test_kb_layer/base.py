from abc import ABC, abstractmethod
from typing import Type
from unittest import TestCase, SkipTest

from semantics.kb_layer.connections import KnowledgeBaseConnection
from semantics.kb_layer.interface import KnowledgeBaseInterface
from semantics.kb_layer.knowledge_base import KnowledgeBase


class KnowledgeBaseInterfaceTestCase(TestCase, ABC):

    kb_interface_subclass: Type[KnowledgeBaseInterface]

    @classmethod
    def setUpClass(cls) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if cls.__name__.startswith('KnowledgeBaseInterface') and cls.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % cls.__name__)
        assert hasattr(cls, 'kb_interface_subclass'), \
            "You need to define kb_interface_subclass in your unit test class %s" % \
            cls.__qualname__

    def setUp(self) -> None:
        # The __init__.py of this package excludes this file, but in the off chance
        # a different method was used that incorrectly loads these abstract base
        # classes, we should ignore them.
        if self.__class__.__name__.startswith('KnowledgeBaseInterface') and \
                self.__class__.__name__.endswith('TestCase'):
            raise SkipTest("Test case abstract base class %s ignored." % self.__class__.__name__)
        assert hasattr(self, 'kb_interface_subclass'), \
            "You need to define kb_interface_subclass in your unit test class %s" % \
            self.__class__.__qualname__

        self.kb = KnowledgeBase()
        self.connection = self.kb.connect()

        if self.kb_interface_subclass is KnowledgeBase:
            self.interface = self.kb
        else:
            assert self.kb_interface_subclass is KnowledgeBaseConnection
            self.interface = self.connection

    @abstractmethod
    def test_get_word(self):
        self.assertIsNone(self.interface.get_word('gibberish'))
        word = self.interface.get_word('gibberish', add=True)
        self.assertIsNotNone(word)
        self.assertEqual(self.interface.get_word('gibberish'), word)
        self.assertEqual(self.interface.get_word('gibberish', add=True), word)
        self.assertEqual(word.spelling, 'gibberish')

    @abstractmethod
    def test_add_kind(self):
        # Must provide at least one name for new kinds
        with self.assertRaises(ValueError):
            self.interface.add_kind()
        # TODO: This is getting an error because we have built-in roles but not built-in labels.
        #       We need to add built-in labels and make NAME one of them.
        kind = self.interface.add_kind('name1', 'name2')
        name1 = self.interface.get_word('name1')
        self.assertIsNotNone(name1)
        name2 = self.interface.get_word('name2')
        self.assertIsNotNone(name2)
        self.assertNotEqual(name1, name2)
        self.assertIn(name1, kind.names)
        self.assertIn(name2, kind.names)
        self.assertEqual(len(list(kind.names)), 2)

    @abstractmethod
    def test_add_instance(self):
        self.fail()

    @abstractmethod
    def test_add_time(self):
        self.fail()

    @abstractmethod
    def test_add_manifestation(self):
        self.fail()
