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
import semantics.data_structs.controller_data as controller_data
import semantics.data_structs.transaction_data as transaction_data
import semantics.data_types.indices as indices


PersistentIDType = typing.TypeVar('PersistentIDType', bound=indices.PersistentDataID)


class Controller(interface.BaseController):
    """The internal-facing, protected interface of the graph database."""

    def __init__(self, save_dir: str = None, *, data: controller_data.ControllerData = None):
        super().__init__(data or controller_data.ControllerData())
        self.save_dir = save_dir

    def save(self, save_dir: str = None) -> None:
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
        save_dir = save_dir or self.save_dir
        if save_dir is None:
            raise ValueError("The save_dir parameter must be provided when there is no default "
                             "save_dir set.")
        save_paths = glob.glob(os.path.join(save_dir, '*_*.semantic'))
        data = None
        # Load the oldest file that has good data.
        expired = []
        for save_path in sorted(save_paths, reverse=True):
            if data:
                expired.append(save_path)
                continue
            try:
                with open(save_path, 'rb') as save_file:
                    data = pickle.load(save_file)
                logging.info("Successfully loaded save file: %s", save_path)
            except pickle.UnpicklingError:
                logging.warning("Save file was corrupted: %s", save_path)
                expired.append(save_path)
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
        return transaction_data.TransactionData(self._data)
