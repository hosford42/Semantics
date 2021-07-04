"""
Data structures associated with each type of graph element.
"""

import typing

import semantics.data_types.indices as indices
import semantics.data_types.typedefs as typedefs

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)
Self = typing.TypeVar('Self')


class ElementData(typing.Generic[PersistentIDType]):
    """Base class for graph element internal data types."""

    def __init__(self, index: PersistentIDType, *_args, **_kwargs):
        # Uniquely identifies the element, given its element type:
        self._index = index
        self._data = typedefs.DataDict({})

    @property
    def index(self) -> PersistentIDType:
        """The index of the element."""
        return self._index

    @property
    def data(self) -> typedefs.DataDict:
        """The key/value pairs associated with the element."""
        return self._data

    def transaction_copy(self: Self) -> Self:
        """Return a transaction-level copy of the data"""

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_data'] = state['_data'].copy()
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)


class NameableElementData(typing.Generic[PersistentIDType], ElementData[PersistentIDType]):
    """Base class for element data for elements that can have names associated with them."""

    def __init__(self, index: PersistentIDType, name: typing.Optional[str]):
        super().__init__(index)
        self._name = name

    @property
    def name(self) -> typing.Optional[str]:
        """The name associated with the element, if any."""
        return self._name


class RoleData(NameableElementData[indices.RoleID]):
    """Internal data for roles."""

    def __init__(self, index: indices.RoleID, name: str):
        super().__init__(index, name)

    @property
    def name(self) -> str:
        """The name associated with the role."""
        return self._name


class VertexData(NameableElementData[indices.VertexID]):
    """Internal data for vertices."""

    def __init__(self, index: indices.VertexID, preferred_role: 'indices.RoleID', name: str = None,
                 time_stamp: typedefs.TimeStamp = None):
        super().__init__(index, name)
        self._preferred_role = preferred_role
        self._time_stamp = time_stamp

        # These can't be controlled with simple context managers, so we leave it to the caller to do
        # the right thing. We already trust them to be holding the registry lock. We're just doing
        # less legwork on their behalf.
        self._inbound = set()
        self._outbound = set()

    @property
    def preferred_role(self) -> 'indices.RoleID':
        """The role of the vertex."""
        return self._preferred_role

    @property
    def name(self) -> typing.Optional[str]:
        """The name associated with the vertex, if any."""
        return self._name

    @name.setter
    def name(self, value: typing.Optional[str]):
        """The name associated with the vertex, if any."""
        self._name = value

    @property
    def time_stamp(self) -> typing.Optional[typedefs.TimeStamp]:
        """The time stamp associated with the vertex, if any."""
        return self._time_stamp

    @time_stamp.setter
    def time_stamp(self, value: typing.Optional[typedefs.TimeStamp]):
        """The time stamp associated with the vertex, if any."""
        self._time_stamp = value

    @property
    def outbound(self) -> typing.Set['indices.EdgeID']:
        """The outbound edges from the vertex."""
        return self._outbound

    @property
    def inbound(self) -> typing.Set['indices.EdgeID']:
        """The inbound edges to the vertex."""
        return self._inbound

    def __getstate__(self):
        state = super().__getstate__()
        state['_inbound'] = state['_inbound'].copy()
        state['_outbound'] = state['_outbound'].copy()
        return state


class LabelData(NameableElementData[indices.LabelID]):
    """Internal data for labels."""

    def __init__(self, index: indices.LabelID, name: str):
        super().__init__(index, name)

    @property
    def name(self) -> str:
        """The name associated with the label."""
        return self._name


class EdgeData(ElementData[indices.EdgeID]):
    """Internal data for edges."""

    def __init__(self, index: indices.EdgeID, label: 'indices.LabelID', source: 'indices.VertexID',
                 sink: 'indices.VertexID'):
        super().__init__(index)
        self._label = label
        self._source = source
        self._sink = sink

    @property
    def label(self) -> 'indices.LabelID':
        """The label associated with the edge."""
        return self._label

    @property
    def source(self) -> 'indices.VertexID':
        """The source (origin) vertex of the edge."""
        return self._source

    @property
    def sink(self) -> 'indices.VertexID':
        """The sink (destination) vertex of the edge."""
        return self._sink
