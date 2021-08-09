import logging
import typing

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry
from semantics.kb_layer.orm._divisibility_schema import Divisibility
from semantics.kb_layer.orm._kind_schema import Kind
from semantics.kb_layer.orm._quality_schema import Quality
from semantics.kb_layer.orm._time_schema import Time
from semantics.kb_layer.orm._word_schema import Word

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


@schema_registry.register
class Instance(schema.Schema):
    """An instance is a particular thing."""

    def __repr__(self) -> str:
        name = '<unnamed>'
        name_obj = self.name.get(validate=False)
        if name_obj and name_obj.spelling:
            name = name_obj.spelling
        kind = '<untyped>'
        kind_obj = self.kind.get(validate=False)
        if kind_obj:
            kind_name_obj = kind_obj.name.get(validate=False)
            if kind_name_obj and kind_name_obj.spelling:
                kind = kind_name_obj.spelling
        return '<%s#%s(%s,%s)>' % (type(self).__name__, int(self._vertex.index), name, kind)

    # Individual instances can be named just like kinds, but usually aren't.
    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    kind = schema.attribute('KIND', Kind)
    kinds = schema.attribute('KIND', Kind, plural=True)

    time = schema.attribute('TIME', Time)
    times = schema.attribute('TIME', Time, plural=True)

    divisibility = schema.attribute('DIVISIBILITY', Divisibility)
    qualities = schema.attribute('QUALITY', Quality, plural=True)

    instance: 'schema_attributes.SingularAttribute[Instance]'
    instances: 'schema_attributes.PluralAttribute[Instance]'
    observations: 'schema_attributes.PluralAttribute[Instance]'
