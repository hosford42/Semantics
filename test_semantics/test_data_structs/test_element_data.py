import copy
from unittest import TestCase

from semantics.data_structs.element_data import RoleData, VertexData, LabelData, EdgeData
from semantics.data_types.indices import RoleID, VertexID, EdgeID, LabelID
from semantics.data_types.typedefs import TimeStamp


class TestRoleData(TestCase):

    def test_copy(self):
        role_data = RoleData(RoleID(0), 'role_name')
        role_data.data['a'] = 'b'
        copied_data = copy.copy(role_data)
        self.assertIsNot(copied_data.data, role_data.data,
                         "Data dict should not be shared by reference")
        self.assertEqual(copied_data.data, role_data.data,
                         "Data dicts should have same values")
        self.assertEqual(copied_data.name, role_data.name, "Names should be the same")
        self.assertEqual(copied_data.index, role_data.index, "Indices should be the same")
        self.assertIsNot(copied_data.access_manager, role_data.access_manager,
                         "Access manager should NOT be copied")


class TestVertexData(TestCase):

    def test_copy(self):
        vertex_data = VertexData(VertexID(1), RoleID(2), 'vertex_name', TimeStamp(3.0))
        vertex_data.data['p'] = 'q'
        vertex_data.inbound.add(EdgeID(1))
        vertex_data.outbound.add(EdgeID(2))
        copied_data = copy.copy(vertex_data)
        self.assertIsNot(copied_data.data, vertex_data.data,
                         "Data dict should not be shared by reference")
        self.assertEqual(copied_data.data, vertex_data.data,
                         "Data dicts should have the same value")
        self.assertEqual(copied_data.name, vertex_data.name, "Names should be the same")
        self.assertEqual(copied_data.index, vertex_data.index, "Indices should be the same")
        self.assertEqual(copied_data.time_stamp, vertex_data.time_stamp,
                         "Time stamps should be the same")
        self.assertIsNot(copied_data.access_manager, vertex_data.access_manager,
                         "Access manager should NOT be copied")
        self.assertIsNot(copied_data.outbound, vertex_data.outbound,
                         "Outbound should not be shared by reference")
        self.assertEqual(copied_data.outbound, vertex_data.outbound,
                         "Outbound should have same value")
        self.assertIsNot(copied_data.inbound, vertex_data.inbound,
                         "Outbound should not be shared by reference")
        self.assertEqual(copied_data.inbound, vertex_data.inbound,
                         "Outbound should have same value")


class TestLabelData(TestCase):

    def test_copy(self):
        label_data = LabelData(LabelID(4), 'label_name')
        label_data.data['x'] = 'y'
        copied_data = copy.copy(label_data)
        self.assertIsNot(copied_data.data, label_data.data,
                         "Data dict should not be shared by reference")
        self.assertEqual(copied_data.data, label_data.data, "Data dicts should have the same value")
        self.assertEqual(copied_data.name, label_data.name, "Names should be the same")
        self.assertEqual(copied_data.index, label_data.index, "Indices should be the same")
        self.assertIsNot(copied_data.access_manager, label_data.access_manager,
                         "Access manager should NOT be copied")


class TestEdgeData(TestCase):

    def test_copy(self):
        edge_data = EdgeData(EdgeID(5), LabelID(6), VertexID(7), VertexID(8))
        edge_data.data['k'] = 'v'
        copied_data = copy.copy(edge_data)
        self.assertIsNot(copied_data.data, edge_data.data,
                         "Data dict should not be shared by reference")
        self.assertEqual(copied_data.data, edge_data.data, "Data dicts should have the same value")
        self.assertEqual(copied_data.index, edge_data.index, "Indices should be the same")
        self.assertEqual(copied_data.label, edge_data.label, "Label IDs should be the same")
        self.assertEqual(copied_data.source, edge_data.source, "Source IDs should be the same")
        self.assertEqual(copied_data.sink, edge_data.sink, "Sink IDs should be the same")
        self.assertIsNot(copied_data.access_manager, edge_data.access_manager,
                         "Access manager should NOT be copied")
