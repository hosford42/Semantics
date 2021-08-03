import threading
import unittest

from semantics.kb_layer.evidence import apply_evidence
from semantics.kb_layer.interface import KnowledgeBaseInterface
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance, PatternMatch

THREAD_LOCAL = threading.local()


def mock_action(kb: KnowledgeBaseInterface, match: PatternMatch):
    # if not match.is_isomorphic():
    #     match.apply()
    THREAD_LOCAL.matches.append((kb, match))


class TestTriggers(unittest.TestCase):

    def setUp(self) -> None:
        THREAD_LOCAL.matches = []

        kb = KnowledgeBase()

        self.mock_action = kb.get_hook(mock_action)

        # Define "singular" and "plural", for the purposes of matching.
        singular = kb.get_divisibility(divisible=False, countable=True)
        # plural = kb.get_divisibility(divisible=True, countable=True)
        # mass = kb.get_divisibility(divisible=True, countable=False)

        # Ensure there are kinds corresponding to the words "apple" and "fall".
        kb.get_named_kind('apple', 1, add=True)
        kb.get_named_kind('fall', 1, add=True)

        # Define "an".
        self.selector_an_template = kb.get_selector_pattern('an', add=True)
        self.selector_an_template.match.divisibility.set(singular)
        apply_evidence(self.selector_an_template.match.vertex, 1)  # Assert it.
        self.selector_an = self.selector_an_template.templated_clone()

        # Define "-ed".
        self.pattern_before_now = kb.add_pattern(Time)
        self.pattern_before_now.children.add(kb.context.now)
        self.pattern_before_now.match.later_times.add(kb.context.now.match)
        apply_evidence(self.pattern_before_now.match.vertex, 1)  # Assert it.
        self.selector_ed_suffix_template = kb.get_selector_pattern('-ed', add=True)
        self.selector_ed_suffix_template.match.time.set(self.pattern_before_now.match)
        self.selector_ed_suffix_template.children.add(self.pattern_before_now)
        # NOTE: We do not assert the event's existence here; the ed suffix only tells us the
        #       temporal relationship to now, not whether the event took place.
        self.selector_ed_suffix = self.selector_ed_suffix_template.templated_clone()

        # Create a pattern that will match "an apple".
        self.pattern_an_apple = kb.add_pattern(Instance)
        self.pattern_an_apple.selectors.add(self.selector_an)
        self.pattern_an_apple.match.kinds.update(kb.get_word('apple').kinds)

        # Create a pattern that will match "an apple fell".
        self.pattern_an_apple_fell = kb.add_pattern(Instance)
        self.pattern_an_apple_fell.selectors.add(self.selector_ed_suffix)
        self.pattern_an_apple_fell.children.add(self.pattern_an_apple)
        self.pattern_an_apple_fell.match.kinds.update(kb.get_word('fall').kinds)
        self.pattern_an_apple_fell.match.actor.set(self.pattern_an_apple.match)
        apply_evidence(self.pattern_an_apple_fell.match.vertex, 1)  # Assert it.

        self.kb = kb

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

        # self.kb.trigger_queue.process_all()
        # print("Creating partial match.")

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
        # NOTE: Each time the pending triggers are processed, a new "now" is created for the match
        #       context. This in turn enables a 2nd match for the same "apple" instance. The
        #       additional match isn't inherently a problem, since it is in fact a legitimate match.
        #       However, it can result in a proliferation of outbound PRECEDES edges from the time
        #       attached to the "fall" instance to various later times. It would be best to keep
        #       these to a minimum. To avoid this outcome, apply() does not add a new edge between
        #       two vertices if the edge is transitive and a path already exists.
        previous_mapping = None
        for kb, match in THREAD_LOCAL.matches:
            match: PatternMatch
            self.assertIs(kb, self.kb)
            mapping = match.get_mapping()
            print("Matched:")
            for key, (value, score) in mapping.items():
                print("    Key:", key)
                print("        Template:", key.template.get())
                print("        Representative:", key.match)
                print("        Value:", value)
                print("        Score:", score)
                if hasattr(value, 'time_stamp'):
                    print("        Time Stamp:", value.time_stamp)
            self.assertEqual(self.pattern_an_apple_fell, match.preimage.get())
            child = None
            for child in match.children:
                break
            self.assertIsNotNone(child)
            self.assertEqual(self.pattern_an_apple, child.preimage.get())
            self.assertEqual(apple, child.image.get())
            if previous_mapping:
                for key, (value, score) in mapping.items():
                    previous_value, previous_score = previous_mapping.get(key, (None, None))
                    if previous_value is not None and key.template.get() != self.kb.context.now:
                        self.assertEqual(previous_value, value)
            previous_mapping = mapping
        self.assertGreaterEqual(len(THREAD_LOCAL.matches), 1)
