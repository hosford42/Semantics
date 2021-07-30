# TODO: None of this is implemented yet. Once it is, subsume Time with the new framework.
import datetime
from typing import Dict
from unittest import TestCase

from semantics.kb_layer.knowledge_base import KnowledgeBase


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
        self.float_number_kind = self.kb.get_data_type(float, add=True)
        self.datetime_number_kind = self.kb.get_data_type(datetime.datetime, add=True)

    def test_number_requires_data_type(self):
        non_data_type_kind = self.kb.get_kind('kind', 0, add=True)
        with self.assertRaises(Exception):
            _number = self.kb.get_number(non_data_type_kind)

    def test_value_must_match_data_type(self):
        with self.assertRaises(TypeError):
            _number = self.kb.get_number(self.float_number_kind, '0')

    def test_kind_of_number_without_value_is_number_kind(self):
        number = self.kb.get_number(self.float_number_kind)
        self.assertEqual(self.float_number_kind, number.float_number_kind.get())

    def test_kind_of_number_with_value_is_number_kind(self):
        number = self.kb.get_number(self.float_number_kind, 1.0)
        self.assertEqual(self.float_number_kind, number.float_number_kind.get())

    def test_number_without_value_has_value_None(self):
        number = self.kb.get_number(self.float_number_kind)
        self.assertIsNone(number.value)

    def test_number_with_value_has_given_value(self):
        number = self.kb.get_number(self.float_number_kind, 1.0)
        self.assertEqual(1.0, number.value)

    def test_comparison_of_number_without_value_to_itself(self):
        number = self.kb.get_number(self.float_number_kind)
        result = get_comparison_results(number, number)
        self.assertEqual(EXPECTED_FOR_SAME_VALUE, result)

    def test_comparison_of_two_unrelated_numbers_without_values(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)

    def test_comparison_of_two_related_numbers_without_values(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind)
        number1.greater_values.add(number2)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_comparison_of_number_without_value_to_unrelated_number_with_value(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind, 1.0)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)

    def test_comparison_of_number_without_value_to_related_number_with_value(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind, 1.0)
        number1.greater_values.add(number2)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_comparison_of_two_numbers_with_different_values(self):
        number1 = self.kb.get_number(self.float_number_kind, 0.0)
        number2 = self.kb.get_number(self.float_number_kind, 1.0)
        result = get_comparison_results(number1, number2)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_chained_comparison_of_unrelated_numbers_without_values(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind)
        number1.greater_values.add(number2)
        number3 = self.kb.get_number(self.float_number_kind)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)

    def test_chained_comparison_of_related_numbers_without_values(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind)
        number1.greater_values.add(number2)
        number3 = self.kb.get_number(self.float_number_kind)
        number2.greater_values.add(number3)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_chained_comparison_of_related_numbers_with_and_without_values_case1(self):
        number1 = self.kb.get_number(self.float_number_kind)
        number2 = self.kb.get_number(self.float_number_kind, 0.0)
        number1.greater_values.add(number2)
        number3 = self.kb.get_number(self.float_number_kind, 1.0)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_chained_comparison_of_related_numbers_with_and_without_values_case2(self):
        number1 = self.kb.get_number(self.float_number_kind, 0.0)
        number2 = self.kb.get_number(self.float_number_kind, 0.1)
        number3 = self.kb.get_number(self.float_number_kind)
        number2.greater_values.add(number3)
        result = get_comparison_results(number1, number3)
        self.assertEqual(EXPECTED_FOR_INCREASING_VALUE, result)

    def test_comparison_of_numbers_with_values_of_uncomparable_types(self):
        float_number = self.kb.get_number(self.float_number_kind, 0.0)
        datetime_number = self.kb.get_number(self.datetime_number_kind, datetime.datetime.now())
        result = get_comparison_results(float_number, datetime_number)
        self.assertEqual(EXPECTED_FOR_UNRELATED_VALUE, result)
