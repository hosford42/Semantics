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
    """Abstract base class for database data container classes."""

    element_type_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                     typing.Type[element_data.ElementData]] = {
        indices.RoleID: element_data.RoleData,
        indices.VertexID: element_data.VertexData,
        indices.LabelID: element_data.LabelData,
        indices.EdgeID: element_data.EdgeData,
    }

    controller_data: typing.Optional['DataInterface']

    reference_id_allocator: allocators.IndexAllocator[indices.ReferenceID]
    id_allocator_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                     allocators.IndexAllocator]
    name_allocator_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                       allocators.MapAllocator[str, indices.PersistentDataID]]
    vertex_time_stamp_allocator: allocators.MapAllocator[typedefs.TimeStamp, indices.VertexID]
    held_references: typing.MutableSet[indices.ReferenceID]
    held_references_union: typing.AbstractSet[indices.ReferenceID]
    registry_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                 typing.MutableMapping[indices.PersistentDataID,
                                                       element_data.ElementData]]
    registry_stack_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                       typing.MutableMapping[indices.PersistentDataID,
                                                             element_data.ElementData]]
    pending_deletion_map: typing.Optional[
        typing.Mapping[typing.Type[indices.PersistentDataID],
                       typing.MutableSet[indices.PersistentDataID]]
    ]
    pending_name_deletion_map: typing.Optional[
        typing.MutableMapping[typing.Type[indices.PersistentDataID],
                              typing.MutableSet[str]]
    ]
    name_allocator_stack_map: typing.Mapping[typing.Type[indices.PersistentDataID],
                                             typing.Mapping[str, indices.PersistentDataID]]

    # Protects object creation, deletion, and reference count changes
    registry_lock: threading.Lock

    def add(self, index_type: typing.Type['PersistentIDType'], *args, **kwargs) \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        """A context manager which adds a new element of the given type if no
        exceptions occur in the `with` body.

        Note: Do not hold the registry lock while calling this method.

        Usage:
            with data.add(VertexID) as element_data:
                assert isinstance(element_data, VertexData)
                # Perform validation and/or do things to the element data before
                # it is added to the database. If an exception is raised here,
                # the element won't be added.
        """
        return contexts.Addition(self, index_type, *args, **kwargs)

    def read(self, index: 'PersistentIDType') \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        """A context manager which provides read access to a data element and revokes
        it upon exiting the `with` block.

        Note: Do not hold the registry lock while calling this method.

        Usage:
            with data.read(element_id) as element_data:
                # A read lock to the data element is held for the duration of this
                # block. Access the data element, but do not modify it.
        """
        return contexts.Read(self, index)

    def update(self, index: 'PersistentIDType') \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        """A context manager which provides update (modify) access to a data element
        and revokes it upon exiting the `with` block. Raising an exception cancels
        the update.

        Note: Do not hold the registry lock while calling this method.

        Usage:
            with data.update(element_id) as element_data:
                # A write lock to the data element is held for the duration of this
                # block. Access or update the element freely. If no exception is
                # raised, the changes will be applied. Otherwise, they will be
                # rolled back.
        """
        return contexts.Update(self, index)

    def find(self, index_type: typing.Type['PersistentIDType'], name: str) \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        """A context manager which provides read access to a data element and revokes
        it upon exiting the `with` block.

        Note: Do not hold the registry lock while calling this method.

        Usage:
            with data.find(RoleID, "role_name") as element_data:
                assert element_data is None or isinstance(element_data, RoleData)
                # If element_data is not None, a read lock to the data element is held
                # for the duration of this block. Access the data element, but do not
                # modify it.
        """
        return contexts.Find(self, index_type, name)

    def remove(self, index: 'PersistentIDType') \
            -> 'typing.ContextManager[element_data.ElementData[PersistentIDType]]':
        """A context manager which removes an element of the given type if no
        exceptions occur in the `with` body.

        Note: Do not hold the registry lock while calling this method.

        Usage:
            with data.update(element_id) as element_data:
                # A write lock to the data element is held for the duration of this
                # block. Access or update the element freely. If no exception is
                # raised, the element will be deleted. Otherwise, the changes will be
                # rolled back.
        """
        return contexts.Removal(self, index)

    def get_data(self, index: 'PersistentIDType') -> 'element_data.ElementData[PersistentIDType]':
        """Return the element data associated with the given index. Raise a KeyError if
        no data is associated with the index.

        Note: The registry lock must be held while calling this method.
        """
        assert self.registry_lock.locked()
        if self.pending_deletion_map and index in self.pending_deletion_map[type(index)]:
            raise KeyError(index)
        return self.registry_stack_map[type(index)][index]

    def iter_all(self, index_type: typing.Type['PersistentIDType']) \
            -> typing.Iterator['PersistentIDType']:
        """Return an iterator over all existing elements indices of the given type.

        Note: The registry lock must be held while calling this method.

        WARNING: This is an expensive operation that requires traversing a large
        portion of the database while holding the registry lock. Do not use it
        for trivial purposes!"""
        # Do a basic check to make sure the method isn't being abused.
        # (The caller can still mistakenly drop the lock during iteration.)
        assert self.registry_lock.locked()
        if self.pending_deletion_map:
            pending_deletions = self.pending_deletion_map[index_type]
            yield from (self.registry_map[index_type].keys() |
                        self.controller_data.registry_map[index_type].keys()) - pending_deletions
        else:
            yield from self.registry_map[index_type]

    def is_in_use(self, index: 'PersistentIDType') -> bool:
        """Check if there are any references to the element from other elements.

        Note: The registry lock must be held while calling this method.

        WARNING: This is an expensive operation that requires traversing a large
        portion of the database while holding the registry lock. Do not use it
        for trivial purposes!"""
        if type(index) is indices.RoleID:
            for referring_index in self.iter_all(indices.VertexID):
                referring_data = self.get_data(referring_index)
                assert isinstance(referring_data, element_data.VertexData)
                if referring_data.preferred_role == index:
                    return True
            return False
        elif type(index) is indices.LabelID:
            for referring_index in self.iter_all(indices.EdgeID):
                referring_data = self.get_data(referring_index)
                assert isinstance(referring_data, element_data.EdgeData)
                if referring_data.label == index:
                    return True
            return False
        else:
            # We never hold persistent references from other elements to vertices or edges.
            return False

    @abc.abstractmethod
    def allocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Assign a name to an index."""
        raise NotImplementedError()

    @abc.abstractmethod
    def deallocate_name(self, name: str, index: 'PersistentIDType') -> None:
        """Remove a name/index assignment."""
        raise NotImplementedError()

    @abc.abstractmethod
    def allocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID) \
            -> None:
        """Assign a time stamp to a vertex index."""
        raise NotImplementedError()

    # @abc.abstractmethod
    # def deallocate_time_stamp(self, time_stamp: typedefs.TimeStamp, vertex_id: indices.VertexID)
    #         -> None:
    #     raise NotImplementedError()
