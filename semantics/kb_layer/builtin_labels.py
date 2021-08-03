"""
Automatic creation/lookup and direct access to standardized, built-in labels used by the
knowledge base.
"""

import typing

from semantics.graph_layer import elements

if typing.TYPE_CHECKING:
    import semantics.graph_layer.interface as graph_db_interface


TRANSITIVE_LABEL_NAMES = frozenset([
    'PRECEDES',
])


class BuiltinLabels:
    """Simple class to access and ensure the existence of edge labels that are built-in for the
    knowledge base."""

    def __init__(self, db: 'graph_db_interface.GraphDBInterface'):
        self._db = db

        labels_dict: typing.Dict[str, elements.Label] = {}
        for name in dir(type(self)):
            if not name.startswith('_'):
                name = name.upper()
                labels_dict[name] = self._db.get_label(name, add=True,
                                                       transitive=name in TRANSITIVE_LABEL_NAMES)
        self._labels: typing.Dict[str, elements.Label] = labels_dict

    @property
    def name(self) -> elements.Label:
        """The edge connects a conceptual element to a word which is one of its names."""
        return self._labels['NAME']

    @property
    def kind(self) -> elements.Label:
        """The edge connects an instance to the kind to which it belongs."""
        return self._labels['KIND']

    @property
    def instance(self) -> elements.Label:
        """The edge connects an observation to the instance observed."""
        return self._labels['INSTANCE']

    @property
    def time(self) -> elements.Label:
        """The edge connects an observation to the time at which it was made."""
        return self._labels['TIME']

    @property
    def precedes(self) -> elements.Label:
        """The edge connects two times, with the earlier of the two as the source and the later of
        the two as the sink."""
        return self._labels['PRECEDES']

    @property
    def less_than(self) -> elements.Label:
        """The edge connects two numbers, with the smaller of the two as the source and the larger
        of the two as the sink."""
        return self._labels['LESS_THAN']

    @property
    def match_representative(self) -> elements.Label:
        """The edge connects a selector to its match representative observation."""
        return self._labels['MATCH_REPRESENTATIVE']

    @property
    def divisibility(self) -> elements.Label:
        """The edge connects an instance or observation to its divisibility."""
        return self._labels['DIVISIBILITY']

    @property
    def selector(self) -> elements.Label:
        """The edge connects a pattern to a selector pattern."""
        return self._labels['SELECTOR']

    @property
    def preimage(self) -> elements.Label:
        """The edge connects a pattern match to the pattern that was matched."""
        return self._labels['PREIMAGE']

    @property
    def image(self) -> elements.Label:
        """The edge connects a pattern match to the vertex the pattern matched against."""
        return self._labels['IMAGE']

    @property
    def template(self) -> elements.Label:
        """The edge connects a cloned pattern to its template."""
        return self._labels['TEMPLATE']

    @property
    def child(self) -> elements.Label:
        """The edge connects a pattern to a child pattern."""
        return self._labels['CHILD']

    @property
    def actor(self) -> elements.Label:
        """The edge connects an event instance to its actor instance."""
        return self._labels['ACTOR']

    @property
    def condition(self) -> elements.Label:
        """The edge connects a trigger to the pattern it is conditioned upon."""
        return self._labels['CONDITION']

    @property
    def action(self) -> elements.Label:
        """The edge connects a trigger to the action it performs."""
        return self._labels['ACTION']

    @property
    def trigger(self) -> elements.Label:
        """The edge connects any non-pattern vertex to a trigger associated with it."""
        return self._labels['TRIGGER']

    @property
    def quality(self) -> elements.Label:
        """The edge connects an instance or quality to a quality that describes it."""
        return self._labels['QUALITY']
