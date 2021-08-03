import unittest

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance


class TestApplyAndMatch(unittest.TestCase):

    def test_apply_and_match(self):
        """Create an empty knowledge base. Add the statement, 'An apple fell,' to the contents of
        the knowledge base by updating it with a pattern. Verify that the knowledge was added by
        querying the knowledge base afterward with the same pattern."""

        kb = KnowledgeBase()

        # Define "singular" and "plural", for the purposes of matching.
        singular = kb.get_divisibility(divisible=False, countable=True)
        # plural = kb.get_divisibility(divisible=True, countable=True)
        # mass = kb.get_divisibility(divisible=True, countable=False)

        # Ensure there are kinds corresponding to the words "apple" and "fall".
        kb.get_named_kind('apple', 1, add=True)
        kb.get_named_kind('fall', 1, add=True)

        # Define "an".
        selector_an_template = kb.get_selector_pattern('an', add=True)
        selector_an_template.match.divisibility.set(singular)

        # Define "-ed".
        pattern_before_now = kb.add_pattern(Time)
        pattern_before_now.children.add(kb.context.now)
        pattern_before_now.match.later_times.add(kb.context.now.match)
        selector_ed_suffix_template = kb.get_selector_pattern('-ed', add=True)
        selector_ed_suffix_template.match.time.set(pattern_before_now.match)
        selector_ed_suffix_template.children.add(pattern_before_now)

        # Create a pattern that will match "an apple".
        # NOTES:
        #   * Selectors act to modulate search in the knowledge base, whereas patterns determine
        #     what graph structures must be present for a match to occur.
        #   * The 'match' attribute of selectors acts as a placeholder for the observation or
        #     instance being matched. Setting an attribute of 'match' tells the selector that the
        #     matched observation or instance must have that value for the given attribute.
        #   * Selector match placeholders can be updated repeatedly. The same rules of evidence that
        #     apply to graph structures also apply to selector match placeholder structures. This
        #     means that each time you modify a selector match placeholder, this is weighed against
        #     previous usage to adjust the selector's behavior incrementally. You can also accept
        #     or reject a match returned by update() or query() to modulate selector behavior in a
        #     similar fashion using contextual cues, rather than (or in addition to) defining the
        #     selector's behavior up front like this.
        #   * When a string is passed to add_pattern(), it is treated as a kind name. The word and
        #     kind are automatically added, if necessary. If there are multiple kinds with the same
        #     name, the pattern connects to all of them with equally divided evidence, so that the
        #     intended meaning can be determined contextually based on the structural aspects of
        #     the pattern and the matched subgraph(s). Accepting or rejecting a match returned by
        #     update() or query() will apply evidence towards the pattern's connection to the
        #     matched kind and against the pattern's connections to the other kinds sharing the same
        #     name, influencing later match results for that same pattern.
        selector_an = selector_an_template.templated_clone()
        pattern_an_apple = kb.add_pattern(Instance)
        pattern_an_apple.selectors.add(selector_an)
        pattern_an_apple.match.kinds.update(kb.get_word('apple').kinds)

        # Create a pattern that will match "an apple fell".
        # NOTES:
        #   * kb.context.now is a built-in pattern that *contextually* matches the current time when
        #     the call to kb.update() or kb.query() is made. This is in contrast to kb.now(), which
        #     returns the *literal* current time.
        #   * During matching, the 'PRECEDES' relation for time patterns does not have to directly
        #     match two times connected by an edge of that type. It will also match two times for
        #     which the time stamps are in the correct order. This is for efficiency's sake, so we
        #     don't have to add an edge connecting every pair of times with time stamps.
        selector_ed_suffix = selector_ed_suffix_template.templated_clone()
        pattern_an_apple_fell = kb.add_pattern(Instance)
        pattern_an_apple_fell.selectors.add(selector_ed_suffix)
        pattern_an_apple_fell.children.add(pattern_an_apple)
        pattern_an_apple_fell.match.kinds.update(kb.get_word('fall').kinds)
        pattern_an_apple_fell.match.actor.set(pattern_an_apple.match)

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
        apple_key = fall_key = an_key = ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in kb.match(pattern_an_apple_fell, partial=True):
            kb.core_dump()

            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            kb.core_dump()

            mapping = match.get_mapping()
            for key in mapping:
                if key == selector_an:
                    self.assertIsNone(an_key)
                    an_key = key
                elif key == selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == kb.context.now:
                    self.assertIsNone(now_key)
                    now_key = key
                elif key.template.get() and isinstance(key.template.get().match, Time):
                    self.assertIsNone(before_key)
                    before_key = key
                elif key.match.kind.get().name.get().spelling == 'apple':
                    self.assertIsNone(apple_key)
                    apple_key = key
                else:
                    self.assertEqual('fall', key.match.kind.get().name.get().spelling)
                    self.assertIsNone(fall_key)
                    fall_key = key
            self.assertEqual(6, len(mapping))

            apple_value, apple_score = mapping[apple_key]
            self.assertIsInstance(apple_value, Instance)
            fall_value, fall_score = mapping[fall_key]
            self.assertIsInstance(fall_value, Instance)
            an_value, an_score = mapping[an_key]
            self.assertIsInstance(an_value, Instance)
            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Instance)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    apple:", apple_key)
            print("    fall:", fall_key)
            print("    an:", an_key)
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    an:", mapping.get(an_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertEqual(apple_value, fall_value.actor.get())
            self.assertEqual(before_value, fall_value.time.get())
            self.assertIn(now_value, before_value.later_times)
            self.assertEqual(an_value, apple_value)
            self.assertEqual(ed_value, fall_value)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = kb.now()

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
        for match in kb.match(pattern_an_apple_fell, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            print("Matched:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    an:", mapping.get(an_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_apple, apple_score = mapping[apple_key]
            self.assertIsInstance(matched_apple, Instance)
            matched_fall, fall_score = mapping[fall_key]
            self.assertIsInstance(matched_fall, Instance)
            matched_an, an_score = mapping[an_key]
            self.assertIsInstance(matched_an, Instance)
            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Instance)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertEqual(matched_apple, matched_fall.actor.get())
            self.assertEqual(matched_before, matched_fall.time.get())
            self.assertTrue(matched_before.precedes(current_time))
            self.assertEqual(matched_an, matched_apple)
            self.assertEqual(matched_ed, matched_fall)

        self.assertEqual(1, match_count)
