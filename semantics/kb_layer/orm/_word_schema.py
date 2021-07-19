import logging
import typing

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

if typing.TYPE_CHECKING:
    from semantics.kb_layer import orm
    from semantics.kb_layer import schema_attributes


_logger = logging.getLogger(__name__)


@schema_registry.register
class Word(schema.Schema):
    """A word is a sequence of characters, independent of their meaning."""

    def __repr__(self) -> str:
        name = self.vertex.name or '<unnamed>'
        return '<%s#%s(%s)>' % (type(self).__name__, int(self._vertex.index), name)

    @schema.validation('{schema} must have an associated spelling attribute.')
    def has_spelling(self) -> bool:
        """Whether the word has an associated spelling. In order for the word to pass validation,
        this must return True."""
        return self._vertex.name is not None

    @property
    def spelling(self) -> typing.Optional[str]:
        """The spelling, if any, associated with this word."""
        return self._vertex.name

    kind: 'schema_attributes.SingularAttribute[orm.Kind]'
    kinds: 'schema_attributes.PluralAttribute[orm.Kind]'
    selector: 'schema_attributes.SingularAttribute[orm.Pattern]'
    selectors: 'schema_attributes.PluralAttribute[orm.Pattern]'
    divisibility: 'schema_attributes.SingularAttribute[orm.Divisibility]'
    divisibilities: 'schema_attributes.PluralAttribute[orm.Divisibility]'