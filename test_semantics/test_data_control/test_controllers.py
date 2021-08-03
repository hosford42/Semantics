import os
import pickle
import tempfile
from unittest import TestCase
from unittest.mock import patch

from semantics.data_control.controllers import Controller
import test_semantics.test_data_control.base as base


class TestControllerSaveAndLoad(TestCase):

    def setUp(self) -> None:
        self._temp_dir_context = tempfile.TemporaryDirectory()
        self.temp_dir = self._temp_dir_context.name

    def tearDown(self) -> None:
        self._temp_dir_context.cleanup()
        del self.temp_dir

    def test_save_fails_if_no_save_dir(self):
        # Fail if no save_dir has been provided
        controller = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        with self.assertRaises(ValueError):
            controller.save()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)

    def test_load_fails_if_no_save_dir(self):
        # Have to provide a save_dir or we can't load even if a file exists
        controller1 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        controller2 = Controller()
        with self.assertRaises(ValueError):
            controller2.load()

    def test_save_when_save_dir_passed_to_method(self):
        # Can save if save_dir is provided directly to method
        controller = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

    def test_load_when_save_dir_passed_to_method(self):
        # Can load if save_dir is provided through method
        controller1 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        controller2 = Controller()
        controller2.load(self.temp_dir)

    def test_save_when_save_dir_passed_to_constructor(self):
        # Can save if save_dir is provided through constructor
        controller = Controller(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller.save()
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

    def test_load_when_save_dir_passed_to_constructor(self):
        # Can load if save_dir is provided via constructor
        controller1 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        controller2 = Controller(self.temp_dir)
        controller2.load()

    def test_load_fails_if_no_file(self):
        # Load fails with exception if no files exist
        controller = Controller(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        with self.assertRaises(FileNotFoundError):
            controller.load()
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)

    def test_can_save_multiple_times(self):
        # Can save multiple times
        controller2 = Controller(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller2.save()
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        controller2.save()
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)

    def test_content_is_preserved(self):
        # When we save and then load from another controller, the content in the saved controller is
        # in the loaded one.
        controller1 = Controller()
        label_id = controller1.add_label('test_label')
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        controller2 = Controller()
        controller2.load(self.temp_dir)

        self.assertEqual(controller2.find_label('test_label'), label_id)
        self.assertEqual(controller2.get_label_name(label_id), 'test_label')

    def test_latest_is_loaded(self):
        # Latest save is the one that's loaded.
        controller1 = Controller()
        label1 = 'label1'
        label1_id = controller1.add_label(label1)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        controller2 = Controller()
        label2 = 'label2'
        self.assertNotEqual(label1, label2)
        label2_id = controller2.add_label(label2)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        controller2.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)

        controller3 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)
        controller3.load(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)

        self.assertEqual(controller3.find_label(label2), label2_id)
        self.assertEqual(controller3.get_label_name(label2_id), label2)
        self.assertNotEqual(controller3.find_label(label1), label1_id)
        # Either label1_id isn't in controller3 at all, or it just happens to be equal to label2_id.
        try:
            self.assertNotEqual(controller3.get_label_name(label1_id), label1)
        except KeyError:
            self.assertNotEqual(label1_id, label2_id)

    def test_previous_saves_removed(self):
        # Older saves are removed on load if clear_expired is set
        controller1 = Controller()
        label1 = 'label1'
        label1_id = controller1.add_label(label1)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        controller2 = Controller()
        label2 = 'label2'
        self.assertNotEqual(label1, label2)
        label2_id = controller2.add_label(label2)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        controller2.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)

        controller3 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)
        controller3.load(self.temp_dir, clear_expired=True)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        self.assertEqual(controller3.find_label(label2), label2_id)
        self.assertEqual(controller3.get_label_name(label2_id), label2)
        self.assertNotEqual(controller3.find_label(label1), label1_id)

        # Either label1_id isn't in controller3 at all, or it just happens to be equal to label2_id.
        try:
            self.assertNotEqual(controller3.get_label_name(label1_id), label1)
        except KeyError:
            self.assertNotEqual(label1_id, label2_id)

        # Above, we verified that the latest file is loaded when clear_expired is set, and that all
        # but one file is
        # removed. Here, we verify that the file that was left is the latest one.
        controller4 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        controller4.load(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)

        self.assertEqual(controller4.find_label(label2), label2_id)
        self.assertEqual(controller4.get_label_name(label2_id), label2)
        self.assertNotEqual(controller4.find_label(label1), label1_id)

        # Either label1_id isn't in controller4 at all, or it just happens to be equal to label2_id.
        try:
            self.assertNotEqual(controller4.get_label_name(label1_id), label1)
        except KeyError:
            self.assertNotEqual(label1_id, label2_id)

    def test_most_recent_save_corrupted(self):
        """
        If there are corrupted saves:
            * The latest good save is loaded, if one exists.
            * The corrupted ones are skipped even if they are the latest one.
            * Corrupted files that are more recent than the latest good save are not removed, even
              if clear_expired is True. (This is to assist in forensic recovery should the end user
              decide to pursue it.)
        """
        controller1 = Controller()
        label1 = 'label1'
        label1_id = controller1.add_label(label1)
        self.assertEqual(len(os.listdir(self.temp_dir)), 0)
        controller1.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        good_save_name = os.listdir(self.temp_dir).pop()

        controller2 = Controller()
        label2 = 'label2'
        self.assertNotEqual(label1, label2)
        label2_id = controller2.add_label(label2)
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
        controller2.save(self.temp_dir)
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)
        save_paths = os.listdir(self.temp_dir)
        save_paths.remove(good_save_name)
        bad_save_name = save_paths.pop()
        bad_save_path = os.path.join(self.temp_dir, bad_save_name)

        bad_data = b"Some garbage that pickle can't read. \x00\x01\x02"
        with open(bad_save_path, 'wb') as bad_save_file:
            bad_save_file.write(bad_data)
        with self.assertRaises(pickle.UnpicklingError):
            with open(bad_save_path, 'rb') as bad_save_file:
                pickle.load(bad_save_file)

        controller3 = Controller()
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)
        with patch('logging.Logger.warning') as log_warning_method:
            controller3.load(self.temp_dir, clear_expired=True)
            log_warning_method.assert_called()
        self.assertEqual(len(os.listdir(self.temp_dir)), 2)

        self.assertEqual(controller3.find_label(label1), label1_id)
        self.assertEqual(controller3.get_label_name(label1_id), label1)
        self.assertNotEqual(controller3.find_label(label2), label2_id)
        # Either label2_id isn't in controller3 at all, or it just happens to be equal to label1_id.
        try:
            self.assertNotEqual(controller3.get_label_name(label2_id), label2)
        except KeyError:
            self.assertNotEqual(label1_id, label2_id)


