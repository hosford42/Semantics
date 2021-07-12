import typing

from semantics.kb_layer import orm

if typing.TYPE_CHECKING:
    from semantics.kb_layer import schema
    import semantics.kb_layer.interface as kb_interface


_PATTERN_SCHEMAS = {}


def pattern_schema(schema_type: typing.Type['schema.Schema']) -> typing.Callable:
    """Decorator for builtin patterns to associate schemas with them."""
    def decorator(pattern):
        if isinstance(pattern, property):
            name = pattern.getter.__name__
        else:
            assert callable(pattern)
            name = pattern.__name__
        _PATTERN_SCHEMAS[name] = schema_type
        return pattern
    return decorator


class BuiltinPatterns:
    """Class to access and ensure the existence of contextual patterns that are built-in for the
    knowledge base."""

    def __init__(self, kb: 'kb_interface.KnowledgeBaseInterface'):
        self._kb = kb

        patterns_dict: typing.Dict[str, orm.Pattern] = {}
        for name in dir(type(self)):
            if not name.startswith('_'):
                schema_type = _PATTERN_SCHEMAS.get(name, None)
                pattern = self._kb.add_pattern(schema_type)
                pattern.name.set(kb.get_word(name, add=True))
                patterns_dict[name] = pattern
        self._patterns: typing.Dict[str, orm.Pattern] = patterns_dict

    @property
    @pattern_schema(orm.Time)
    def now(self) -> orm.Pattern:
        return self._patterns['now']
