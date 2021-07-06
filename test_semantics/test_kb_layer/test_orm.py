from unittest import TestCase

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Word, Kind, Instance, Observation


class TestWord(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_has_spelling(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertFalse(word.has_spelling())
        vertex.name = 'vertex'
        self.assertTrue(word.has_spelling())

    def test_spelling(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        word = Word(vertex, self.kb.database)
        self.assertIsNone(word.spelling)
        vertex.name = 'vertex'
        self.assertEqual(word.spelling, 'vertex')

    def test_kinds(self):
        kind1 = self.kb.add_kind('word')
        kind2 = self.kb.add_kind('word')
        kind3 = self.kb.add_kind('a different word')
        word = self.kb.get_word('word')
        self.assertIn(kind1, word.kinds)
        self.assertIn(kind2, word.kinds)
        self.assertNotIn(kind3, word.kinds)
        self.assertEqual(2, len(word.kinds))


class TestKind(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_has_name(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        kind = Kind(vertex, self.kb.database)
        self.assertFalse(kind.has_name())
        kind.name.set(self.kb.get_word('word', add=True))
        self.assertTrue(kind.has_name())

    def test_name(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        kind = Kind(vertex, self.kb.database)
        self.assertIsNone(kind.name.get())
        name1 = self.kb.get_word('name1', add=True)
        kind.name.set(name1)
        self.assertEqual(kind.name.get(), name1)
        name2 = self.kb.get_word('name2', add=True)
        kind.name.set(name2)
        self.assertEqual(kind.name.get(), name2)
        kind.name.set(name1)
        self.assertEqual(kind.name.get(), name1)
        kind.name.set(name2)
        self.assertEqual(kind.name.get(), name2)
        name3 = self.kb.get_word('name3', add=True)
        kind.name.set(name3)
        self.assertEqual(kind.name.get(), name3)

    def test_names(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        kind = Kind(vertex, self.kb.database)
        self.assertEqual([], list(kind.names))
        name1 = self.kb.get_word('name1', add=True)
        kind.names.add(name1)
        self.assertEqual([name1], list(kind.names))
        name2 = self.kb.get_word('name2', add=True)
        kind.names.add(name2)
        kind.names.add(name2)
        self.assertEqual([name2, name1], kind.names.descending())
        kind.names.add(name1)
        self.assertEqual([name1, name2], kind.names.descending())
        kind.names.add(name2)
        self.assertEqual([name2, name1], kind.names.descending())
        name3 = self.kb.get_word('name3', add=True)
        kind.names.add(name3)
        self.assertEqual([name2, name1, name3], kind.names.descending())

    def test_instances(self):
        kind = self.kb.add_kind('kind')
        self.assertEqual([], list(kind.instances))
        instance1 = self.kb.add_instance(kind)
        self.assertEqual([instance1], list(kind.instances))
        instance2 = self.kb.add_instance(kind)
        self.assertEqual({instance1, instance2}, set(kind.instances))
        kind.instances.remove(instance1)
        # Doing it just once doesn't remove it, because we have a preference threshold of 0.5 and
        # preference of 0.5. One positive evidence sample perfectly balances one negative evidence
        # sample.
        self.assertEqual([instance2, instance1], kind.instances.descending())
        kind.instances.remove(instance1)
        # However, doing it twice drops the preference below the threshold, and the instance no
        # longer shows up when validation is used.
        self.assertEqual([instance2], list(kind.instances))


class TestInstance(TestCase):
    """An instance is a particular thing."""

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_has_kind(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        instance = Instance(vertex, self.kb.database)
        self.assertFalse(instance.has_kind())
        instance.kind.set(self.kb.add_kind('kind'))
        self.assertTrue(instance.has_kind())

    def test_name(self):
        kind = self.kb.add_kind('kind name')
        instance = self.kb.add_instance(kind)
        self.assertIsNone(instance.name.get())
        instance_name = self.kb.get_word('instance name', add=True)
        instance.name.set(instance_name)
        self.assertEqual(instance_name, instance.name.get())

    def test_names(self):
        kind = self.kb.add_kind('kind name')
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
        kind = self.kb.add_kind('kind')
        instance.kind.set(kind)
        self.assertEqual(kind, instance.kind.get())

    def test_kinds(self):
        kind1 = self.kb.add_kind('kind1')
        instance = self.kb.add_instance(kind1)
        self.assertEqual([kind1], list(instance.kinds))
        instance.kinds.clear()  # Adds negative evidence, but does not remove it outright.
        kind2 = self.kb.add_kind('kind2')
        instance.kinds.add(kind2)
        self.assertEqual([kind2, kind1], instance.kinds.descending())
        kind3 = self.kb.add_kind('kind3')
        instance.kinds.add(kind3)
        instance.kinds.add(kind3)
        self.assertEqual([kind3, kind2, kind1], instance.kinds.descending())
        instance.kinds.add(kind2)
        self.assertEqual([kind2, kind3, kind1], instance.kinds.descending())
        instance.kinds.add(kind3)
        self.assertEqual([kind3, kind2, kind1], instance.kinds.descending())
        kind4 = self.kb.add_kind('kind4')
        instance.kinds.add(kind4)
        self.assertEqual([kind3, kind2, kind4, kind1], instance.kinds.descending())

    def test_observations(self):
        kind = self.kb.add_kind('kind')
        instance = self.kb.add_instance(kind)
        self.assertEqual([], list(instance.observations))
        observation1 = self.kb.add_observation(instance)
        self.assertEqual([observation1], list(instance.observations))
        observation2 = self.kb.add_observation(instance)
        self.assertEqual({observation1, observation2}, set(instance.observations))


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


class TestObservation(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_has_time(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        observation = Observation(vertex, self.kb.database)
        self.assertFalse(observation.has_time())
        observation.time.set(self.kb.add_time())
        self.assertTrue(observation.has_time())

    def test_has_instance(self):
        role = self.kb.database.get_role('role', add=True)
        vertex = self.kb.database.add_vertex(role)
        observation = Observation(vertex, self.kb.database)
        self.assertFalse(observation.has_instance())
        kind = self.kb.add_kind('kind')
        observation.instance.set(self.kb.add_instance(kind))
        self.assertTrue(observation.has_instance())

    def test_time(self):
        kind = self.kb.add_kind('kind')
        instance = self.kb.add_instance(kind)
        time = self.kb.add_time()
        observation = self.kb.add_observation(instance, time)
        self.assertEqual(time, observation.time.get())

    def test_times(self):
        kind = self.kb.add_kind('kind')
        instance = self.kb.add_instance(kind)
        time1 = self.kb.add_time()
        observation = self.kb.add_observation(instance, time1)
        self.assertEqual([time1], list(observation.times))
        time2 = self.kb.add_time()
        observation.times.add(time2)
        self.assertEqual({time1, time2}, set(observation.times))

    def test_instance(self):
        kind = self.kb.add_kind('kind')
        instance = self.kb.add_instance(kind)
        observation = self.kb.add_observation(instance)
        self.assertEqual(instance, observation.instance.get())

    def test_instances(self):
        kind = self.kb.add_kind('kind')
        instance1 = self.kb.add_instance(kind)
        observation = self.kb.add_observation(instance1)
        self.assertEqual([instance1], list(observation.instances))
        instance2 = self.kb.add_instance(kind)
        observation.instances.add(instance2)
        self.assertEqual({instance1, instance2}, set(observation.instances))
