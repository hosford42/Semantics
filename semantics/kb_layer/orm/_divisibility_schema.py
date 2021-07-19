import logging

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

from semantics.kb_layer.orm._word_schema import Word

_logger = logging.getLogger(__name__)


@schema_registry.register
class Divisibility(schema.Schema):
    """A divisibility is an attribute determining whether/to what degree an instance or observation
    can be subdivided. These are 'singular' (an indivisible unit), 'plural' (divisible into two or
    more singular components), and 'mass' (a substance, divisible into any number of likewise
    mass-divisible components)."""

    def __repr__(self) -> str:
        name = '<unnamed>'
        name_obj = self.name.get(validate=False)
        if name_obj and name_obj.spelling:
            name = name_obj.spelling
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index), name)

    name = schema.attribute('NAME', Word)
    names = schema.attribute('NAME', Word, plural=True)
