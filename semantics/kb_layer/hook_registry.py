import typing


_HOOK_REGISTRY: typing.Set[typing.Callable] = set()


def register(callback: typing.Callable) -> typing.Callable:
    """Decorator for hook callbacks to register them at knowledge base initialization."""
    if not (getattr(callback, '__module__', None) and getattr(callback, '__qualname__', None)):
        raise ValueError(callback)
    if ('__main__' in getattr(callback, '__module__') or
            '<locals>' in getattr(callback, '__qualname__')):
        raise ValueError(callback)
    _HOOK_REGISTRY.add(callback)
    return callback


def iter_hooks() -> typing.Iterator[typing.Callable]:
    yield from _HOOK_REGISTRY
