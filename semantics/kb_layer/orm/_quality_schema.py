import logging
import typing

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry
from semantics.kb_layer.orm._kind_schema import Kind

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


@schema_registry.register
class Quality(schema.Schema):
    """A quality is a feature or attribute of an instance or another quality."""

    def __repr__(self) -> str:
        kind = '<untyped>'
        kind_obj = self.kind.get(validate=False)
        if kind_obj:
            kind_name_obj = kind_obj.name.get(validate=False)
            if kind_name_obj and kind_name_obj.spelling:
                kind = kind_name_obj.spelling
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index), kind)

    kind = schema.attribute('KIND', Kind)
    kinds = schema.attribute('KIND', Kind, plural=True)

    # We don't specify a schema for the attribute because qualities can apply to both instances
    # and other qualities.
    described = schema.attribute('QUALITY', outbound=False, plural=False)

    # A quality can itself have qualities. (In linguistic terms, these are adverbs.)
    qualities: 'schema_attributes.PluralAttribute[Quality]'
