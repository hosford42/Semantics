"""The Controller implements the behavior of the GraphDB instance. It serves as an abstraction to
hide the details of data storage and persistence from the GraphDB. The GraphDB provides the
high-level interface to the graph data, while calling into the Controller to perform the actual data
transformations. The GraphDB operates at the level of references to graph elements, while the
Controller operates at the level of element indices and primitive data types. All interactions with
the underlying graph elements' data structures are managed by the Controller, leaving the GraphDB to
focus on providing a friendly external interface."""

import datetime
import glob
import logging
import os.path
import pickle
import typing

import semantics.data_control.base as interface
from semantics.data_structs import controller_data
from semantics.data_structs import transaction_data
from semantics.data_types import indices


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Controller(interface.BaseController[controller_data.ControllerData]):
    """The internal-facing, protected interface of the graph database."""

    def __init__(self, save_dir: str = None, *, data: controller_data.ControllerData = None):
        super().__init__(data or controller_data.ControllerData())
        self.save_dir = save_dir

    def save(self, save_dir: str = None) -> None:
        """Save the controller's data to disk."""
        save_dir = save_dir or self.save_dir
        if save_dir is None:
            raise ValueError("The save_dir parameter must be provided when there is no default "
                             "save_dir set.")
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        time_stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        save_name = time_stamp + '.semantic'
        counter = 1
        while save_name in os.listdir(save_dir):
            counter += 1
            save_name = '%s_%s.semantic' % (time_stamp, counter)
        save_path = os.path.join(save_dir, save_name)
        assert not os.path.exists(save_path)
        with open(save_path, 'wb') as save_file:
            pickle.dump(self._data, save_file, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, save_dir: str = None, *, clear_expired: bool = False) -> None:
        """Load the most recently saved version of the controller's data from disk. Corrupted or
        older versions of the data are skipped. If clear_expired is set, corrupted and older
        versions of the data are removed. If no valid version can be found, an exception is raised.
        """
        save_dir = save_dir or self.save_dir
        if save_dir is None:
            raise ValueError("The save_dir parameter must be provided when there is no default "
                             "save_dir set.")
        save_paths = glob.glob(os.path.join(save_dir, '*_*.semantic'))

        sort_keys = {}
        for save_path in save_paths:
            save_name = os.path.basename(save_path)
            components = save_name.split('.')[0].split('_')
            if len(components) == 2:
                save_date, save_time = components
                save_sequence = '1'
            elif len(components) == 3:
                save_date, save_time, save_sequence = components
            else:
                logging.warning("Unrecognized file in save dir: %s", save_path)
                continue
            if save_date.isdigit() and save_time.isdigit() and save_sequence.isdigit():
                sort_keys[save_path] = (int(save_date), int(save_time), int(save_sequence))
            else:
                logging.warning("Unrecognized file in save dir: %s", save_path)

        # Load the newest file that has good data.
        data = None
        expired = []
        for save_path in sorted(sort_keys, key=sort_keys.get, reverse=True):
            if data:
                expired.append(save_path)
                continue
            try:
                with open(save_path, 'rb') as save_file:
                    data = pickle.load(save_file)
                logging.info("Successfully loaded save file: %s", save_path)
            except pickle.UnpicklingError:
                logging.warning("Save file was corrupted: %s", save_path)
        if clear_expired:
            for path in expired:
                try:
                    os.remove(path)
                except OSError:
                    logging.warning("Failed to remove expired save file: %s", path)
        if not data:
            raise FileNotFoundError("No valid previous save files identified.")
        self._data = data

    def new_transaction_data(self) -> transaction_data.TransactionData:
        """Create and return a new TransactionData instance for use by a new transaction."""
        return transaction_data.TransactionData(self._data)
