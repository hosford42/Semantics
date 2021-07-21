from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Instance


class TestInstance(TestCase):
    """An instance is a particular thing."""

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_name(self):
        kind = self.kb.get_kind('kind name', 1, add=True)
        instance = self.kb.add_instance(kind)
        self.assertIsNone(instance.name.get())
        instance_name = self.kb.get_word('instance name', add=True)
        instance.name.set(instance_name)
        self.assertEqual(instance_name, instance.name.get())

    def test_names(self):
        kind = self.kb.get_kind('kind name', 1, add=True)
        instance = self.kb.add_instance(kind)
        self.assertEqual([], list(instance.names))
        name1 = self.kb.get_word('name1', add=True)
        instance.names.add(name1)
        self.assertEqual([name1], list(instance.names))
        name2 = self.kb.get_word('name2', add=True)
        instance.names.add(name2)
        instance.names.add(name2)
        self.assertEqual([name2, name1], instance.names.descending())
        instance.names.add(name1)
        self.assertEqual([name1, name2], instance.names.descending())
        instance.names.add(name2)
        self.assertEqual([name2, name1], instance.names.descending())
        name3 = self.kb.get_word('name3', add=True)
        instance.names.add(name3)
        self.assertEqual([name2, name1, name3], instance.names.descending())

    def test_kind(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        instance = Instance(vertex, self.kb.database)
        self.assertIsNone(instance.kind.get())
        kind = self.kb.get_kind('kind', 1, add=True)
        instance.kind.set(kind)
        self.assertEqual(kind, instance.kind.get())

    def test_kinds(self):
        kind1 = self.kb.get_kind('kind1', 1, add=True)
        instance = self.kb.add_instance(kind1)
        self.assertEqual([kind1], list(instance.kinds))
        instance.kinds.clear()  # Adds negative evidence, but does not remove it outright.
        kind2 = self.kb.get_kind('kind2', 1, add=True)
        instance.kinds.add(kind2)
        self.assertEqual([kind2, kind1], instance.kinds.descending())
        kind3 = self.kb.get_kind('kind3', 1, add=True)
        instance.kinds.add(kind3)
        instance.kinds.add(kind3)
        self.assertEqual([kind3, kind2, kind1], instance.kinds.descending())
        instance.kinds.add(kind2)
        self.assertEqual([kind2, kind3, kind1], instance.kinds.descending())
        instance.kinds.add(kind3)
        self.assertEqual([kind3, kind2, kind1], instance.kinds.descending())
        kind4 = self.kb.get_kind('kind4', 1, add=True)
        instance.kinds.add(kind4)
        self.assertEqual([kind3, kind2, kind4, kind1], instance.kinds.descending())

    def test_observations(self):
        kind = self.kb.get_kind('kind', 1, add=True)
        instance = self.kb.add_instance(kind)
        self.assertEqual([], list(instance.observations))
        observation1 = self.kb.add_observation(instance)
        self.assertEqual([observation1], list(instance.observations))
        observation2 = self.kb.add_observation(instance)
        self.assertEqual({observation1, observation2}, set(instance.observations))

    def test_time(self):
        kind = self.kb.get_kind('kind', 1, add=True)
        instance = self.kb.add_instance(kind)
        time = self.kb.add_time()
        observation = self.kb.add_observation(instance, time)
        self.assertEqual(time, observation.time.get())

    def test_times(self):
        kind = self.kb.get_kind('kind', 1, add=True)
        instance = self.kb.add_instance(kind)
        time1 = self.kb.add_time()
        observation = self.kb.add_observation(instance, time1)
        self.assertEqual([time1], list(observation.times))
        time2 = self.kb.add_time()
        observation.times.add(time2)
        self.assertEqual({time1, time2}, set(observation.times))

    def test_instance(self):
        kind = self.kb.get_kind('kind', 1, add=True)
        instance = self.kb.add_instance(kind)
        observation = self.kb.add_observation(instance)
        self.assertEqual(instance, observation.instance.get())

    def test_instances(self):
        kind = self.kb.get_kind('kind', 1, add=True)
        instance1 = self.kb.add_instance(kind)
        observation = self.kb.add_observation(instance1)
        self.assertEqual([instance1], list(observation.instances))
        instance2 = self.kb.add_instance(kind)
        observation.instances.add(instance2)
        self.assertEqual({instance1, instance2}, set(observation.instances))
