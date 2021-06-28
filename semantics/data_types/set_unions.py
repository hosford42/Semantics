import typing


ValueType = typing.TypeVar('ValueType', bound=typing.Hashable)


class SetUnion(typing.AbstractSet[ValueType]):

    def __init__(self, *subsets: typing.AbstractSet[ValueType]):
        self._subsets = subsets

    def __contains__(self, value: object) -> bool:
        return any(value in subset for subset in self._subsets)

    def __len__(self) -> int:
        return len(set.union(*self._subsets))

    def __iter__(self) -> typing.Iterator[ValueType]:
        return iter(set.union(*self._subsets))
