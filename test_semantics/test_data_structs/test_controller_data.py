import pickle
from unittest import TestCase

from semantics.data_structs.controller_data import ControllerData
from semantics.data_types.indices import RoleID, VertexID, LabelID, EdgeID
from semantics.data_types.typedefs import TimeStamp


class TestControllerData(TestCase):

    def setUp(self) -> None:
        self.data = ControllerData()

    def test_pickle_protocol(self):
        with self.data.add(RoleID, "role") as role_data:
            role_id = role_data.index
            self.data.name_allocator_map[RoleID].allocate('role', role_id)
        with self.data.add(VertexID, role_id) as source_data:
            source_id = source_data.index
            source_data.name = 'source'
            self.data.name_allocator_map[VertexID].allocate('source', source_id)
            source_data.time_stamp = TimeStamp(3.14159)
            self.data.vertex_time_stamp_allocator.allocate(TimeStamp(3.14159), source_id)
        with self.data.add(VertexID, role_id) as sink_data:
            sink_id = sink_data.index
            self.data.name_allocator_map[VertexID].allocate('sink', sink_id)
        with self.data.add(LabelID, "label") as label_data:
            label_id = label_data.index
            self.data.name_allocator_map[LabelID].allocate('label', label_id)
        with self.data.add(EdgeID, label_id, source_id, sink_id) as edge_data:
            pass
        self.data.held_references.add(self.data.reference_id_allocator.new_id())
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
        self.assertEqual(self.data.vertex_time_stamp_allocator.items(),
                         restored.vertex_time_stamp_allocator.items())
        self.assertEqual(restored.held_references, set())
        self.assertFalse(restored.registry_lock.locked())

    def test_allocate_name(self):
        self.data.allocate_name('name', VertexID(100))
        self.assertEqual(self.data.name_allocator_map[VertexID]['name'], VertexID(100))

    def test_deallocate_name(self):
        self.data.allocate_name('name', VertexID(100))
        with self.assertRaises(AssertionError):
            self.data.deallocate_name('name', VertexID(1000))
        with self.assertRaises(AssertionError):
            self.data.deallocate_name('another name', VertexID(100))
        self.data.deallocate_name('name', VertexID(100))
        self.assertIsNone(self.data.name_allocator_map[VertexID].get('name'))

    def test_allocate_time_stamp(self):
        self.data.allocate_time_stamp(TimeStamp(3.14159), VertexID(100))
        self.assertEqual(self.data.vertex_time_stamp_allocator[TimeStamp(3.14159)], VertexID(100))
