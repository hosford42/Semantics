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

    @property
    def divisible(self) -> bool:
        result = self.vertex.get_data_key('divisible')
        if result is None:
            raise AttributeError("Attribute not set: Divisibility.divisible")
        return result

    @property
    def countable(self) -> bool:
        result = self.vertex.get_data_key('countable')
        if result is None:
            raise AttributeError("Attribute not set: Divisibility.countable")
        return result
