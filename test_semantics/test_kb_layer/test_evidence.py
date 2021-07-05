from unittest import TestCase

from semantics.kb_layer.evidence import get_evidence_mean, get_evidence_samples, apply_evidence
from semantics.kb_layer.knowledge_base import KnowledgeBase


class TestFunctions(TestCase):

    def test_get_evidence_mean(self):
        kb = KnowledgeBase()
        word = kb.get_word('word', add=True)
        vertex = word.vertex

        original_mean = get_evidence_mean(vertex)
        original_samples = get_evidence_samples(vertex)

        # Default evidence mean is at least 0.5, meaning the element's mere existence in the graph
        # is treated as neutral or positive evidence of its existence.
        self.assertGreaterEqual(original_mean, 0.5)

        new_value = 0.9
        new_samples = 2.5
        apply_evidence(vertex, new_value, new_samples)

        weighted_total = original_mean * original_samples + new_value * new_samples
        total_samples = original_samples + new_samples
        new_mean = weighted_total / total_samples
        self.assertEqual(get_evidence_mean(vertex), new_mean)

    def test_get_evidence_samples(self):
        kb = KnowledgeBase()
        word = kb.get_word('word', add=True)
        vertex = word.vertex

        original_samples = get_evidence_samples(vertex)

        # Initial sample count is greater than zero, in order to implement additive smoothing.
        self.assertGreater(original_samples, 0)

        new_samples = 10
        apply_evidence(vertex, 0.5, new_samples)

        self.assertEqual(get_evidence_samples(vertex), original_samples + new_samples)

    def test_apply_evidence(self):
        kb = KnowledgeBase()
        word = kb.get_word('word', add=True)
        vertex = word.vertex

        # Value must be non-negative and no greater than one. Sample count must be non-negative.
        with self.assertRaises(ValueError):
            apply_evidence(vertex, -0.1, 1)
        with self.assertRaises(ValueError):
            apply_evidence(vertex, 1.1, 1)
        with self.assertRaises(ValueError):
            apply_evidence(vertex, 0.5, -1)
        apply_evidence(vertex, 0, 1)
        apply_evidence(vertex, 1, 1)
        apply_evidence(vertex, 0, 0)
        apply_evidence(vertex, 1, 0)
