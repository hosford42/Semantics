import logging
from abc import ABC, abstractmethod
from typing import Type
from unittest import TestCase, SkipTest
from unittest.mock import patch

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.connections import KnowledgeBaseConnection
from semantics.kb_layer.interface import KnowledgeBaseInterface
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Kind, Word, Instance, Time, Hook


def fake_hook1():
    pass


def fake_hook2():
    pass


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
    def test_get_divisibility(self):
        d00 = self.interface.get_divisibility(divisible=False, countable=False)
        d01 = self.interface.get_divisibility(divisible=False, countable=True)
        d10 = self.interface.get_divisibility(divisible=True, countable=False)
        d11 = self.interface.get_divisibility(divisible=True, countable=True)
        self.assertNotEqual(d00, d01)
        self.assertNotEqual(d00, d10)
        self.assertNotEqual(d00, d11)
        self.assertNotEqual(d01, d10)
        self.assertNotEqual(d01, d11)
        self.assertNotEqual(d10, d11)
        self.assertEqual(d00, self.interface.get_divisibility(divisible=False, countable=False))
        self.assertEqual(d01, self.interface.get_divisibility(divisible=False, countable=True))
        self.assertEqual(d10, self.interface.get_divisibility(divisible=True, countable=False))
        self.assertEqual(d11, self.interface.get_divisibility(divisible=True, countable=True))

    @abstractmethod
    def test_get_kind(self):
        # Must provide at least one name for new kinds
        with self.assertRaises(ValueError):
            self.interface.get_kind('', 1)
        kind = self.interface.get_kind('name', 1, add=False)
        self.assertIsNone(kind)
        kind = self.interface.get_kind('name', 1, add=True)
        self.assertIsInstance(kind, Kind)
        name = self.interface.get_word('name')
        self.assertIsNotNone(name)
        self.assertIn(name, kind.names)
        self.assertEqual(len(list(kind.names)), 1)
        self.assertEqual(kind, self.interface.get_kind('name', 1, add=False))
        self.assertEqual(kind, self.interface.get_kind('name', 1, add=True))
        self.assertIsNone(self.interface.get_kind('name', 2, add=False))
        self.assertNotEqual(kind, self.interface.get_kind('name', 2, add=True))

    @abstractmethod
    def test_add_instance(self):
        kind = self.interface.get_kind('kind', 1, add=True)
        instance = self.interface.add_instance(kind)
        self.assertIsInstance(instance, Instance)
        self.assertEqual(kind, instance.kind.get())
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
        kind = self.interface.get_kind('kind', 1, add=True)
        instance = self.interface.add_instance(kind)
        time1 = self.interface.add_time(TimeStamp(1))
        time2 = self.interface.add_time(TimeStamp(2))
        observation1 = self.interface.add_observation(instance, time1)
        observation2 = self.interface.add_observation(instance, time2)
        self.assertNotEqual(observation1, observation2)
        self.assertEqual(observation1.instance.get(), instance)
        self.assertEqual(observation2.instance.get(), instance)
        self.assertIn(observation1, instance.observations)
        self.assertIn(observation2, instance.observations)
        self.assertIn(observation1, time1.observations)
        self.assertIn(observation2, time2.observations)

    @abstractmethod
    def test_get_hook(self):
        hook1 = self.interface.get_hook(fake_hook1)
        self.assertIsInstance(hook1, Hook)
        self.assertEqual(hook1, self.interface.get_hook(fake_hook1))
        self.assertNotEqual(hook1, self.interface.get_hook(fake_hook2))
        with self.assertRaises(ValueError):
            self.interface.get_hook(lambda: None)

        def fake_local_hook():
            pass

        with self.assertRaises(ValueError):
            self.interface.get_hook(fake_local_hook)

    @abstractmethod
    def test_core_dump(self):
        self.interface.now()
        self.interface.now()
        with patch('logging.Logger.log') as log_method:
            self.interface.core_dump(log_level=logging.CRITICAL)
            log_method.assert_called()
