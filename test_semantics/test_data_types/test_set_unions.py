from collections import Counter
from unittest import TestCase

from semantics.data_types.set_unions import SetUnion


class TestSetUnion(TestCase):

    def test_contains(self):
        a = {1, 2}
        b = {2, 3}
        u = SetUnion(a, b)
        assert 1 in u
        assert 2 in u
        assert 3 in u
        b.remove(2)
        assert 2 in u
        a.remove(1)
        assert 1 not in u

    def test_len(self):
        a = {1, 2}
        b = {2, 3}
        u = SetUnion(a, b)
        assert len(u) == 3

    def test_iter(self):
        a = {1, 2}
        b = {2, 3}
        u = SetUnion(a, b)
        c = Counter(u)
        assert c[1] == 1
        assert c[2] == 1
        assert c[3] == 1
