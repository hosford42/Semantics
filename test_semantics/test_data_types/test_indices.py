from unittest import TestCase

from semantics.data_types.indices import UniqueID


class TestUniqueID(TestCase):

    def test_equality(self):
        class Subclass1(UniqueID):
            pass

        class Subclass2(UniqueID):
            pass

        self.assertEqual(Subclass1(0), Subclass1(0), "Two IDs with the same type and value should be equal")
        self.assertNotEqual(Subclass1(0), Subclass1(1), "Two IDs with different values should be unequal")
        self.assertNotEqual(Subclass1(0), Subclass2(0), "Two IDs with different types should be unequal")
