"""
Protocol for comparable types.
"""

import abc
import typing


# Pylint complains that there is only one method, but it's literally all we need the protocol for.
# pylint: disable=R0903
class Comparable(typing.Protocol):
    """Abstract protocol for types that can be compared to themselves with the less-than
    operator, i.e., types that can be sorted. This is only used for type annotations."""

    @abc.abstractmethod
    def __lt__(self: 'ComparableType', other: 'ComparableType') -> bool:
        ...


ComparableType = typing.TypeVar('ComparableType', bound=Comparable)
