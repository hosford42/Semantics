from typing import Dict
from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Number


def get_comparison_results(a, b) -> Dict[str, bool]:
    return {
        '==': a == b,
        '!=': a != b,
        '<=': a <= b,
        '>': a > b,
        '<': a < b,
        '>=': a >= b,
    }


EXPECTED_FOR_SAME_VALUE = get_comparison_results(0, 0)
EXPECTED_FOR_INCREASING_VALUE = get_comparison_results(0, 1)
EXPECTED_FOR_UNRELATED_VALUE = {
    '==': False,
    '!=': True,
    '<=': False,
    '>': False,
    '>=': False,
    '<': False,
}


class TestNumber(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_number_requires_comparable_data_type(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _number = self.kb.get_number(object())

    def test_number_without_value_has_type_Number(self):
        number = self.kb.get_number()
        self.assertIsInstance(number, Number)

    def test_number_with_value_has_type_Number(self):
        number = self.kb.get_number(0.0)
        self.assertIsInstance(number, Number)

    def test_number_without_value_has_value_None(self):
        number = self.kb.get_number()
        self.assertIsNone(number.value)

    def test_number_with_value_has_given_value(self):
        number = self.kb.get_number(1.0)
        self.assertEqual(1.0, number.value)

    def test_comparison_of_number_without_value_to_itself(self):
        number = self.kb.get_number()
        result = get_comparison_results(number, number)
        self.assertEqual(EXPECTED_FOR_SAME_VALUE, result)

    def test_comparison_of_two_unrelated_numbers_without_values(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number()
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)

    def test_comparison_of_two_related_numbers_without_values(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number()
        number1.greater_values.add(number2)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_comparison_of_number_without_value_to_unrelated_number_with_value(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number(1.0)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)

    def test_comparison_of_number_without_value_to_related_number_with_value(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number(1.0)
        number1.greater_values.add(number2)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_comparison_of_two_numbers_with_different_values(self):
        number1 = self.kb.get_number(0.0)
        number2 = self.kb.get_number(1.0)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_chained_comparison_of_unrelated_numbers_without_values(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number()
        number1.greater_values.add(number2)
        number3 = self.kb.get_number()
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)

    def test_chained_comparison_of_related_numbers_without_values(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number()
        number1.greater_values.add(number2)
        number3 = self.kb.get_number()
        number2.greater_values.add(number3)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_chained_comparison_of_related_numbers_with_and_without_values_case1(self):
        number1 = self.kb.get_number()
        number2 = self.kb.get_number(0.0)
        number1.greater_values.add(number2)
        number3 = self.kb.get_number(1.0)
        self.assertLess(number1, number2)
        self.assertLess(number2, number3)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_chained_comparison_of_related_numbers_with_and_without_values_case2(self):
        number1 = self.kb.get_number(0.0)
        number2 = self.kb.get_number(0.1)
        number3 = self.kb.get_number()
        number2.greater_values.add(number3)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    # def test_comparison_of_numbers_with_values_of_uncomparable_types(self):
    #     float_number = self.kb.get_number(0.0)
    #     datetime_number = self.kb.get_number(datetime.datetime.now())
    #     result = get_comparison_results(float_number, datetime_number)
    #     self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)
