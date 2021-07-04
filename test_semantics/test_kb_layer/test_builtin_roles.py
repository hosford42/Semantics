from unittest import TestCase

from semantics.graph_layer.elements import Role
from semantics.graph_layer.graph_db import GraphDB
from semantics.kb_layer.builtin_roles import BuiltinRoles


class TestBuiltinRoles(TestCase):

    def test_attributes(self):
        db = GraphDB()
        another_role = db.get_role('another_role', add=True)
        roles = BuiltinRoles(db)
        for name in dir(roles):
            if name.startswith('_'):
                continue
            self.assertEqual(name, name.lower())
            role = getattr(roles, name)
            self.assertIsInstance(role, Role)
            self.assertEqual(name, role.name.lower())
            self.assertEqual(role.name, name.upper())
            with self.assertRaises(AttributeError):
                setattr(roles, name, another_role)
