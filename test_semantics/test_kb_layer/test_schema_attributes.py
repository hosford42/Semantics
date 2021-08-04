from unittest import TestCase
from unittest.mock import MagicMock, patch

from semantics.graph_layer.graph_db import GraphDB
from semantics.kb_layer import evidence
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Word
from semantics.kb_layer.schema import Schema
from semantics.kb_layer.schema_attributes import default_attribute_preference, attribute, \
    SingularAttributeDescriptor, PluralAttributeDescriptor, AttributeDescriptor, \
    SingularAttribute, PluralAttribute


class TestFunctions(TestCase):

    def test_default_attribute_preference(self):
        db = GraphDB()
        label = db.get_label('label', add=True)
        role = db.get_role('role', add=True)
        source = db.add_vertex(role)
        sink = db.add_vertex(role)
        edge = db.add_edge(label, source, sink)

        previous_value = default_attribute_preference(edge, sink)
        evidence.apply_evidence(edge, 1.0)
        current_value = default_attribute_preference(edge, sink)
        self.assertGreater(current_value, previous_value)

        previous_value = current_value
        evidence.apply_evidence(sink, 1.0)
        current_value = default_attribute_preference(edge, sink)
        self.assertGreater(current_value, previous_value)

        previous_value = current_value
        evidence.apply_evidence(edge, 0.0)
        current_value = default_attribute_preference(edge, sink)
        self.assertLess(current_value, previous_value)

        previous_value = current_value
        evidence.apply_evidence(sink, 0.0)
        current_value = default_attribute_preference(edge, sink)
        self.assertLess(current_value, previous_value)

    def test_attribute(self):
        a1 = attribute('edge', Word)
        self.assertIsInstance(a1, SingularAttributeDescriptor)
        a2 = attribute('edge', Word, plural=True)
        self.assertIsInstance(a2, PluralAttributeDescriptor)


