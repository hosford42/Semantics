import logging
import typing

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

from semantics.kb_layer.orm._word_schema import Word


if typing.TYPE_CHECKING:
    from semantics.kb_layer import orm
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


@schema_registry.register
class Kind(schema.Schema):
    """A kind is an abstract type of thing."""

    @schema.validation('{schema} should have at least one name Word.')
    def has_name(self) -> bool:
        """Whether the kind has an associated name. In order for the kind to pass validation, this
        must return True."""
        return self.name.defined

    def __repr__(self) -> str:
        name = '<unnamed>'
        name_obj = self.name.get(validate=False)
        if name_obj and name_obj.spelling:
            name = name_obj.spelling
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index), name)

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)

    instances: 'schema_attributes.PluralAttribute[orm.Instance]'
