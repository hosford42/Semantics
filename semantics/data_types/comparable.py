import abc
import typing


class Comparable(typing.Protocol):

    @abc.abstractmethod
    def __lt__(self: 'ComparableType', other: 'ComparableType') -> bool:
        ...


ComparableType = typing.TypeVar('ComparableType', bound=Comparable)
