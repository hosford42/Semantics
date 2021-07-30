from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase


# TODO: None of this is implemented yet. Once it is, subsume Time with the new framework.

class TestQuantity(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_value(self):
        unit = self.kb.get_unit('unit', float, add=True)
        quantity1 = self.kb.get_quantity(unit)
        self.assertIsNone(quantity1.value)
        self.assertEqual(unit, quantity1.unit.get())
        quantity2 = self.kb.get_quantity(unit, 1.0)
        self.assertEqual(1.0, quantity2.value)
        self.assertEqual(unit, quantity2.unit.get())

    def test_quantity_equality_without_value(self):
        unit = self.kb.get_unit('unit', float, add=True)
        quantity1 = self.kb.get_quantity(unit)
        quantity2 = self.kb.get_quantity(unit)
        self.assertNotEqual(quantity1, quantity2)
        quantity3 = self.kb.get_quantity(unit, 1.0)
        self.assertNotEqual(quantity1, quantity3)

    def test_quantity_equality_with_value(self):
        unit = self.kb.get_unit('unit', float, add=True)
        quantity1 = self.kb.get_quantity(unit, 0.0)
        quantity2 = self.kb.get_quantity(unit, 0.0)
        self.assertEqual(quantity1, quantity2)
        quantity3 = self.kb.get_quantity(unit, 1.0)
        self.assertNotEqual(quantity1, quantity3)

    def test_ordering_without_value(self):
        unit = self.kb.get_unit('unit', float, add=True)
        quantity1 = self.kb.get_quantity(unit)
        self.assertFalse(quantity1 < quantity1)
        self.assertTrue(quantity1 <= quantity1)
        self.assertFalse(quantity1 > quantity1)
        self.assertTrue(quantity1 >= quantity1)
        self.assertTrue(quantity1 == quantity1)
        self.assertFalse(quantity1 != quantity1)
        quantity2 = self.kb.get_quantity(unit)
        self.assertFalse(quantity1 < quantity2)
        self.assertFalse(quantity1 <= quantity2)
        self.assertFalse(quantity1 > quantity2)
        self.assertFalse(quantity1 >= quantity2)
        self.assertFalse(quantity1 == quantity2)
        self.assertTrue(quantity1 != quantity2)
        quantity1.greater.add(quantity2)
        self.assertTrue(quantity1 < quantity2)
        self.assertTrue(quantity1 <= quantity2)
        self.assertFalse(quantity1 > quantity2)
        self.assertFalse(quantity1 >= quantity2)
        self.assertFalse(quantity1 == quantity2)
        self.assertTrue(quantity1 != quantity2)

    def test_ordering_with_value(self):
        unit = self.kb.get_unit('unit', float, add=True)
        quantity1 = self.kb.get_quantity(unit, 0.0)
        self.assertFalse(quantity1 < quantity1)
        self.assertTrue(quantity1 <= quantity1)
        self.assertFalse(quantity1 > quantity1)
        self.assertTrue(quantity1 >= quantity1)
        self.assertTrue(quantity1 == quantity1)
        self.assertFalse(quantity1 != quantity1)
        quantity2 = self.kb.get_quantity(unit, 1.0)
        self.assertTrue(quantity1 < quantity2)
        self.assertTrue(quantity1 <= quantity2)
        self.assertFalse(quantity1 > quantity2)
        self.assertFalse(quantity1 >= quantity2)
        self.assertFalse(quantity1 == quantity2)
        self.assertTrue(quantity1 != quantity2)
