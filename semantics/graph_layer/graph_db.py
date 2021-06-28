"""GraphDB implements a graph database specifically tailored to the needs of the KnowledgeBase. It
is designed to be flexible and generic, having no direct knowledge of how it will be used by the
KnowledgeBase. Thus it *may* be useful for other, more general purposes, but this is its primary
one. It is not intended to be part of the public API of the semantics library.

The GraphDB consists of only four primitive element types: vertices, edges, roles, and labels. Edges
are always directed. Roles and labels serve to categorize vertices and edges, respectively,
according to their expected behavior and usage.

All four element types of the GraphDB are persistent and are accessed via *indirect references*
which hold only the element's unique ID. References to graph elements automatically inform the graph
database when they are created and destroyed (including creation of copies of existing references),
ensuring that an element cannot be deleted so long as a live reference to it exists. Elements are
only destroyed when it is specifically requested by a client. If a thread lock, live reference, or
database-internal reference to an element exists, the operation will fail and the element will not
be destroyed.

The GraphDB supports both direct/immediate access and transaction-mediated indirect access. For
direct access, simply call into the GraphDB's interface. To use transaction-mediated access, first
create a connection via the GraphDB's connect() method, and then interact with the connection. The
connection supports the full interface of the GraphDB, plus the standard commit() and rollback()
transactional operations. Because the connection supports the full GraphDB interface, code which
uses direct access can easily be modified to use a transactional connection instead. Connections
actively communicate with the GraphDB, acquiring the appropriate read and write locks as the
transaction is constructed, rather than passively accumulating requested operations and then
acquiring all locks at the time commit() is called. This is due to the highly interactive nature of
graph database interaction. (However, a passive transactional mode may eventually be supported,
since active communication with the database is not well-suited for remote clients with limited
network bandwidth.)
"""

import semantics.graph_layer.connections as connections
import semantics.graph_layer.interface as interface


class GraphDB(interface.GraphDBInterface):
    """The graph database class provides immediate, non-transactional access to the
    contents of the graph."""

    def connect(self) -> 'connections.GraphDBConnection':
        return connections.GraphDBConnection(self)