class TestAttributeDescriptor(TestCase):

    def test_property_descriptor_protocol(self):
        class MySchema(Schema):
            a = AttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        s = MySchema(vertex, kb.database)
        with self.assertRaises(AttributeError):
            s.a = 1
        with self.assertRaises(AttributeError):
            del s.a

    def test_error_on_comparison(self):
        descriptor = AttributeDescriptor('edge', Word)
        with self.assertRaises(TypeError):
            # noinspection PyStatementEffect
            descriptor == 'anything'
        with self.assertRaises(TypeError):
            # noinspection PyStatementEffect
            descriptor != 'anything'

    def test_preference(self):
        d = AttributeDescriptor('edge', Word)

        self.assertIs(default_attribute_preference, d.get_preference_function())

        @d.preference
        def pref(_edge, _vertex):
            return 0

        self.assertIs(pref, d.get_preference_function())

        @d.preference
        def pref2(_edge, _vertex):
            return 1

        self.assertIs(pref2, d.get_preference_function())

    def test_validation(self):
        d = AttributeDescriptor('edge', Word)

        self.assertIsNone(d.get_validation_function())

        @d.validation
        def val(_edge, _vertex):
            return 0

        self.assertIs(val, d.get_validation_function())

        @d.validation
        def val2(_edge, _vertex):
            return 1

        self.assertIs(val2, d.get_validation_function())

    def test_iter_choices(self):
        d = AttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        db = kb.database
        role = db.get_role('role', add=True)
        vertex1 = db.add_vertex(role)
        vertex2 = db.add_vertex(role)
        vertex3 = kb.get_word('word', add=True).vertex
        label = db.get_label('edge', add=True)
        instance = Schema(vertex1, db)

        self.assertEqual([], list(d.iter_choices(instance)))

        edge1 = vertex1.add_edge_to(label, vertex2)
        self.assertEqual([], list(d.iter_choices(instance, validate=True)))
        self.assertEqual([(edge1, vertex2, None)],
                         list(d.iter_choices(instance, validate=False, preferences=False)))
        self.assertEqual([(edge1, vertex2, default_attribute_preference(edge1, vertex2))],
                         list(d.iter_choices(instance, validate=False, preferences=True)))

        edge2 = vertex1.add_edge_to(label, vertex3)
        self.assertEqual([(edge2, vertex3, None)],
                         list(d.iter_choices(instance, validate=True, preferences=False)))
        self.assertEqual([(edge2, vertex3, default_attribute_preference(edge2, vertex3))],
                         list(d.iter_choices(instance, validate=True, preferences=True)))
        self.assertEqual({(edge1, vertex2, None), (edge2, vertex3, None)},
                         set(d.iter_choices(instance, validate=False, preferences=False)))
        self.assertEqual({(edge1, vertex2, default_attribute_preference(edge1, vertex2)),
                          (edge2, vertex3, default_attribute_preference(edge2, vertex3))},
                         set(d.iter_choices(instance, validate=False, preferences=True)))

    def test_best_choice(self):
        d = AttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        db = kb.database
        role = db.get_role('role', add=True)
        vertex1 = db.add_vertex(role)
        vertex2 = db.add_vertex(role)
        vertex3 = kb.get_word('word', add=True).vertex
        label = db.get_label('edge', add=True)
        instance = Schema(vertex1, db)

        self.assertIsNone(d.best_choice(instance))

        edge1 = vertex1.add_edge_to(label, vertex2)
        self.assertIsNone(d.best_choice(instance, validate=True))
        self.assertEqual((edge1, vertex2, default_attribute_preference(edge1, vertex2)),
                         d.best_choice(instance, validate=False))

        edge2 = vertex1.add_edge_to(label, vertex3)
        evidence.apply_evidence(edge1, 1)
        evidence.apply_evidence(edge2, 0.9)
        self.assertEqual((edge2, vertex3, default_attribute_preference(edge2, vertex3)),
                         d.best_choice(instance, validate=True))
        self.assertEqual((edge1, vertex2, default_attribute_preference(edge1, vertex2)),
                         d.best_choice(instance, validate=False))

    def test_sorted_choices(self):
        d = AttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        db = kb.database
        role = db.get_role('role', add=True)
        vertex1 = db.add_vertex(role)
        vertex2 = db.add_vertex(role)
        vertex3 = kb.get_word('word', add=True).vertex
        label = db.get_label('edge', add=True)
        instance = Schema(vertex1, db)

        self.assertEqual([], d.sorted_choices(instance))

        edge1 = vertex1.add_edge_to(label, vertex2)
        self.assertEqual([], d.sorted_choices(instance, validate=True))
        self.assertEqual([(edge1, vertex2, default_attribute_preference(edge1, vertex2))],
                         d.sorted_choices(instance, validate=False))

        edge2 = vertex1.add_edge_to(label, vertex3)
        evidence.apply_evidence(edge1, 1)
        evidence.apply_evidence(edge2, 0.9)
        self.assertEqual([(edge2, vertex3, default_attribute_preference(edge2, vertex3))],
                         d.sorted_choices(instance, validate=True))
        self.assertEqual([(edge1, vertex2, default_attribute_preference(edge1, vertex2)),
                          (edge2, vertex3, default_attribute_preference(edge2, vertex3))],
                         d.sorted_choices(instance, validate=False))

    def test_clear(self):
        d = AttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        db = kb.database
        role = db.get_role('role', add=True)
        vertex1 = db.add_vertex(role)
        vertex2 = kb.get_word('word', add=True).vertex
        label = db.get_label('edge', add=True)
        edge = vertex1.add_edge_to(label, vertex2)
        instance = Schema(vertex1, db)

        with patch('semantics.kb_layer.evidence.apply_evidence', return_value=None):
            d.clear(instance)
            # noinspection PyUnresolvedReferences
            evidence.apply_evidence.assert_called_with(edge, 0)


class TestSingularAttribute(TestCase):

    def setUp(self) -> None:
        self.obj = MagicMock()
        self.descriptor = MagicMock()
        self.attribute = SingularAttribute(self.obj, self.descriptor)

    def test_error_on_comparison(self):
        with self.assertRaises(TypeError):
            # noinspection PyStatementEffect
            self.attribute == self.obj
        with self.assertRaises(TypeError):
            # noinspection PyStatementEffect
            self.attribute != self.obj

    def test_defined(self):
        self.descriptor.defined.return_value = True
        self.assertTrue(self.attribute.defined)
        self.descriptor.defined.assert_called_with(self.obj)

    def test_set(self):
        value = MagicMock(spec=Schema)
        self.attribute.set(value)
        self.descriptor.set_value.assert_called_with(self.obj, value)

    def test_get(self):
        value = MagicMock()
        self.descriptor.get_value.return_value = value
        self.assertIs(value, self.attribute.get())
        self.descriptor.get_value.assert_called_with(self.obj, validate=True)

    def test_clear(self):
        self.attribute.clear()
        self.descriptor.clear.assert_called_with(self.obj)


