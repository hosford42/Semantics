import typing


_HOOK_REGISTRY: typing.Set[typing.Callable] = set()


def register(callback: typing.Callable) -> typing.Callable:
    """Decorator for hook callbacks to register them at knowledge base initialization."""
    assert getattr(callback, '__module__', None)
    assert getattr(callback, '__qualname__', None)
    assert '__main__' not in getattr(callback, '__module__')
    _HOOK_REGISTRY.add(callback)
    return callback


def iter_hooks() -> typing.Iterator[typing.Callable]:
    yield from _HOOK_REGISTRY
