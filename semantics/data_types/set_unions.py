"""
Set unions as a datatype.
"""
import typing


ValueType = typing.TypeVar('ValueType', bound=typing.Hashable)


class SetUnion(typing.AbstractSet[ValueType]):
    """A datatype for treating the dynamic computation of the union of two or more sets as
    a set in its own right.

    Usage:
        >>> a = {1, 2}
        >>> b = {2, 3}
        >>> u = SetUnion(a, b)
        >>> sorted(u)
        [1, 2, 3]
        >>> b.add(4)
        >>> sorted(u)
        [1, 2, 3, 4]
        >>>
    """

    def __init__(self, *subsets: typing.AbstractSet[ValueType]):
        self._subsets = subsets

    def __contains__(self, value: object) -> bool:
        return any(value in subset for subset in self._subsets)

    def __len__(self) -> int:
        return len(set.union(*self._subsets))

    def __iter__(self) -> typing.Iterator[ValueType]:
        return iter(set.union(*self._subsets))
