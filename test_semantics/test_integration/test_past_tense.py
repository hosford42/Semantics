import unittest

import logging
logging.root.setLevel(logging.DEBUG)

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance


class TestPastTense(unittest.TestCase):

    def setUp(self) -> None:
        kb = KnowledgeBase()

        # Define "-ed".
        # NOTES:
        #   * kb.context.now is a built-in pattern that *contextually* matches the current time when
        #     the call to kb.update() or kb.query() is made. This is in contrast to kb.now(), which
        #     returns the *literal* current time.
        #   * During matching, the 'PRECEDES' relation for time patterns does not have to directly
        #     match two times connected by an edge of that type. It will also match two times for
        #     which the time stamps are in the correct order. This is for efficiency's sake, so we
        #     don't have to add an edge connecting every pair of times with time stamps.
        pattern_before_now = kb.add_pattern(Time)
        pattern_before_now.children.add(kb.context.now)
        pattern_before_now.match.later_times.add(kb.context.now.match)
        selector_ed_suffix_template = kb.get_selector_pattern('-ed', add=True)
        selector_ed_suffix_template.match.time.set(pattern_before_now.match)
        selector_ed_suffix_template.children.add(pattern_before_now)
        selector_ed_suffix = selector_ed_suffix_template.templated_clone()

        self.kb = kb
        self.pattern_before_now = pattern_before_now
        self.pattern_before_now_clone = pattern_before_now.templated_clone()
        self.selector_ed_suffix_template = selector_ed_suffix_template
        self.selector_ed_suffix = selector_ed_suffix

    def test_before_now(self):
        """Create an empty knowledge base. Add an unstamped time that precedes the current time to
        the contents of the knowledge base by updating it with a pattern. Verify that the structure
        was added by querying the knowledge base afterward with the same pattern."""

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        # NOTES:
        #   * A match object is an immutable mapping from pattern components to graph elements.
        #   * Applying a match tells the knowledge base to update the graph to incorporate the
        #     structure of the pattern into the graph using the given elements, making the matched
        #     subgraph isomorphic to the pattern, and then apply positive evidence to the subgraph.
        #   * Unconditionally applying the first match and then breaking has the effect of taking
        #     whatever match the knowledge base deems most probable based on previous evidence
        #     (which is none, in this case).
        now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.pattern_before_now, partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.kb.context.now:
                    self.assertIsNone(now_key)
                    now_key = key
                else:
                    assert key and isinstance(key.match, Time)
                    self.assertIsNone(before_key)
                    before_key = key
            self.assertEqual(2, len(mapping))

            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertIn(now_value, before_value.later_times)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value.precedes(current_time))
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value.precedes(now_value))
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, and that the
        # observations have the expected structural relationships.
        # NOTES:
        #   * In partial matching, the matched subgraph may only be *approximately* isomorphic to
        #     the pattern being matched. The is_isomorphic() method of the match will tell you
        #     whether the match is exact or merely approximate.
        #   * For queries, as opposed to updates, we use match.accept() instead of match.apply() to
        #     apply positive evidence to the match without modifying the graph's structure.
        match_count = 0
        for match in self.kb.match(self.pattern_before_now, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            print("Matched:")
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertTrue(matched_before.precedes(matched_now))

        self.assertGreaterEqual(match_count, 1)

    def test_before_now_clone(self):
        """Create an empty knowledge base. Add an unstamped time that precedes the current time to
        the contents of the knowledge base by updating it with a pattern. Verify that the structure
        was added by querying the knowledge base afterward with the same pattern."""

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        # NOTES:
        #   * A match object is an immutable mapping from pattern components to graph elements.
        #   * Applying a match tells the knowledge base to update the graph to incorporate the
        #     structure of the pattern into the graph using the given elements, making the matched
        #     subgraph isomorphic to the pattern, and then apply positive evidence to the subgraph.
        #   * Unconditionally applying the first match and then breaking has the effect of taking
        #     whatever match the knowledge base deems most probable based on previous evidence
        #     (which is none, in this case).
        now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.pattern_before_now_clone, partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            mapping = match.get_mapping()
            for key in mapping:
                if key.template.get() == self.kb.context.now:
                    self.assertIsNone(now_key)
                    now_key = key
                else:
                    assert key and isinstance(key.match, Time)
                    self.assertIsNone(before_key)
                    before_key = key
            self.assertEqual(2, len(mapping))

            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertIn(now_value, before_value.later_times)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value.precedes(current_time))
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value.precedes(now_value))
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, and that the
        # observations have the expected structural relationships.
        # NOTES:
        #   * In partial matching, the matched subgraph may only be *approximately* isomorphic to
        #     the pattern being matched. The is_isomorphic() method of the match will tell you
        #     whether the match is exact or merely approximate.
        #   * For queries, as opposed to updates, we use match.accept() instead of match.apply() to
        #     apply positive evidence to the match without modifying the graph's structure.
        match_count = 0
        for match in self.kb.match(self.pattern_before_now_clone, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            print("Matched:")
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertTrue(matched_before.precedes(matched_now))

        self.assertGreaterEqual(match_count, 1)

    def test_past_tense_template(self):
        """Create an empty knowledge base. Add an unstamped time that precedes the current time to
        the contents of the knowledge base by updating it with a pattern. Verify that the structure
        was added by querying the knowledge base afterward with the same pattern."""

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        # NOTES:
        #   * A match object is an immutable mapping from pattern components to graph elements.
        #   * Applying a match tells the knowledge base to update the graph to incorporate the
        #     structure of the pattern into the graph using the given elements, making the matched
        #     subgraph isomorphic to the pattern, and then apply positive evidence to the subgraph.
        #   * Unconditionally applying the first match and then breaking has the effect of taking
        #     whatever match the knowledge base deems most probable based on previous evidence
        #     (which is none, in this case).
        ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.selector_ed_suffix_template, partial=True):
            self.kb.core_dump()

            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            self.kb.core_dump()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_ed_suffix_template:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key == self.kb.context.now:
                    self.assertIsNone(now_key)
                    now_key = key
                else:
                    assert key and isinstance(key.match, Time)
                    self.assertIsNone(before_key)
                    before_key = key
            self.assertEqual(3, len(mapping))

            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Instance)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertIn(now_value, before_value.later_times)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value.precedes(current_time))
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value.precedes(now_value))
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, and that the
        # observations have the expected structural relationships.
        # NOTES:
        #   * In partial matching, the matched subgraph may only be *approximately* isomorphic to
        #     the pattern being matched. The is_isomorphic() method of the match will tell you
        #     whether the match is exact or merely approximate.
        #   * For queries, as opposed to updates, we use match.accept() instead of match.apply() to
        #     apply positive evidence to the match without modifying the graph's structure.
        match_count = 0
        for match in self.kb.match(self.selector_ed_suffix_template, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            print("Matched:")
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Instance)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertTrue(matched_before.precedes(current_time))

        self.assertEqual(1, match_count)

    def test_past_tense(self):
        """Create an empty knowledge base. Add an unstamped time that precedes the current time to
        the contents of the knowledge base by updating it with a pattern. Verify that the structure
        was added by querying the knowledge base afterward with the same pattern."""

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        # NOTES:
        #   * A match object is an immutable mapping from pattern components to graph elements.
        #   * Applying a match tells the knowledge base to update the graph to incorporate the
        #     structure of the pattern into the graph using the given elements, making the matched
        #     subgraph isomorphic to the pattern, and then apply positive evidence to the subgraph.
        #   * Unconditionally applying the first match and then breaking has the effect of taking
        #     whatever match the knowledge base deems most probable based on previous evidence
        #     (which is none, in this case).
        ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.selector_ed_suffix, partial=True):
            self.kb.core_dump()

            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            self.kb.core_dump()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
                    self.assertIsNone(now_key)
                    now_key = key
                else:
                    assert key.template.get() and isinstance(key.template.get().match, Time)
                    self.assertIsNone(before_key)
                    before_key = key
            self.assertEqual(3, len(mapping))

            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Instance)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertIn(now_value, before_value.later_times)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value.precedes(current_time))
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value.precedes(now_value))
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, and that the
        # observations have the expected structural relationships.
        # NOTES:
        #   * In partial matching, the matched subgraph may only be *approximately* isomorphic to
        #     the pattern being matched. The is_isomorphic() method of the match will tell you
        #     whether the match is exact or merely approximate.
        #   * For queries, as opposed to updates, we use match.accept() instead of match.apply() to
        #     apply positive evidence to the match without modifying the graph's structure.
        match_count = 0
        for match in self.kb.match(self.selector_ed_suffix, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            print("Matched:")
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Instance)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertTrue(matched_before.precedes(current_time))

        self.assertEqual(1, match_count)
