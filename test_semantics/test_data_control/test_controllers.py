import os
import tempfile
from unittest import TestCase

from semantics.data_control.controllers import Controller


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
        # When we save and then load from another controller, the content in the saved controller is in the loaded one.
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

        # Above, we verified that the latest file is loaded when clear_expired is set, and that all but one file is
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

    # TODO:
    #   * If there are corrupted saves:
    #       * The latest good save is loaded, if one exists.
    #       * The corrupted ones are skipped even if they are the latest one.
    #       * If clear_expired is set, the corrupted ones are removed, even if there are no good ones.
    #   * Loading a save file does not change its contents.
    #   * If the latest good save is removed, and a previous good one exists, it will be the one that's loaded.
