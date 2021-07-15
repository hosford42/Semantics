import unittest

from semantics.kb_layer.evidence import apply_evidence, get_evidence, get_evidence_mean
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance


class TestTriggers(unittest.TestCase):

    def test_triggers(self):
        kb = KnowledgeBase()

        # TODO
        self.fail()
