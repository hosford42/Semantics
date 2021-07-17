from unittest import TestCase

from semantics.kb_layer.schema import Schema
from semantics.kb_layer.schema_registry import register, get_schema_type


class Test(TestCase):

    def test_register(self):
        class MySchema(Schema):
            pass

        self.assertIsNone(get_schema_type(MySchema.role_name()))
        self.assertEqual(MySchema, register(MySchema))
        self.assertEqual(MySchema, get_schema_type(MySchema.role_name()))

        class MyOtherSchema(Schema):
            __role_name__ = MySchema.role_name()

        with self.assertRaises(KeyError):
            register(MyOtherSchema)

        self.assertEqual(MySchema, get_schema_type(MySchema.role_name()))
