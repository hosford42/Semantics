from unittest import TestCase

from semantics.data_types.exceptions import SchemaValidationError
from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.schema import SchemaValidation, Schema, validation


class TestSchemaValidation(TestCase):

    def setUp(self) -> None:
        kb = KnowledgeBase()
        self.schema_instance1 = kb.get_word('word', add=True)
        self.schema_instance2 = kb.add_time()

    def test_format_message(self):
        sv = SchemaValidation('simple message', lambda s: True)
        self.assertEqual('simple message', sv.format_message(self.schema_instance1))
        sv = SchemaValidation('templated {schema} message', lambda s: True)
        self.assertEqual('templated Word message', sv.format_message(self.schema_instance1))

    def test_call_protocol(self):
        sv = SchemaValidation('message', lambda s: s is self.schema_instance1)
        self.assertTrue(sv(self.schema_instance1))
        self.assertFalse(sv(self.schema_instance2))

    def test_get_validation_error(self):
        sv = SchemaValidation('message', lambda s: s is self.schema_instance1)
        self.assertIsNone(sv.get_validation_error(self.schema_instance1))
        self.assertEqual('message', sv.get_validation_error(self.schema_instance2))

    def test_validate(self):
        sv = SchemaValidation('message', lambda s: s is self.schema_instance1)
        sv.validate(self.schema_instance1)
        with self.assertRaises(SchemaValidationError):
            sv.validate(self.schema_instance2)


class TestFunctions(TestCase):

    def setUp(self) -> None:
        kb = KnowledgeBase()
        self.schema_instance1 = kb.get_word('word', add=True)
        self.schema_instance2 = kb.add_time()

    def test_validation(self):
        @validation('message')
        def sv(s):
            return s is self.schema_instance1
        self.assertIsInstance(sv, SchemaValidation)
        self.assertTrue(sv(self.schema_instance1))
        self.assertFalse(sv(self.schema_instance2))


class TestSchema(TestCase):

    def setUp(self) -> None:
        self.kb = KnowledgeBase()
        self.schema_instance1 = self.kb.get_word('word', add=True)
        self.schema_instance2 = self.kb.add_time()

    def test_role_name(self):
        class MySchema(Schema):
            __role_name__ = 'my role'

        self.assertEqual('my role', MySchema.role_name())

        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        self.assertEqual('my role', s.role_name())

        class MyOtherSchema(Schema):
            pass

        self.assertEqual('MY_OTHER_SCHEMA', MyOtherSchema.role_name())

        s = MyOtherSchema(self.schema_instance1.vertex, self.kb.database)
        self.assertEqual('MY_OTHER_SCHEMA', s.role_name())

        class MyThirdSchema(Schema):
            pass

        self.assertEqual('MY_THIRD_SCHEMA', MyThirdSchema.role_name())

        s = MyThirdSchema(self.schema_instance1.vertex, self.kb.database)
        self.assertEqual('MY_THIRD_SCHEMA', s.role_name())

    def test_is_valid(self):
        class MySchema(Schema):
            @validation('message')
            def never_valid(self) -> bool:
                return False

        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        self.assertFalse(s.is_valid)

        class MySchema2(Schema):
            @validation('message')
            def always_valid(self) -> bool:
                return True

        s = MySchema2(self.schema_instance1.vertex, self.kb.database)
        self.assertTrue(s.is_valid)

        class MySchema3(Schema):
            __only_valid_vertex__ = self.schema_instance1.vertex

            @validation('message')
            def sometimes_valid(self) -> bool:
                return self.vertex is self.__only_valid_vertex__

        s1 = MySchema3(self.schema_instance1.vertex, self.kb.database)
        self.assertTrue(s1.is_valid)
        s2 = MySchema3(self.schema_instance2.vertex, self.kb.database)
        self.assertFalse(s2.is_valid)

    def test_get_validation_error(self):
        class MySchema(Schema):
            validator1_return: bool
            validator2_return: bool

            @validation('message1')
            def validator1(self) -> bool:
                return self.validator1_return

            @validation('message2')
            def validator2(self) -> bool:
                return self.validator2_return

        MySchema.validator1_return = MySchema.validator2_return = True
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        self.assertIsNone(s.get_validation_error())

        MySchema.validator1_return = False
        MySchema.validator2_return = True
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        self.assertEqual('message1', s.get_validation_error())

        MySchema.validator1_return = True
        MySchema.validator2_return = False
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        self.assertEqual('message2', s.get_validation_error())

        MySchema.validator1_return = MySchema.validator2_return = False
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        self.assertIsNotNone(s.get_validation_error())

    def test_validate(self):
        class MySchema(Schema):
            validator1_return: bool
            validator2_return: bool

            @validation('message1')
            def validator1(self) -> bool:
                return self.validator1_return

            @validation('message2')
            def validator2(self) -> bool:
                return self.validator2_return

        MySchema.validator1_return = MySchema.validator2_return = True
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        s.validate()

        MySchema.validator1_return = False
        MySchema.validator2_return = True
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        with self.assertRaises(SchemaValidationError):
            s.validate()

        MySchema.validator1_return = True
        MySchema.validator2_return = False
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        with self.assertRaises(SchemaValidationError):
            s.validate()

        MySchema.validator1_return = MySchema.validator2_return = False
        s = MySchema(self.schema_instance1.vertex, self.kb.database)
        with self.assertRaises(SchemaValidationError):
            s.validate()

    def test_has_correct_role(self):
        class MySchema(Schema):
            __role_name__ = 'role'

        good_role = self.kb.database.get_role('role', add=True)
        good_vertex = self.kb.database.add_vertex(good_role)
        s = MySchema(good_vertex, self.kb.database)
        self.assertTrue(s.has_correct_role())

        bad_role = self.kb.database.get_role('another role', add=True)
        bad_vertex = self.kb.database.add_vertex(bad_role)
        s = MySchema(bad_vertex, self.kb.database)
        self.assertFalse(s.has_correct_role())
