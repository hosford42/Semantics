from unittest import TestCase

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.knowledge_base import KnowledgeBase


class TestTime(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_time_stamp(self):
        time1 = self.kb.add_time()
        self.assertIsNone(time1.time_stamp)
        time2 = self.kb.add_time(TimeStamp(1.0))
        self.assertEqual(TimeStamp(1.0), time2.time_stamp)

    def test_observations(self):
        time = self.kb.add_time()
        self.assertEqual([], list(time.observations))
        kind = self.kb.add_kind('kind')
        instance = self.kb.add_instance(kind)
        observation1 = self.kb.add_observation(instance, time)
        self.assertEqual([observation1], list(time.observations))
        observation2 = self.kb.add_observation(instance, time)
        self.assertEqual({observation1, observation2}, set(time.observations))
