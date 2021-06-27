import abc
import threading
import typing

import semantics.data_structs.element_data as element_data
import semantics.data_structs.operation_contexts as contexts
import semantics.data_types.allocators as allocators
import semantics.data_types.indices as indices
import semantics.data_types.typedefs as typedefs

PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class DataInterface(metaclass=abc.ABCMeta):

    element_type_map: typing.Mapping[typing.Type[indices.PersistentDataID], typing.Type[element_data.ElementData]] = {
        indices.RoleID: element_data.RoleData,
        indices.VertexID: element_data.VertexData,
        indices.LabelID: element_data.LabelData,
        indices.EdgeID: element_data.EdgeData,
    }

    controller_data: typing.Optional['DataInterface']

    reference_id_allocator: allocators.IndexAllocator[indices.ReferenceID]
    id_allocator_map: typing.Mapping[typing.Type[indices.PersistentDataID], allocators.IndexAllocator]
    name_allocator_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                       allocators.MapAllocator[str, indices.PersistentDataID]]
    vertex_time_stamp_allocator: allocators.MapAllocator[typedefs.TimeStamp, indices.VertexID]
    held_references: typing.MutableSet[indices.ReferenceID]
    held_references_union: typing.AbstractSet[indices.ReferenceID]
    registry_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                 typing.MutableMapping[indices.PersistentDataID, element_data.ElementData]]
    registry_stack_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                       typing.MutableMapping[indices.PersistentDataID, element_data.ElementData]]
    pending_deletion_map: typing.Optional[typing.Mapping[typing.Type[indices.PersistentDataID],
                                                         typing.MutableSet[indices.PersistentDataID]]]
    pending_name_deletion_map: typing.Optional[typing.MutableMapping[typing.Type[indices.PersistentDataID],
                                                                     typing.MutableSet[str]]]
    name_allocator_stack_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                             typing.Mapping[str, indices.PersistentDataID]]

    # Protects object creation, deletion, and reference count changes
    registry_lock: threading.Lock

    def add(self, index_type: typing.Type['PersistentIDType'], *args, **kwargs) \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        return contexts.Addition(self, index_type, *args, **kwargs)

    def read(self, index: 'PersistentIDType') \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        return contexts.Read(self, index)

    def update(self, index: 'PersistentIDType') \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        return contexts.Update(self, index)

    def find(self, index_type: typing.Type['PersistentIDType'], name: str) \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        return contexts.Find(self, index_type, name)

    def remove(self, index: 'PersistentIDType') \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        return contexts.Removal(self, index)

    def get_data(self, index: 'PersistentIDType') -> 'element_data.ElementData[PersistentIDType]':
        if self.pending_deletion_map and index in self.pending_deletion_map[type(index)]:
            raise KeyError(index)
        return self.registry_stack_map[type(index)][index]

    @abc.abstractmethod
    def add_usage(self, index: 'PersistentIDType') -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def remove_usage(self, index: 'PersistentIDType') -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def allocate_name(self, name: str, index: 'PersistentIDType') -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def deallocate_name(self, name: str, index: 'PersistentIDType') -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def allocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID) -> None:
        raise NotImplementedError()

    # @abc.abstractmethod
    # def deallocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID) -> None:
    #     raise NotImplementedError()
