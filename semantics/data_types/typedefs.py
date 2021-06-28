"""
Basic type definitions.
"""

import typing


# Can't use NewType because it can't be pickled.
class TimeStamp(float):
    """Time stamp values used in element data."""


SimpleDataType = typing.NewType('SimpleDataType', typing.Union[None, bool, int, float, str])


# Can't use NewType because it can't be pickled.
class DataDict(typing.Dict[str, SimpleDataType], dict):
    """Mapping used for key/value pairs in element data."""
