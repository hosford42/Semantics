import pickle
from unittest import TestCase

from semantics.data_types import allocators

from semantics.data_structs.controller_data import ControllerData
from semantics.data_types.indices import RoleID, VertexID, LabelID, EdgeID, CatalogID
from semantics.data_types.typedefs import TimeStamp
from test_semantics.test_data_structs import base as base


class TestControllerData(TestCase):

    def setUp(self) -> None:
        self.data = ControllerData()

    def test_pickle_protocol(self):
        with self.data.add(RoleID, "role") as role_data:
            role_id = role_data.index
            self.data.name_allocator_map[RoleID].allocate('role', role_id)
        with self.data.add(CatalogID, 'name_catalog', str, ordered=False) as catalog_data:
            name_catalog_id = catalog_data.index
            self.data.name_allocator_map[CatalogID].allocate('name_catalog', name_catalog_id)
            self.data.catalog_allocator_map[name_catalog_id] = \
                allocators.MapAllocator(str, VertexID)
        with self.data.add(CatalogID, 'time_stamp_catalog', TimeStamp,
                           ordered=True) as catalog_data:
            time_stamp_catalog_id = catalog_data.index
            self.data.name_allocator_map[CatalogID].allocate('time_stamp_catalog',
                                                             time_stamp_catalog_id)
            self.data.catalog_allocator_map[time_stamp_catalog_id] = \
                allocators.MapAllocator(TimeStamp, VertexID)
        with self.data.add(VertexID, role_id) as source_data:
            source_id = source_data.index
            self.data.catalog_allocator_map[name_catalog_id].allocate('source', source_id)
            self.data.catalog_allocator_map[time_stamp_catalog_id].allocate(TimeStamp(3.14159),
                                                                            source_id)
        with self.data.add(VertexID, role_id) as sink_data:
            sink_id = sink_data.index
            self.data.catalog_allocator_map[name_catalog_id].allocate('sink', sink_id)
        with self.data.add(LabelID, "label") as label_data:
            label_id = label_data.index
            self.data.name_allocator_map[LabelID].allocate('label', label_id)
        with self.data.add(EdgeID, label_id, source_id, sink_id) as _edge_data:
            pass
        self.data.held_references[self.data.reference_id_allocator.new_id()] = label_id
        self.data.registry_lock.acquire()
        pickled = pickle.dumps(self.data, pickle.HIGHEST_PROTOCOL)
        restored = pickle.loads(pickled)
        self.assertIsInstance(restored, ControllerData)
        self.assertEqual(self.data.reference_id_allocator.total_allocated,
                         restored.reference_id_allocator.total_allocated)
        for index_type, id_allocator in self.data.id_allocator_map.items():
            self.assertEqual(id_allocator.total_allocated,
                             restored.id_allocator_map[index_type].total_allocated)
        for index_type, name_allocator in self.data.name_allocator_map.items():
            self.assertEqual(name_allocator.items(),
                             restored.name_allocator_map[index_type].items())
        for index_type, registry in self.data.registry_map.items():
            self.assertEqual(registry.keys(), restored.registry_map[index_type].keys())
        self.assertEqual(self.data.catalog_allocator_map.keys(),
                         restored.catalog_allocator_map.keys())
        for catalog_id, allocator in self.data.catalog_allocator_map.items():
            restored_allocator = restored.catalog_allocator_map[catalog_id]
            self.assertIs(type(allocator), type(restored_allocator))
            self.assertEqual(allocator.items(), restored_allocator.items())
        self.assertEqual(restored.held_references, {})
        self.assertFalse(restored.registry_lock.locked())

    def test_allocate_name(self):
        self.data.allocate_name('name', RoleID(100))
        self.assertEqual(self.data.name_allocator_map[RoleID]['name'], RoleID(100))

    def test_deallocate_name(self):
        self.data.allocate_name('name', RoleID(100))
        with self.assertRaises(AssertionError):
            self.data.deallocate_name('name', RoleID(1000))
        with self.assertRaises(AssertionError):
            self.data.deallocate_name('another name', RoleID(100))
        self.data.deallocate_name('name', RoleID(100))
        with self.data.find(RoleID, 'name') as data:
            self.assertIsNone(data)


class TestDataInterfaceForControllerData(base.DataInterfaceTestCase):

    data_interface_subclass = ControllerData

    def test_add(self):
        super().test_add()

    def test_read(self):
        super().test_read()

    def test_update(self):
        super().test_update()

    def test_find(self):
        super().test_find()

    def test_remove(self):
        super().test_remove()

    def test_get_data(self):
        super().test_get_data()
