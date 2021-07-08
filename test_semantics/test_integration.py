import time
import unittest

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.knowledge_base import KnowledgeBase


class TestIntegration(unittest.TestCase):

    def test_statement_update(self):
        kb = KnowledgeBase()

        # Create a pattern that will match "an apple".
        # NOTE: Selectors act to modulate search in the knowledge base, whereas patterns
        #       determine what graph structures must be present for a match to occur.
        selector_an = kb.get_selector('an', add=True)
        pattern_an_apple = kb.add_pattern('apple')
        pattern_an_apple.selector.set(selector_an)

        # Create a pattern that will match "an apple fell".
        selector_ed_suffix = kb.get_selector('-ed', add=True)
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
            # NOTE: The 'precedes' method should return an Evidence instance, which is then
            #       automatically converted to a boolean value for the assertion.
            self.assertTrue(observed_fall.time.get().precedes(current_time))
        self.assertEqual(1, match_count)