class TestControllerReferences(base.BaseControllerReferencesTestCase):
    base_controller_subclass = Controller

    def test_new_reference_id(self):
        super().test_new_reference_id()

    def test_acquire_reference(self):
        super().test_acquire_reference()

    def test_release_reference(self):
        super().test_release_reference()


class TestControllerRoles(base.BaseControllerRolesTestCase):
    base_controller_subclass = Controller

    def test_add(self):
        super().test_add()

    def test_remove(self):
        super().test_remove()

    def test_remove_locked(self):
        super().test_remove_locked()

    def test_get_name(self):
        super().test_get_name()

    def test_get_name_locked(self):
        super().test_get_name_locked()

    def test_find(self):
        super().test_find()


class TestControllerLabels(base.BaseControllerLabelsTestCase):
    base_controller_subclass = Controller

    def test_add(self):
        super().test_add()

    def test_remove(self):
        super().test_remove()

    def test_remove_locked(self):
        super().test_remove_locked()

    def test_get_name(self):
        super().test_get_name()

    def test_get_name_locked(self):
        super().test_get_name_locked()

    def test_find(self):
        super().test_find()


class TestControllerVertices(base.BaseControllerVerticesTestCase):
    base_controller_subclass = Controller

    def test_add_vertex(self):
        super().test_add_vertex()

    def test_add_vertex_locked_role(self):
        super().test_add_vertex_locked_role()

    def test_get_vertex_preferred_role(self):
        super().test_get_vertex_preferred_role()

    def test_get_locked_vertex_preferred_role(self):
        super().test_get_locked_vertex_preferred_role()

    def test_find_in_catalog(self):
        super().test_find_in_catalog()

    def test_count_vertex_outbound(self):
        super().test_count_vertex_outbound()

    def test_count_locked_vertex_outbound(self):
        super().test_count_locked_vertex_outbound()

    def test_iter_vertex_inbound(self):
        super().test_iter_vertex_outbound()

    def test_iter_locked_vertex_outbound(self):
        super().test_iter_locked_vertex_outbound()

    def test_count_vertex_inbound(self):
        super().test_count_vertex_inbound()

    def test_count_locked_vertex_inbound(self):
        super().test_count_locked_vertex_inbound()

    def test_iter_vertex_outbound(self):
        super().test_iter_vertex_inbound()

    def test_iter_locked_vertex_inbound(self):
        super().test_iter_locked_vertex_inbound()


