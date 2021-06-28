import typing


# Can't use NewType because it can't be pickled.
class TimeStamp(float):
    pass


SimpleDataType = typing.NewType('SimpleDataType', typing.Union[None, bool, int, float, str])


# Can't use NewType because it can't be pickled.
class DataDict(typing.Dict[str, SimpleDataType], dict):
    pass
