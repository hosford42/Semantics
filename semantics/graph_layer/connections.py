"""
Connections to the graph database.
"""

import typing

import semantics.data_control.transactions as transactions
import semantics.graph_layer.interface as interface

if typing.TYPE_CHECKING:
    import semantics.graph_layer.graph_db as graph_db


class GraphDBConnection(interface.GraphDBInterface):
    """Connect to a GraphDB instance. Modifications are delayed and cached locally until the changes
    are committed or rolled back. If the changes are committed, they are applied to the underlying
    database as a single, atomic transaction."""

    def __init__(self, db: 'graph_db.GraphDB'):
        self._transaction = transactions.Transaction(db._controller)
        self._is_open = True
        super().__init__(self._transaction)

    def __del__(self):
        if getattr(self, '_is_open', False):
            self.rollback()

    @property
    def is_open(self) -> bool:
        """Whether the connection is currently open."""
        return self._is_open

    def commit(self):
        """Commit pending changes to the database as a single atomic transaction."""
        if self._is_open:
            self._transaction.commit()
            self._is_open = False
        else:
            raise ValueError("Connection was already closed.")

    def rollback(self):
        """Roll back pending changes to the database."""
        if self._is_open:
            self._transaction.rollback()
            self._is_open = False
        else:
            raise ValueError("Connection was already closed.")

    def __enter__(self) -> 'GraphDBConnection':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._is_open:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
