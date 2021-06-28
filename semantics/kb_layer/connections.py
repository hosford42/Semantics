import typing

import semantics.kb_layer.interface as interface

if typing.TYPE_CHECKING:
    import semantics.kb_layer.knowledge_base as knowledge_base


class KnowledgeBaseConnection(interface.KnowledgeBaseInterface):

    def __init__(self, kb: 'knowledge_base.KnowledgeBase'):
        self._db_connection = kb.database.connect()
        super().__init__(self._db_connection, kb.roles)

    @property
    def is_open(self) -> bool:
        return self._db_connection.is_open

    def commit(self):
        self._db_connection.commit()

    def rollback(self):
        self._db_connection.rollback()

    def __enter__(self) -> 'KnowledgeBaseConnection':
        self._db_connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._db_connection.__exit__(exc_type, exc_val, exc_tb)
