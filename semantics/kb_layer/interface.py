import typing

import semantics.data_types.typedefs as typedefs
import semantics.graph_layer.elements as elements
import semantics.graph_layer.interface as interface
import semantics.kb_layer.builtin_roles as builtin_roles
import semantics.kb_layer.orm as orm


class KnowledgeBaseInterface:
    """The outward-facing, public interface of the knowledge base."""

    def __init__(self, db: interface.GraphDBInterface, roles: 'builtin_roles.BuiltinRoles' = None):
        self._db = db
        self._roles = builtin_roles.BuiltinRoles(db) if roles is None else roles

    @property
    def roles(self) -> 'builtin_roles.BuiltinRoles':
        return self._roles

    def get_word(self, spelling: str, add: bool = False) -> typing.Optional['orm.Word']:
        vertex = self._db.find_vertex(spelling)
        if vertex is None:
            if add:
                vertex: elements.Vertex = self._db.add_vertex(self.roles.word)
                vertex.name = spelling
            else:
                return None
        else:
            assert vertex.preferred_role == self.roles.word
        return orm.Word(vertex, self._db)

    def add_kind(self, *names: str) -> 'orm.Kind':
        if not names:
            raise ValueError("Must provide at least one name for new kinds.")
        names = [self.get_word(name, add=True) for name in names]
        vertex = self._db.add_vertex(self._roles.kind)
        kind = orm.Kind(vertex, self._db, validate=False)
        for name in names:
            kind.names.add(name)
        kind.validate()
        return kind

    def add_instance(self, kind: 'orm.Kind') -> 'orm.Instance':
        vertex = self._db.add_vertex(self._roles.instance)
        instance = orm.Instance(vertex, self._db, validate=False)
        instance.kind = kind
        instance.validate()
        return instance

    def add_time(self, time_stamp: typedefs.TimeStamp = None) -> 'orm.Time':
        vertex = self._db.add_vertex(self._roles.time)
        if time_stamp is not None:
            vertex.time_stamp = time_stamp
        return orm.Time(vertex, self._db)

    def add_manifestation(self, instance: 'orm.Instance', time: 'orm.Time') -> 'orm.Manifestation':
        vertex = self._db.add_vertex(self._roles.manifestation)
        manifestation = orm.Manifestation(vertex, self._db, validate=False)
        manifestation.instance = instance
        manifestation.time = time
        manifestation.validate()
        return manifestation

    # def to_string(self, vertices: Iterable[VertexID] = None, edges: Iterable[EdgeID] = None) -> str:
    #     vertices = set(vertices or ())
    #     edges = set(edges or ())
    #
    #     visited_vertices = set()
    #     visited_edges = set()
    #
    #     results = []
    #     for vertex in sorted(vertices, key=lambda vertex: len(edges.intersection(self.iter_vertex_inbound(vertex)))):
    #         if vertex in visited_vertices:
    #             continue
    #         vertex_str = self._vertex_to_string(vertex, vertices, edges, visited_vertices, visited_edges)
    #         results.append(vertex_str)
    #
    #     for edge in sorted(edges):
    #         if edge in visited_edges:
    #             continue
    #         source = self.get_edge_source(edge)
    #         assert source not in visited_vertices
    #         edge_str = self._vertex_to_string(source, vertices, edges, visited_vertices, visited_edges, force=True)
    #         results.append(edge_str)
    #
    #     return '\n'.join(results)
    #
    # def _vertex_to_string(self, root: VertexID, vertices: Set[VertexID], edges: Set[EdgeID],
    #                       visited_vertices: Set[VertexID], visited_edges: Set[EdgeID], *, force: bool = False) -> str:
    #     visit_vertex = force or (root in vertices and root not in visited_vertices)
    #     visited_vertices.add(root)
    #     preferred_role = self.get_role_name(self.get_vertex_preferred_role(root))
    #     display_pairs = [('id', root)]
    #     spelling = self.get_vertex_spelling(root)
    #     if spelling:
    #         display_pairs.append(('name', repr(spelling)))
    #     if visit_vertex:
    #         items = []
    #         for edge in self.iter_vertex_outbound(root):
    #             if edge in visited_edges:
    #                 continue
    #             visited_edges.add(edge)
    #             sink = self.get_edge_sink(edge)
    #             if edge not in edges and sink not in vertices:
    #                 continue
    #             label = self.get_label_name(self.get_edge_label(edge))
    #             items.append((label, sink))
    #         items.sort()
    #         for label, sink in items:
    #             sink_str = self._vertex_to_string(sink, vertices, edges, visited_vertices, visited_edges)
    #             display_pairs.append((label, sink_str))
    #     return '%s[%s]' % (preferred_role, ', '.join('%s=%s' % (key, value) for key, value in display_pairs))
