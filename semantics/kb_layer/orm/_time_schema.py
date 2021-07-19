import logging
import typing

from semantics.data_types import typedefs
from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

if typing.TYPE_CHECKING:
    from semantics.kb_layer import orm
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


@schema_registry.register
class Time(schema.Schema):
    """A time can represent a specific point in type if it has a time stamp, or else an abstract
    point or span of time if it has no time stamp."""

    def __repr__(self) -> str:
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index),
                                self.time_stamp or '<unstamped>')

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        """The time stamp, if any, associated with this time."""
        return self._vertex.time_stamp

    later_times: 'schema_attributes.PluralAttribute[Time]'
    earlier_times: 'schema_attributes.PluralAttribute[Time]'
    observations: 'schema_attributes.PluralAttribute[orm.Instance]'

    def precedes(self, other: 'Time') -> bool:
        precedes_label = self.database.get_label('PRECEDES')
        assert precedes_label
        return self.vertex in other.vertex.iter_transitive_sources(precedes_label)
