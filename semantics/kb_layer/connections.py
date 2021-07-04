"""
Connections to a knowledge base.
"""

import typing

from semantics.kb_layer import interface

if typing.TYPE_CHECKING:
    from semantics.kb_layer import knowledge_base


class KnowledgeBaseConnection(interface.KnowledgeBaseInterface):
    """A transactional connection to a knowledge base. Changes made through the connection are
    cached until they are committed, at which point they are applied to the knowledge base as a
    single, atomic transaction."""

    def __init__(self, kb: 'knowledge_base.KnowledgeBase'):
        self._db_connection = kb.database.connect()
        super().__init__(self._db_connection, kb.roles)

    @property
    def is_open(self) -> bool:
        """Whether the connection is currently open."""
        return self._db_connection.is_open

    def commit(self):
        """Commit any pending changes to the knowledge base."""
        self._db_connection.commit()

    def rollback(self):
        """Cancel any pending changes to the knowledge base."""
        self._db_connection.rollback()

    def __enter__(self) -> 'KnowledgeBaseConnection':
        self._db_connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._db_connection.__exit__(exc_type, exc_val, exc_tb)
