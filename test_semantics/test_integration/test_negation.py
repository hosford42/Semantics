import unittest

from semantics.kb_layer.evidence import apply_evidence, get_evidence, get_evidence_mean
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance, Event


class TestNegation(unittest.TestCase):

    def setUp(self) -> None:
        kb = KnowledgeBase()

        # Define "singular" and "plural", for the purposes of matching.
        singular = kb.get_divisibility(divisible=False, countable=True)
        # plural = kb.get_divisibility(divisible=True, countable=True)
        # mass = kb.get_divisibility(divisible=True, countable=False)

        # Ensure there are kinds corresponding to the words "apple" and "fall".
        kb.get_named_kind('apple', 1, add=True)
        kb.get_named_kind('fall', 1, add=True)

        # Define "the".
        # NOTE: This is a very simplistic definition of "the". In actuality, we should choose the
        #       most contextually relevant singular instance, rather than just any singular
        #       instance. However, for the purposes of these tests, this definition is sufficient.
        self.selector_the_template = kb.get_selector_pattern('the', add=True)
        self.selector_the_template.match.divisibility.set(singular)
        apply_evidence(self.selector_the_template.match.vertex, 1)  # Assert it.
        self.selector_the = self.selector_the_template.templated_clone()

        # Define "-ed".
        self.pattern_before_now = kb.add_pattern(Time)
        self.pattern_before_now.children.add(kb.context.now)
        self.pattern_before_now.match.later_times.add(kb.context.now.match)
        apply_evidence(self.pattern_before_now.match.vertex, 1)  # Assert it.
        self.selector_ed_suffix_template = kb.get_selector_pattern('-ed', schema=Event, add=True)
        self.selector_ed_suffix_template.match.time.set(self.pattern_before_now.match)
        self.selector_ed_suffix_template.children.add(self.pattern_before_now)
        # NOTE: We do not assert the event's existence here; the ed suffix only tells us the
        #       temporal relationship to now, not whether the event took place.
        self.selector_ed_suffix = self.selector_ed_suffix_template.templated_clone()

        # Create a pattern that will match "the apple".
        self.pattern_the_apple = kb.add_pattern(Instance)
        self.pattern_the_apple.selectors.add(self.selector_the)
        self.pattern_the_apple.match.kinds.update(kb.get_word('apple').kinds)

        # Create a pattern that will match "the apple fell".
        self.pattern_the_apple_fell = kb.add_pattern(Event)
        self.pattern_the_apple_fell.selectors.add(self.selector_ed_suffix)
        self.pattern_the_apple_fell.children.add(self.pattern_the_apple)
        self.pattern_the_apple_fell.match.kinds.update(kb.get_word('fall').kinds)
        self.pattern_the_apple_fell.match.actor.set(self.pattern_the_apple.match)
        apply_evidence(self.pattern_the_apple_fell.match.vertex, 1)  # Assert it.

        # Create a pattern that will match "the apple did not fall".
        self.pattern_the_apple_did_not_fall = kb.add_pattern(Event)
        self.pattern_the_apple_did_not_fall.selectors.add(self.selector_ed_suffix)
        self.pattern_the_apple_did_not_fall.children.add(self.pattern_the_apple)
        self.pattern_the_apple_did_not_fall.match.kinds.update(kb.get_word('fall').kinds)
        self.pattern_the_apple_did_not_fall.match.actor.set(self.pattern_the_apple.match)
        apply_evidence(self.pattern_the_apple_did_not_fall.match.vertex, 0)  # Negate it.

        self.kb = kb

    def test_positive_matches_positive(self):
        """Create an empty knowledge base. Add the statement, 'The apple fell,' to the contents of
        the knowledge base by updating it with a pattern. Verify that querying the knowledge base
        with the same pattern results in a match with positive-leaning evidence."""

        # Apply the positive pattern as a statement to update the graph. This should modify the
        # structure of the graph by adding (indirect) observations which structurally mirror the
        # pattern, and which can later be matched by queries.
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.pattern_the_apple_fell, partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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
            self.assertIsInstance(fall_value, Event)
            the_value, the_score = mapping[the_key]
            self.assertIsInstance(the_value, Instance)
            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Event)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    apple:", apple_key)
            print("    fall:", fall_key)
            print("    the:", the_key)
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            for score in (apple_score, fall_score, the_score, ed_score, now_score, before_score):
                self.assertGreater(score, 0.5)

            for key, (value, score) in mapping.items():
                key_evidence = get_evidence_mean(key.match.vertex)
                value_evidence = get_evidence_mean(value.vertex)
                if key_evidence != 0.5:
                    self.assertEqual(key_evidence > 0.5, value_evidence > 0.5,
                                     (key, value, score, key_evidence, value_evidence))

            self.assertEqual(apple_value, fall_value.actor.get())
            self.assertEqual(before_value, fall_value.time.get())
            self.assertIn(now_value, before_value.later_times)
            self.assertEqual(the_value, apple_value)
            self.assertEqual(ed_value, fall_value)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value in current_time.earlier_times)
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value in now_value.earlier_times)
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, that the
        # observations have the expected structural relationships, and that the match's evidence
        # leans positive.
        match_count = 0
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        for match in self.kb.match(self.pattern_the_apple_fell, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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

            print("Matched:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_apple, apple_score = mapping[apple_key]
            self.assertIsInstance(matched_apple, Instance)
            matched_fall, fall_score = mapping[fall_key]
            self.assertIsInstance(matched_fall, Event)
            matched_the, the_score = mapping[the_key]
            self.assertIsInstance(matched_the, Instance)
            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Event)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertEqual(matched_apple, matched_fall.actor.get())
            self.assertEqual(matched_before, matched_fall.time.get())
            self.assertTrue(matched_before.precedes(current_time))
            self.assertEqual(matched_the, matched_apple)
            self.assertEqual(matched_ed, matched_fall)
            self.assertTrue(get_evidence(match.vertex))
        self.assertEqual(1, match_count)

    def test_negative_matches_negative(self):
        """Create an empty knowledge base. Add the statement, 'The apple did not fall,' to the
        contents of the knowledge base by updating it with a pattern. Verify that querying the
        knowledge base with the same pattern results in a match with positive-leaning evidence."""

        # Apply the negative pattern as a statement to update the graph. This should modify the
        # structure of the graph by adding (indirect) observations which structurally mirror the
        # pattern, and which can later be matched by queries.
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.pattern_the_apple_did_not_fall, partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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
            self.assertIsInstance(fall_value, Event)
            the_value, the_score = mapping[the_key]
            self.assertIsInstance(the_value, Instance)
            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Event)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    apple:", apple_key)
            print("    fall:", fall_key)
            print("    the:", the_key)
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            for score in (apple_score, fall_score, the_score, ed_score, now_score, before_score):
                self.assertGreater(score, 0.5)

            for key, (value, score) in mapping.items():
                key_evidence = get_evidence_mean(key.match.vertex)
                value_evidence = get_evidence_mean(value.vertex)
                if key_evidence != 0.5:
                    self.assertEqual(key_evidence > 0.5, value_evidence > 0.5,
                                     (key, value, score, key_evidence, value_evidence))

            self.assertEqual(apple_value, fall_value.actor.get())
            self.assertEqual(before_value, fall_value.time.get())
            self.assertIn(now_value, before_value.later_times)
            self.assertEqual(the_value, apple_value)
            self.assertEqual(ed_value, fall_value)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value in current_time.earlier_times)
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value in now_value.earlier_times)
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, that the
        # observations have the expected structural relationships, and that the match's evidence
        # leans positive.
        match_count = 0
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        for match in self.kb.match(self.pattern_the_apple_did_not_fall, partial=True):
            match_count += 1
            mapping = match.get_mapping()

            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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

            print("Matched:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_apple, apple_score = mapping[apple_key]
            self.assertIsInstance(matched_apple, Instance)
            matched_fall, fall_score = mapping[fall_key]
            self.assertIsInstance(matched_fall, Event)
            matched_the, the_score = mapping[the_key]
            self.assertIsInstance(matched_the, Instance)
            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Event)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertEqual(matched_apple, matched_fall.actor.get())
            self.assertEqual(matched_before, matched_fall.time.get())
            self.assertTrue(matched_before.precedes(current_time))
            self.assertEqual(matched_the, matched_apple)
            self.assertEqual(matched_ed, matched_fall)
            self.assertTrue(get_evidence(match.vertex))
        self.assertEqual(1, match_count)

    def test_positive_contradicts_negative(self):
        """Create an empty knowledge base. Add the statement, 'The apple did not fall,' to the
        contents of the knowledge base by updating it with a pattern. Verify that the statement,
        'The apple fell,' matches, but that the match's evidence leans negative."""

        # Apply the negative pattern as a statement to update the graph. This should modify the
        # structure of the graph by adding (indirect) observations which structurally mirror the
        # pattern, and which can later be matched by queries.
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.pattern_the_apple_did_not_fall, partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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
            self.assertIsInstance(fall_value, Event)
            the_value, the_score = mapping[the_key]
            self.assertIsInstance(the_value, Instance)
            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Event)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    apple:", apple_key)
            print("    fall:", fall_key)
            print("    the:", the_key)
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertEqual(apple_value, fall_value.actor.get())
            self.assertEqual(before_value, fall_value.time.get())
            self.assertIn(now_value, before_value.later_times)
            self.assertEqual(the_value, apple_value)
            self.assertEqual(ed_value, fall_value)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value in current_time.earlier_times)
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value in now_value.earlier_times)
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, that the
        # observations have the expected structural relationships, and that the match's evidence
        # leans negative due to the contradiction.
        match_count = 0
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        for match in self.kb.match(self.pattern_the_apple_fell, partial=True):
            match_count += 1

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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

            print("Matched:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_apple, apple_score = mapping[apple_key]
            self.assertIsInstance(matched_apple, Instance)
            matched_fall, fall_score = mapping[fall_key]
            self.assertIsInstance(matched_fall, Event)
            matched_the, the_score = mapping[the_key]
            self.assertIsInstance(matched_the, Instance)
            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Event)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertEqual(matched_apple, matched_fall.actor.get())
            self.assertEqual(matched_before, matched_fall.time.get())
            self.assertTrue(matched_before.precedes(current_time))
            self.assertEqual(matched_the, matched_apple)
            self.assertEqual(matched_ed, matched_fall)
            self.assertFalse(get_evidence(match.vertex))
        self.assertEqual(1, match_count)

    def test_negative_contradicts_positive(self):
        """Create an empty knowledge base. Add the statement, 'The apple fell,' to the contents of
        the knowledge base by updating it with a pattern. Verify that the statement, 'The apple did
        not fall,' matches, but that the match's evidence leans negative."""

        # Apply the positive pattern as a statement to update the graph. This should modify the
        # structure of the graph by adding (indirect) observations which structurally mirror the
        # pattern, and which can later be matched by queries.
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        now_value = before_value = None
        for match in self.kb.match(self.pattern_the_apple_fell, partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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
            self.assertIsInstance(fall_value, Event)
            the_value, the_score = mapping[the_key]
            self.assertIsInstance(the_value, Instance)
            ed_value, ed_score = mapping[ed_key]
            self.assertIsInstance(ed_value, Event)
            now_value, now_score = mapping[now_key]
            self.assertIsInstance(now_value, Time)
            before_value, before_score = mapping[before_key]
            self.assertIsInstance(before_value, Time)

            print("Keys:")
            print("    apple:", apple_key)
            print("    fall:", fall_key)
            print("    the:", the_key)
            print("    -ed:", ed_key)
            print("    now:", now_key)
            print("    before:", before_key)
            print()

            print("Applied:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertEqual(apple_value, fall_value.actor.get())
            self.assertEqual(before_value, fall_value.time.get())
            self.assertIn(now_value, before_value.later_times)
            self.assertEqual(the_value, apple_value)
            self.assertEqual(ed_value, fall_value)
            break
        else:
            self.assertFalse("No matches found.")

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = self.kb.now()

        self.assertIsNotNone(now_value)
        self.assertTrue(now_value in current_time.earlier_times)
        self.assertIsNotNone(before_value)
        self.assertTrue(before_value in now_value.earlier_times)
        self.assertTrue(before_value.precedes(current_time))

        # Verify that there is exactly one match in the database for the pattern, that the
        # observations have the expected structural relationships, and that the match's evidence
        # leans negative due to the contradiction.
        match_count = 0
        apple_key = fall_key = the_key = ed_key = now_key = before_key = None
        for match in self.kb.match(self.pattern_the_apple_did_not_fall, partial=True):
            match_count += 1

            mapping = match.get_mapping()
            for key in mapping:
                if key == self.selector_the:
                    self.assertIsNone(the_key)
                    the_key = key
                elif key == self.selector_ed_suffix:
                    self.assertIsNone(ed_key)
                    ed_key = key
                elif key.template.get() == self.kb.context.now:
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

            print("Matched:")
            print("    apple:", mapping.get(apple_key))
            print("    fall:", mapping.get(fall_key))
            print("    the:", mapping.get(the_key))
            print("    -ed:", mapping.get(ed_key))
            print("    now:", mapping.get(now_key))
            print("    before:", mapping.get(before_key))
            print()

            self.assertTrue(match.is_isomorphic())

            matched_apple, apple_score = mapping[apple_key]
            self.assertIsInstance(matched_apple, Instance)
            matched_fall, fall_score = mapping[fall_key]
            self.assertIsInstance(matched_fall, Event)
            matched_the, the_score = mapping[the_key]
            self.assertIsInstance(matched_the, Instance)
            matched_ed, ed_score = mapping[ed_key]
            self.assertIsInstance(matched_ed, Event)
            matched_now, now_score = mapping[now_key]
            self.assertIsInstance(matched_now, Time)
            matched_before, before_score = mapping[before_key]
            self.assertIsInstance(matched_before, Time)

            self.assertEqual(matched_apple, matched_fall.actor.get())
            self.assertEqual(matched_before, matched_fall.time.get())
            self.assertTrue(matched_before.precedes(current_time))
            self.assertEqual(matched_the, matched_apple)
            self.assertEqual(matched_ed, matched_fall)
            self.assertFalse(get_evidence(match.vertex))
        self.assertEqual(1, match_count)
