"""
Automatic creation/lookup and direct access to standardized, built-in roles used by the
knowledge base.
"""

import typing

import semantics.graph_layer.elements as elements

if typing.TYPE_CHECKING:
    import semantics.graph_layer.interface as graph_db_interface


class BuiltinRoles:
    """Simple class to access and ensure the existence of vertex roles that are built-in for the
    knowledge base."""

    def __init__(self, db: 'graph_db_interface.GraphDBInterface'):
        self._db = db

        roles_dict: typing.Dict[str, elements.Role] = {}
        for name in dir(type(self)):
            if not name.startswith('_') and name != 'kb':
                roles_dict[name] = self._db.get_role(name.upper(), add=True)
        self._roles: typing.Dict[str, elements.Role] = roles_dict

    @property
    def word(self) -> elements.Role:
        """Role to indicate that a vertex represents a word, apart from its meaning."""
        return self._roles['WORD']

    @property
    def kind(self) -> elements.Role:
        """Role to indicate that a vertex represents a kind, type, or class."""
        return self._roles['KIND']

    @property
    def instance(self) -> elements.Role:
        """Role to indicate that a vertex represents an particular instance of a kind, type, or
        class."""
        return self._roles['INSTANCE']

    @property
    def time(self) -> elements.Role:
        """Role to indicate that a vertex represents a time."""
        return self._roles['TIME']

    @property
    def manifestation(self) -> elements.Role:
        """Role to indicate that a vertex represents a manifestation or observation of an
        instance. Instances can have different states and attributes, evolving over time. A
        manifestation serves to tie the instance, state, and time at which the instance has that
        state together at a single locus."""
        return self._roles['MANIFESTATION']
