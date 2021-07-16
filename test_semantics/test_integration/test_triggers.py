import unittest
from typing import List

from semantics.kb_layer.evidence import apply_evidence
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance, PatternMatch


class TestTriggers(unittest.TestCase):

    def setUp(self) -> None:
        self.matches: List[PatternMatch] = []

        def mock_action(match):
            self.matches.append(match)

        self.mock_action = mock_action

        self.kb = KnowledgeBase()

        self.mock_action = self.kb.get_hook(mock_action)

        # Define "singular" and "plural", for the purposes of matching. This will normally be done
        # just once, when the knowledge base is first created.
        self.singular = self.kb.get_divisibility('singular', add=True)
        # plural = kb.get_divisibility('plural', add=True)

        # Ensure there are kinds corresponding to the words "apple" and "fall".
        self.kb.add_kind('apple')
        self.kb.add_kind('fall')

        # Define "an".
        self.selector_an_template = self.kb.get_selector_pattern('an', add=True)
        self.selector_an_template.match.divisibility.set(self.singular)
        apply_evidence(self.selector_an_template.match.vertex, 1)  # Assert it.
        self.selector_an = self.selector_an_template.templated_clone()

        # Define "-ed".
        self.pattern_before_now = self.kb.add_pattern(Time)
        self.pattern_before_now.children.add(self.kb.context.now)
        self.pattern_before_now.match.later_times.add(self.kb.context.now.match)
        apply_evidence(self.pattern_before_now.match.vertex, 1)  # Assert it.
        self.selector_ed_suffix_template = self.kb.get_selector_pattern('-ed', add=True)
        self.selector_ed_suffix_template.match.time.set(self.pattern_before_now.match)
        self.selector_ed_suffix_template.children.add(self.pattern_before_now)
        # NOTE: We do not assert the event's existence here; the ed suffix only tells us the
        #       temporal relationship to now, not whether the event took place.
        self.selector_ed_suffix = self.selector_ed_suffix_template.templated_clone()

        # Create a pattern that will match "an apple".
        self.pattern_an_apple = self.kb.add_pattern(Instance)
        self.pattern_an_apple.selectors.add(self.selector_an)
        self.pattern_an_apple.match.kinds.update(self.kb.get_word('apple').kinds)

        # Create a pattern that will match "an apple fell".
        self.pattern_an_apple_fell = self.kb.add_pattern(Instance)
        self.pattern_an_apple_fell.selectors.add(self.selector_ed_suffix)
        self.pattern_an_apple_fell.children.add(self.pattern_an_apple)
        self.pattern_an_apple_fell.match.kinds.update(self.kb.get_word('fall').kinds)
        self.pattern_an_apple_fell.match.actor.set(self.pattern_an_apple.match)
        apply_evidence(self.pattern_an_apple_fell.match.vertex, 1)  # Assert it.

    def test_trigger_activated_by_partial_match(self):
        # NOTES:
        # * We don't have to specify which vertices to attach the trigger to. The add_trigger method
        #   inspects the pattern to identify non-pattern vertices attached directly to the match
        #   representatives in the pattern and adds the trigger to each of them.
        # * The partial and complete flags indicate which sorts of matches for the pattern act as
        #   triggers. At least one of them must be True.
        # * The action is registered with the @action_registry.register decorator and given a unique
        #   handle. The handle is stored in the database, and is used to look up the action in the
        #   registry and call it when a new match is found.
        # * As with patterns and pattern matches, triggers and actions are represented as vertices
        #   in the graph for the purpose of persistence.
        # * Triggers are not immediately activated when new edges are added to the graph; rather,
        #   the new edges are put into a queue which is continually emptied by a trigger processing
        #   method which is designed to be repeated called in a background thread. This method
        #   generates the pattern matching context, checks if the pattern matches, and, if so, calls
        #   the corresponding action. Once the action is completed, the edge is removed from the
        #   queue. The method is also explicitly designed to support multithreading, so there can
        #   be multiple background threads executing triggers if necessary.

        self.kb.add_trigger(self.pattern_an_apple_fell, self.mock_action, partial=True)

        # Create a partial match.
        apple = None
        for match in self.kb.match(self.pattern_an_apple, partial=True):
            self.assertFalse(match.is_isomorphic())
            match.apply()
            apple = match.image.get()
        self.assertIsNotNone(apple)

        # Process pending triggers.
        self.kb.trigger_queue.process_all()

        # Check that the action was executed.
        for match in self.matches:
            self.assertEqual(self.pattern_an_apple_fell, match.preimage.get())
            child = None
            for child in match.children:
                break
            self.assertIsNotNone(child)
            self.assertEqual(self.pattern_an_apple, child.preimage.get())
            self.assertEqual(apple, child.image.get())
        self.assertEqual(1, len(self.matches))
