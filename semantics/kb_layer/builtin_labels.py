"""
Automatic creation/lookup and direct access to standardized, built-in labels used by the
knowledge base.
"""

import typing

from semantics.graph_layer import elements

if typing.TYPE_CHECKING:
    import semantics.graph_layer.interface as graph_db_interface


class BuiltinLabels:
    """Simple class to access and ensure the existence of edge labels that are built-in for the
    knowledge base."""

    def __init__(self, db: 'graph_db_interface.GraphDBInterface'):
        self._db = db

        labels_dict: typing.Dict[str, elements.Label] = {}
        for name in dir(type(self)):
            if not name.startswith('_'):
                labels_dict[name] = self._db.get_label(name.upper(), add=True)
        self._labels: typing.Dict[str, elements.Label] = labels_dict

    @property
    def name(self) -> elements.Label:
        """Label to indicate that an edge connects a conceptual element to a word which is one of
        its names."""
        return self._labels['name']
