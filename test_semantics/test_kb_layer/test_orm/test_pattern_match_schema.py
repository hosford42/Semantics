from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import PatternMatch, Pattern, Instance, Time
from semantics.kb_layer.schema import Schema


class TestPatternMatch(TestCase):

    pass


class TestIsIsomorphic(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def add_pattern_match(self, preimage: Pattern, image: Schema = None) -> PatternMatch:
        match_role = self.kb.database.get_role(PatternMatch.role_name(), add=True)
        vertex = self.kb.database.add_vertex(match_role)
        match = PatternMatch(vertex, self.kb.database)
        match.preimage.set(preimage)
        if image:
            match.image.set(image)
        return match

    def test_without_image(self):
        match = self.add_pattern_match(self.kb.add_pattern())
        self.assertFalse(match.is_isomorphic())

    def test_with_image(self):
        match = self.add_pattern_match(self.kb.add_pattern(Time))
        match.image.set(self.kb.add_time())
        self.assertTrue(match.is_isomorphic())

    def test_with_image_of_different_schema(self):
        match = self.add_pattern_match(self.kb.add_pattern(Instance))
        match.image.set(self.kb.add_time())
        self.assertFalse(match.is_isomorphic())

    def test_with_matching_edge_to_child(self):
        parent_pattern = self.kb.add_pattern(Time)
        child_pattern = self.kb.add_pattern(Time)
        parent_pattern.children.add(child_pattern)
        parent_pattern.match.earlier_times.add(child_pattern.match)

        parent_match = self.add_pattern_match(parent_pattern)
        child_match = self.add_pattern_match(child_pattern)
        parent_match.children.add(child_match)

        parent_image = self.kb.add_time()
        child_image = self.kb.add_time()
        parent_image.earlier_times.add(child_image)

        parent_match.image.set(parent_image)
        child_match.image.set(child_image)

        self.assertTrue(parent_match.is_isomorphic())

    def test_without_matching_edge_to_child(self):
        parent_pattern = self.kb.add_pattern(Time)
        child_pattern = self.kb.add_pattern(Time)
        parent_pattern.children.add(child_pattern)
        parent_pattern.match.earlier_times.add(child_pattern.match)

        parent_match = self.add_pattern_match(parent_pattern)
        child_match = self.add_pattern_match(child_pattern)
        parent_match.children.add(child_match)

        parent_image = self.kb.add_time()
        child_image = self.kb.add_time()

        parent_match.image.set(parent_image)
        child_match.image.set(child_image)

        self.assertFalse(parent_match.is_isomorphic())

    def test_non_isomorphic_child(self):
        parent_pattern = self.kb.add_pattern(Time)
        child_pattern = self.kb.add_pattern(Time)
        parent_pattern.children.add(child_pattern)
        parent_pattern.match.earlier_times.add(child_pattern.match)

        parent_match = self.add_pattern_match(parent_pattern)
        child_match = self.add_pattern_match(child_pattern)
        parent_match.children.add(child_match)

        parent_image = self.kb.add_time()
        parent_match.image.set(parent_image)

        self.assertFalse(parent_match.is_isomorphic())

    def test_with_matching_implicit_transitive_edge_to_child(self):
        parent_pattern = self.kb.add_pattern(Time)
        child_pattern = self.kb.add_pattern(Time)
        parent_pattern.children.add(child_pattern)
        parent_pattern.match.later_times.add(child_pattern.match)

        parent_match = self.add_pattern_match(parent_pattern)
        child_match = self.add_pattern_match(child_pattern)
        parent_match.children.add(child_match)

        parent_image = self.kb.add_time()
        child_image = self.kb.add_time()
        intermediary = self.kb.add_time()
        parent_image.later_times.add(intermediary)
        intermediary.later_times.add(child_image)

        parent_match.image.set(parent_image)
        child_match.image.set(child_image)

        self.assertTrue(parent_match.is_isomorphic())
