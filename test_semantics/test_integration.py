import time
import unittest

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.knowledge_base import KnowledgeBase


class TestIntegration(unittest.TestCase):

    def test_statement_update(self):
        kb = KnowledgeBase()

        # Define "singular" and "plural", for the purposes of matching.
        phrase_number_kind = kb.add_kind('%PHRASE_NUMBER%')
        singular = kb.add_instance(phrase_number_kind)
        singular.name.set(kb.get_word('singular', add=True))
        plural = kb.add_instance(phrase_number_kind)
        plural.name.set(kb.get_word('plural', add=True))

        # Create a pattern that will match "an apple".
        # NOTES:
        #   * Selectors act to modulate search in the knowledge base, whereas patterns determine
        #     what graph structures must be present for a match to occur.
        #   * The 'match' attribute of selectors acts as a placeholder for the observation or
        #     instance being matched. Setting an attribute of 'match' tells the selector that the
        #     matched observation or instance must have that value for the given attribute.
        selector_an = kb.get_selector('an', add=True)
        selector_an.match.phrase_number.set(singular)
        pattern_an_apple = kb.add_pattern('apple')
        pattern_an_apple.selector.set(selector_an)

        # Create a pattern that will match "an apple fell".
        # NOTES:
        #   * kb.patterns.match_start_time() returns a built-in pattern that contextually matches
        #     the current time when the call to kb.update() or kb.query() is made.
        #   * Getting an attribute of the selector's match placeholder returns another placeholder
        #     with the appropriate relationship to the match placeholder.
        #   * Calling a method on the 'predicate' attribute of a match placeholder indicates that
        #     the indicated method of the matched value must return a True value for a match to take
        #     place.
        selector_ed_suffix = kb.get_selector('-ed', add=True)
        selector_ed_suffix.match.time.get().predicate.precedes(kb.patterns.match_start_time())
        pattern_an_apple_fell = kb.add_pattern('fall')
        pattern_an_apple_fell.selector.set(selector_ed_suffix)
        pattern_an_apple_fell.actor.set(pattern_an_apple)

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        kb.update(pattern_an_apple_fell)

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = kb.add_time(TimeStamp(time.time()))

        # Verify that there is exactly one match in the database for the pattern, and that the
        # observations have the expected structural relationships.
        match_count = 0
        for match in kb.query(pattern_an_apple_fell):
            match_count += 1
            observed_fall = match[pattern_an_apple_fell]
            observed_apple = match[pattern_an_apple]
            self.assertEqual(observed_apple, observed_fall.actor.get())
            # NOTE: The 'precedes.get' method should return an Evidence instance, which is then
            #       automatically converted to a boolean value for the assertion.
            self.assertTrue(observed_fall.time.get().precedes(current_time))
        self.assertEqual(1, match_count)
