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
    def test_roles(self):
        self.fail()

    @abstractmethod
    def test_get_word(self):
        self.fail()

    @abstractmethod
    def test_add_kind(self):
        self.fail()

    @abstractmethod
    def test_add_instance(self):
        self.fail()

    @abstractmethod
    def test_add_time(self):
        self.fail()

    @abstractmethod
    def test_add_manifestation(self):
        self.fail()