class TestSingularAttributeDescriptor(TestCase):

    def test_property_descriptor_protocol(self):
        class MySchema(Schema):
            a = SingularAttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        s = MySchema(vertex, kb.database)
        self.assertIsInstance(s.a, SingularAttribute)

    def test_defined(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        s = Schema(vertex, kb.database)
        a = SingularAttributeDescriptor('edge', Word)
        self.assertFalse(a.defined(s))
        vertex2 = kb.get_word('word', add=True).vertex
        label = kb.database.get_label('edge', add=True)
        vertex.add_edge_to(label, vertex2)
        self.assertTrue(a.defined(s))

    def test_get_value(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        s = Schema(vertex, kb.database)
        a = SingularAttributeDescriptor('edge', Word)
        self.assertIsNone(a.get_value(s))
        vertex2 = kb.get_word('word', add=True).vertex
        label = kb.database.get_label('edge', add=True)
        vertex.add_edge_to(label, vertex2)
        self.assertEqual(Word(vertex2, kb.database), a.get_value(s))

    def test_set_value(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        word = kb.get_word('word', add=True)
        label = kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = SingularAttributeDescriptor('edge', Word)
        a.set_value(s, word)
        self.assertIn(label, [edge.label for edge in vertex.iter_outbound()])
        self.assertIn(word.vertex, [edge.sink for edge in vertex.iter_outbound()])
        self.assertEqual(1, vertex.count_outbound())


class TestPluralAttribute(TestCase):

    def setUp(self) -> None:
        self.obj = MagicMock()
        self.descriptor = MagicMock()
        self.attribute = PluralAttribute(self.obj, self.descriptor)

    def test_error_on_comparison(self):
        with self.assertRaises(TypeError):
            # noinspection PyStatementEffect
            self.attribute == self.obj
        with self.assertRaises(TypeError):
            # noinspection PyStatementEffect
            self.attribute != self.obj

    def test_len(self):
        self.descriptor.count.return_value = 111
        self.assertEqual(111, len(self.attribute))
        self.descriptor.count.assert_called_with(self.obj)

    def test_iter(self):
        iterator = MagicMock()
        self.descriptor.iter_values.return_value = iterator
        self.assertIs(iterator, iter(self.attribute))
        self.descriptor.iter_values.assert_called_with(self.obj)

    def test_contains(self):
        value = MagicMock()
        self.descriptor.contains.return_value = False
        self.assertFalse(value in self.attribute)
        self.descriptor.contains.assert_called_with(self.obj, value)

    def test_ascending(self):
        result = MagicMock()
        self.descriptor.sorted_values.return_value = result
        self.assertIs(result, self.attribute.ascending())
        self.descriptor.sorted_values.assert_called_with(self.obj, reverse=False)

    def test_descending(self):
        result = MagicMock()
        self.descriptor.sorted_values.return_value = result
        self.assertIs(result, self.attribute.descending())
        self.descriptor.sorted_values.assert_called_with(self.obj, reverse=True)

    def test_add(self):
        value = MagicMock()
        self.attribute.add(value)
        self.descriptor.add.assert_called_with(self.obj, value)

    def test_remove(self):
        value = MagicMock()
        self.attribute.remove(value)
        self.descriptor.remove.assert_called_with(self.obj, value)

    def test_discard(self):
        value = MagicMock()
        self.attribute.discard(value)
        self.descriptor.discard.assert_called_with(self.obj, value)

    def test_clear(self):
        self.attribute.clear()
        self.descriptor.clear.assert_called_with(self.obj)

    def test_evidence_map(self):
        result = MagicMock()
        validate = MagicMock()
        self.descriptor.evidence_map.return_value = result
        self.assertIs(result, self.attribute.evidence_map(validate=validate))
        self.descriptor.evidence_map.assert_called_with(self.obj, validate=validate)


class TestPluralAttributeDescriptor(TestCase):

    def test_property_descriptor_protocol(self):
        class MySchema(Schema):
            a = PluralAttributeDescriptor('edge', Word)

        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        s = MySchema(vertex, kb.database)
        self.assertIsInstance(s.a, PluralAttribute)

    def test_count(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        label = kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        self.assertEqual(0, a.count(s))
        non_word = kb.database.add_vertex(role)
        vertex.add_edge_to(label, non_word)
        self.assertEqual(0, a.count(s))
        word = kb.get_word('word', add=True)
        vertex.add_edge_to(label, word.vertex)
        self.assertEqual(1, a.count(s))

    def test_iter_values(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        label = kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        self.assertEqual([], list(a.iter_values(s)))
        non_word = kb.database.add_vertex(role)
        vertex.add_edge_to(label, non_word)
        self.assertEqual([], list(a.iter_values(s)))
        word = kb.get_word('word', add=True)
        vertex.add_edge_to(label, word.vertex)
        self.assertEqual([word], list(a.iter_values(s)))

    def test_sorted_values(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        label = kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        self.assertEqual([], a.sorted_values(s))
        non_word = kb.database.add_vertex(role)
        edge1 = vertex.add_edge_to(label, non_word)
        self.assertEqual([], a.sorted_values(s))
        word = kb.get_word('word', add=True)
        vertex.add_edge_to(label, word.vertex)
        self.assertEqual([word], a.sorted_values(s))
        word2 = kb.get_word('word2', add=True)
        edge2 = vertex.add_edge_to(label, word2.vertex)
        evidence.apply_evidence(edge1, 0.9)
        evidence.apply_evidence(edge2, 1)
        self.assertEqual([word, word2], a.sorted_values(s))
        self.assertEqual([word2, word], a.sorted_values(s, reverse=True))

    def test_add(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        word = kb.get_word('word', add=True)
        a.add(s, word)
        self.assertIn(word, a.iter_values(s))
        edge = list(vertex.iter_outbound())[0]
        previous_evidence = evidence.get_evidence(edge)
        a.add(s, word)
        self.assertIn(word, a.iter_values(s))
        current_evidence = evidence.get_evidence(edge)
        self.assertGreater(current_evidence.mean, previous_evidence.mean)
        self.assertGreater(current_evidence.samples, previous_evidence.samples)

    def test_remove(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        word = kb.get_word('word', add=True)
        with self.assertRaises(KeyError):
            a.remove(s, word)
        a.add(s, word)
        edge = list(vertex.iter_outbound())[0]
        current_evidence = evidence.get_evidence(edge)
        self.assertGreater(current_evidence.mean, evidence.INITIAL_MEAN)
        self.assertGreater(current_evidence.samples, evidence.INITIAL_SAMPLES)
        previous_evidence = current_evidence
        a.remove(s, word)
        self.assertIn(word, a.iter_values(s))  # Yes, it should still be there.
        current_evidence = evidence.get_evidence(edge)
        self.assertLess(current_evidence.mean, previous_evidence.mean)
        self.assertGreater(current_evidence.samples, previous_evidence.samples)

    def test_discard(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        word = kb.get_word('word', add=True)
        self.assertNotIn(word, a.iter_values(s))
        a.discard(s, word)
        self.assertIn(word, a.iter_values(s))  # Yes, it should actually be there now.
        edge = list(vertex.iter_outbound())[0]
        current_evidence = evidence.get_evidence(edge)
        self.assertLess(current_evidence.mean, evidence.INITIAL_MEAN)
        self.assertGreater(current_evidence.samples, evidence.INITIAL_SAMPLES)
        previous_evidence = current_evidence
        a.discard(s, word)
        self.assertIn(word, a.iter_values(s))  # Yes, it should still be there.
        current_evidence = evidence.get_evidence(edge)
        self.assertLess(current_evidence.mean, previous_evidence.mean)
        self.assertGreater(current_evidence.samples, previous_evidence.samples)

    def test_contains(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        word = kb.get_word('word', add=True)
        self.assertFalse(a.contains(s, word))
        a.add(s, word)
        self.assertTrue(a.contains(s, word))

    def test_evidence_map(self):
        kb = KnowledgeBase()
        role = kb.database.get_role('role', add=True)
        vertex = kb.database.add_vertex(role)
        label = kb.database.get_label('edge', add=True)
        s = Schema(vertex, kb.database)
        a = PluralAttributeDescriptor('edge', Word)
        self.assertEqual({}, a.evidence_map(s))
        non_word = kb.database.add_vertex(role)
        vertex.add_edge_to(label, non_word)
        self.assertEqual({}, a.evidence_map(s, validate=True))
        self.assertEqual({Word(non_word, kb.database)}, a.evidence_map(s, validate=False).keys())
        word = kb.get_word('word', add=True)
        a.add(s, word)
        self.assertEqual({word}, a.evidence_map(s, validate=True).keys())
        self.assertEqual({word, Word(non_word, kb.database)},
                         a.evidence_map(s, validate=False).keys())
