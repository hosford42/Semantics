"""
Connections to the graph database.
"""

import typing

from semantics.data_control import transactions
from semantics.graph_layer import interface
from semantics.data_types import exceptions

if typing.TYPE_CHECKING:
    from semantics.graph_layer import graph_db


class GraphDBConnection(interface.GraphDBInterface):
    """Connect to a GraphDB instance. Modifications are delayed and cached locally until the changes
    are committed or rolled back. If the changes are committed, they are applied to the underlying
    database as a single, atomic transaction."""

    def __init__(self, db: 'graph_db.GraphDB'):
        self._transaction = None  # Make sure it's defined for __del__ if we get an error below.
        self._transaction = transactions.Transaction(db._controller)
        super().__init__(self._transaction)

    def __del__(self):
        if self._transaction is not None:
            self.close()

    @property
    def is_open(self) -> bool:
        """Whether the connection is currently open."""
        return self._transaction.is_open

    def close(self):
        """Close the connection. Any pending changes are rolled back."""
        if self._transaction.is_open:
            self._transaction.rollback()
            self._transaction.close()

    def commit(self):
        """Commit pending changes to the database as a single atomic transaction."""
        if self._transaction.is_open:
            self._transaction.commit()
        else:
            raise exceptions.ConnectionClosedError()

    def rollback(self):
        """Roll back pending changes to the database."""
        if self._transaction.is_open:
            self._transaction.rollback()
        else:
            raise exceptions.ConnectionClosedError()

    def __enter__(self) -> 'GraphDBConnection':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._transaction.is_open:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
            self._transaction.close()
