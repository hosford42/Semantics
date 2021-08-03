import logging
import typing

from semantics.graph_layer import elements
from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry
from semantics.kb_layer.orm._time_schema import Time

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


MAGIC_COMPARISON_METHOD_NAMES = ('__eq__', '__ne__', '__lt__', '__gt__', '__le__', '__ge__')


@schema_registry.register
class Number(schema.Schema):
    """A number is a comparable quantity."""

    def __repr__(self) -> str:
        return '<%s#%s(%r)>' % (type(self).__name__, int(self._vertex.index), self.value)

    lesser_values: 'schema_attributes.PluralAttribute[Time]'
    greater_values: 'schema_attributes.PluralAttribute[Time]'

    @property
    def value(self) -> typing.Optional[typing.Any]:
        return self.vertex.get_data_key('value', None)

    greater_values: 'schema_attributes.PluralAttribute[Time]'
    lesser_values: 'schema_attributes.PluralAttribute[Time]'

    # TODO: Can we generalize some of this code and move it into Vertex? Maybe
    #       search_transitive_sources() and search_transitive_sinks() methods? They would need to
    #       take not only an optional 'skip' condition, but also a required 'stop' condition. It
    #       might be good to have a breadth-first vs. depth-first option, too.
    def __lt__(self, other: 'Number') -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        if self.vertex == other.vertex:
            return False
        if not (self.is_valid and other.is_valid):
            return False
        my_value = self.value
        other_value = other.value
        # We can immediately know the answer if both vertices have data values associated, by
        # simply comparing them directly.
        if my_value is not None and other_value is not None:
            try:
                return my_value < other_value
            except TypeError:
                return False
        less_than_label = self.database.get_label('LESS_THAN')
        assert less_than_label
        if my_value is not None:
            # Search backward from the other instance until we find this vertex or a vertex with a
            # comparable data value that is greater than this one's.
            def skip_condition(edge: elements.Edge) -> bool:
                vertex_value = edge.source.get_data_key('value', None)
                try:
                    return vertex_value is not None and vertex_value < my_value
                except TypeError:
                    return True
            iterator = other.vertex.iter_transitive_sources(less_than_label, skip=skip_condition)
            for vertex in iterator:
                if vertex == self.vertex:
                    return True
                vertex_value = vertex.get_data_key('value', None)
                try:
                    if vertex_value is not None and my_value < vertex_value:
                        return True
                except TypeError:
                    pass
            return False
        elif other_value is not None:
            # Search forward from this instance until we find the other vertex or a vertex with a
            # comparable data value that is less than the other one's.
            def skip_condition(edge: elements.Edge) -> bool:
                vertex_value = edge.sink.get_data_key('value', None)
                try:
                    return vertex_value is not None and vertex_value > other_value
                except TypeError:
                    return True
            iterator = self.vertex.iter_transitive_sinks(less_than_label, skip=skip_condition)
            for vertex in iterator:
                if vertex == other.vertex:
                    return True
                vertex_value = vertex.get_data_key('value', None)
                try:
                    if vertex_value is not None and vertex_value < other_value:
                        return True
                except TypeError:
                    pass
            return False
        else:
            # If we don't know the data value associated with either vertex, there's no shortcut
            # to be taken; we have to just run the search. Ideally, we won't have a ton of vertices
            # that are highly interconnected and far from the main backbone of vertices that have
            # data values associated with them. Otherwise, this could turn into a long search.
            return self.vertex in other.vertex.iter_transitive_sources(less_than_label)

    def __gt__(self, other: 'Number') -> bool:
        return other.__lt__(self)

    def __le__(self, other: 'Number') -> bool:
        return self == other or self.__lt__(other)

    def __ge__(self, other: 'Number') -> bool:
        return self == other or other.__lt__(self)
