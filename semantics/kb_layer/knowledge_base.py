"""The KnowledgeBase is the primary entrypoint to the library's public API. It provides a high-level
interface to the underlying data via the various Schema subclasses, shielding the client from
dealing directly with the vertices, edges, roles, and labels of the graph database on which it
rests."""

import semantics.graph_layer.graph_db as graph_db
import semantics.kb_layer.connections as connections
import semantics.kb_layer.interface as interface


# GraphDB handles direct interactions with roles, labels, vertices, and edges. KnowledgeBase sits on
# top of GraphDB and handles organizing and interacting with these elements in the specific patterns
# expected of a knowledge base.


class KnowledgeBase(interface.KnowledgeBaseInterface):
    """A knowledge base, for storing, searching, and manipulating semantic information extracted
    from natural language."""

    def __init__(self, database: graph_db.GraphDB = None):
        super().__init__(graph_db.GraphDB() if database is None else database)

    @property
    def database(self) -> graph_db.GraphDB:
        """The graph database the knowledge base resides in."""
        self._database: graph_db.GraphDB
        return self._database

    def connect(self) -> 'connections.KnowledgeBaseConnection':
        """Create and return a new transactional connection to the knowledge base."""
        return connections.KnowledgeBaseConnection(self)
