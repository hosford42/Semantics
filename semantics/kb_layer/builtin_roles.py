import typing

import semantics.graph_layer.elements as elements
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
        return self._roles['WORD']

    @property
    def kind(self) -> elements.Role:
        return self._roles['KIND']

    @property
    def instance(self) -> elements.Role:
        return self._roles['INSTANCE']

    @property
    def time(self) -> elements.Role:
        return self._roles['TIME']

    @property
    def manifestation(self) -> elements.Role:
        return self._roles['MANIFESTATION']
