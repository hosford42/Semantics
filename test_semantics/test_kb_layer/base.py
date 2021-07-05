from abc import ABC, abstractmethod
from typing import Type
from unittest import TestCase, SkipTest

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.connections import KnowledgeBaseConnection
from semantics.kb_layer.interface import KnowledgeBaseInterface
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Kind, Word, Instance, Time


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
        self.assertIsInstance(word, Word)
        self.assertEqual(self.interface.get_word('gibberish'), word)
        self.assertEqual(self.interface.get_word('gibberish', add=True), word)
        self.assertEqual(word.spelling, 'gibberish')

    @abstractmethod
    def test_add_kind(self):
        # Must provide at least one name for new kinds
        with self.assertRaises(ValueError):
            self.interface.add_kind()
        kind = self.interface.add_kind('name1', 'name2')
        self.assertIsInstance(kind, Kind)
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
        kind = self.interface.add_kind('kind')
        instance = self.interface.add_instance(kind)
        self.assertIsInstance(instance, Instance)
        self.assertEqual(kind, instance.kind())
        self.assertIn(instance, kind.instances)
        self.assertIn(kind, instance.kinds)

    @abstractmethod
    def test_add_time(self):
        time1 = self.interface.add_time()
        self.assertIsInstance(time1, Time)
        self.assertIsNone(time1.time_stamp)
        time2 = self.interface.add_time()
        self.assertIsInstance(time2, Time)
        self.assertIsNone(time2.time_stamp)
        self.assertNotEqual(time1, time2)
        time3 = self.interface.add_time(TimeStamp(2.718281828))
        self.assertIsInstance(time3, Time)
        self.assertEqual(time3.time_stamp, TimeStamp(2.718281828))
        time4 = self.interface.add_time(TimeStamp(2.718281828))
        self.assertIsInstance(time4, Time)
        self.assertEqual(time4.time_stamp, TimeStamp(2.718281828))
        self.assertEqual(time3, time4)
        self.assertNotEqual(time1, time3)
        self.assertNotEqual(time2, time3)

    @abstractmethod
    def test_add_observation(self):
        kind = self.interface.add_kind('kind')
        instance = self.interface.add_instance(kind)
        time1 = self.interface.add_time(TimeStamp(1))
        time2 = self.interface.add_time(TimeStamp(2))
        observation1 = self.interface.add_observation(instance, time1)
        observation2 = self.interface.add_observation(instance, time2)
        self.assertNotEqual(observation1, observation2)
        self.assertEqual(observation1.instance(), instance)
        self.assertEqual(observation2.instance(), instance)
        self.assertIn(observation1, instance.observations)
        self.assertIn(observation2, instance.observations)
        self.assertIn(observation1, time1.observations)
        self.assertIn(observation2, time2.observations)
