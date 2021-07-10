"""
Automatic creation/lookup and direct access to standardized, built-in roles used by the
knowledge base.
"""

import typing

from semantics.graph_layer import elements

if typing.TYPE_CHECKING:
    import semantics.graph_layer.interface as graph_db_interface


class BuiltinRoles:
    """Simple class to access and ensure the existence of vertex roles that are built-in for the
    knowledge base."""

    def __init__(self, db: 'graph_db_interface.GraphDBInterface'):
        self._db = db

        roles_dict: typing.Dict[str, elements.Role] = {}
        for name in dir(type(self)):
            if not name.startswith('_'):
                name = name.upper()
                roles_dict[name] = self._db.get_role(name, add=True)
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
    def observation(self) -> elements.Role:
        """Role to indicate that a vertex represents a manifestation or observation of an
        instance. Instances can have different states and attributes, evolving over time. An
        observation serves to tie the instance, state, and time at which the instance has that
        state together at a single locus."""
        return self._roles['OBSERVATION']

    @property
    def pattern(self) -> elements.Role:
        """Role to indicate that a vertex represents a pattern. A pattern represents a structure
        to be found elsewhere in the knowledge graph, together with an ordering relation which
        determines how to search the knowledge graph for matches, and information about which
        matches to prefer and when to stop searching."""
        return self._roles['PATTERN']

    @property
    def divisibility(self) -> elements.Role:
        """Role to indicate that a vertex represents a divisibility. A divisibility is an indicator
        of whether/to what extent an instance or observation can be subdivided. Examples from
        natural language include 'singular', 'plural', and 'mass'."""
        return self._roles['DIVISIBILITY']