class TestControllerRemoveVertexMethod(base.BaseControllerRemoveVertexMethodTestCase):
    base_controller_subclass = Controller

    def test_vertex_does_not_exist(self):
        super().test_vertex_does_not_exist()

    def test_vertex_is_read_locked(self):
        super().test_vertex_is_read_locked()

    def test_vertex_is_write_locked(self):
        super().test_vertex_is_write_locked()

    def test_adjacent_edges_is_false(self):
        super().test_adjacent_edges_is_false()

    def test_edge_is_read_locked(self):
        super().test_edge_is_read_locked()

    def test_edge_is_write_locked(self):
        super().test_edge_is_write_locked()

    def test_adjacent_vertex_is_read_locked(self):
        super().test_adjacent_vertex_is_read_locked()

    def test_adjacent_vertex_is_write_locked(self):
        super().test_adjacent_vertex_is_write_locked()

    def test_happy_path(self):
        super().test_happy_path()


class TestControllerEdges(base.BaseControllerEdgesTestCase):
    base_controller_subclass = Controller

    def test_add_edge(self):
        super().test_add_edge()

    def test_add_edge_label_locked(self):
        super().test_add_edge_label_locked()

    def test_add_edge_source_locked(self):
        super().test_add_edge_source_locked()

    def test_add_edge_sink_locked(self):
        super().test_add_edge_sink_locked()

    def test_remove_edge(self):
        super().test_remove_edge()

    def test_remove_locked_edge(self):
        super().test_remove_locked_edge()

    def test_remove_edge_label_read_locked(self):
        super().test_remove_edge_label_read_locked()

    def test_remove_edge_label_write_locked(self):
        super().test_remove_edge_label_write_locked()

    def test_remove_edge_source_locked(self):
        super().test_remove_edge_source_locked()

    def test_remove_edge_sink_locked(self):
        super().test_remove_edge_sink_locked()

    def test_get_edge_label(self):
        super().test_get_edge_label()

    def test_get_locked_edge_label(self):
        super().test_get_locked_edge_label()

    def test_get_edge_source(self):
        super().test_get_edge_source()

    def test_get_locked_edge_source(self):
        super().test_get_locked_edge_source()

    def test_get_edge_sink(self):
        super().test_get_edge_sink()

    def test_get_locked_edge_sink(self):
        super().test_get_locked_edge_sink()


class TestControllerDataKeys(base.BaseControllerDataKeysTestCase):
    base_controller_subclass = Controller

    def test_get_data_key(self):
        super().test_get_data_key()

    def test_set_data_key(self):
        super().test_set_data_key()

    def test_clear_data_key(self):
        super().test_clear_data_key()

    def test_has_data_key(self):
        super().test_has_data_key()

    def test_iter_data_keys(self):
        super().test_iter_data_keys()

    def test_count_data_keys(self):
        super().test_count_data_keys()
