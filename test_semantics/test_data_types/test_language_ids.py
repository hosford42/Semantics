import pickle
from unittest import TestCase
from unittest.mock import patch

from semantics.data_types.language_ids import LanguageID


class TestLanguageID(TestCase):

    invalid_code = 'd'

    iso639_2_t_code = 'deu'
    iso639_2_b_code = 'ger'
    iso639_1_code = 'de'
    english_name = 'German'
    autonym = 'Deutsch'

    expected_format = iso639_2_t_code
    unexpected_format = iso639_1_code

    @patch('logging.Logger.warning')
    def test_invalid_code(self, log_warning_method):
        lid = LanguageID(self.invalid_code)
        log_warning_method.assert_called()
        self.assertFalse(lid.valid)
        self.assertEqual(lid, eval(repr(lid)))
        self.assertEqual(self.invalid_code, str(lid))
        self.assertIsNone(lid.iso639_1)
        self.assertIsNone(lid.iso639_2b)
        self.assertIsNone(lid.iso639_2t)
        self.assertIsNone(lid.english_name)
        self.assertIsNone(lid.autonym)

        self.assertEqual(lid, lid)
        self.assertEqual(LanguageID(self.invalid_code), lid)
        self.assertNotEqual(LanguageID(self.expected_format), lid)
        self.assertNotEqual(hash(LanguageID(self.expected_format)), hash(lid))

    def test_valid_code_expected_format(self):
        lid = LanguageID(self.expected_format)
        self.assertTrue(lid.valid)
        self.assertEqual(lid, eval(repr(lid)))
        self.assertEqual(self.expected_format, str(lid))
        self.assertEqual(self.iso639_1_code, lid.iso639_1)
        self.assertEqual(self.iso639_2_b_code, lid.iso639_2b)
        self.assertEqual(self.iso639_2_t_code, lid.iso639_2t)
        self.assertEqual(self.english_name, lid.english_name)
        self.assertEqual(self.autonym, lid.autonym)

        self.assertEqual(lid, lid)
        self.assertEqual(LanguageID(self.unexpected_format), lid)
        self.assertNotEqual(LanguageID('eng'), lid)
        self.assertNotEqual(hash(LanguageID('eng')), hash(lid))

    def test_valid_code_unexpected_format(self):
        lid = LanguageID(self.unexpected_format)
        self.assertTrue(lid.valid)
        self.assertEqual(lid, eval(repr(lid)))
        self.assertEqual(self.expected_format, str(lid))
        self.assertEqual(self.iso639_1_code, lid.iso639_1)
        self.assertEqual(self.iso639_2_b_code, lid.iso639_2b)
        self.assertEqual(self.iso639_2_t_code, lid.iso639_2t)
        self.assertEqual(self.english_name, lid.english_name)
        self.assertEqual(self.autonym, lid.autonym)

        self.assertEqual(lid, lid)
        self.assertEqual(LanguageID(self.expected_format), lid)
        self.assertNotEqual(LanguageID('eng'), lid)
        self.assertNotEqual(hash(LanguageID('eng')), hash(lid))

    def test_equality(self):
        self.assertFalse('eng' == LanguageID('eng'))
        self.assertFalse(LanguageID('eng') == 'eng')

        self.assertTrue('eng' != LanguageID('eng'))
        self.assertTrue(LanguageID('eng') != 'eng')

        self.assertTrue(LanguageID('en') == LanguageID('eng'))
        self.assertFalse(LanguageID('en') != LanguageID('eng'))

    def test_pickle_protocol(self):
        language_id = LanguageID('eng')
        pickled = pickle.dumps(language_id, protocol=pickle.HIGHEST_PROTOCOL)
        self.assertEqual(language_id, pickle.loads(pickled))
