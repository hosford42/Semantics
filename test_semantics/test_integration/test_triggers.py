import unittest

from semantics.kb_layer.evidence import apply_evidence, get_evidence, get_evidence_mean
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance


class TestTriggers(unittest.TestCase):

    def test_triggers(self):

        # TODO

        action_registry = ...

        @action_registry.register
        def action(match):
            ...

        kb = KnowledgeBase()
        pattern = ...

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
        trigger = kb.add_trigger(pattern, action, partial=True, complete=False)

        self.fail()
