"""
Shared functionality provided by both knowledge bases and transactional connections to them.
"""
import time
import typing

from semantics.data_types import typedefs
from semantics.graph_layer import elements
from semantics.graph_layer import interface
from semantics.kb_layer import builtin_roles, builtin_labels, builtin_patterns
from semantics.kb_layer import orm
from semantics.kb_layer import schema


class KnowledgeBaseInterface:
    """The outward-facing, public interface of the knowledge base."""

    def __init__(self, db: interface.GraphDBInterface, roles: 'builtin_roles.BuiltinRoles' = None,
                 labels: 'builtin_labels.BuiltinLabels' = None,
                 context: 'builtin_patterns.BuiltinPatterns' = None):
        self._database = db
        self._roles = builtin_roles.BuiltinRoles(db) if roles is None else roles
        self._labels = builtin_labels.BuiltinLabels(db) if labels is None else labels
        self._context = builtin_patterns.BuiltinPatterns(self) if context is None else context

    @property
    def roles(self) -> 'builtin_roles.BuiltinRoles':
        """The standardized, built-in roles used by the knowledge base."""
        return self._roles

    @property
    def labels(self) -> 'builtin_labels.BuiltinLabels':
        """The standardized, built-in labels used by the knowledge base."""
        return self._labels

    @property
    def context(self) -> 'builtin_patterns.BuiltinPatterns':
        """The standardized, built-in contextual patterns used by the knowledge base."""
        return self._context

    def get_word(self, spelling: str, add: bool = False) -> typing.Optional['orm.Word']:
        """Return a word from the knowledge base. If add is True, and the word does not exist
        already, create it first. Otherwise, return None."""
        vertex = self._database.find_vertex(spelling)
        if vertex is None:
            if add:
                vertex: elements.Vertex = self._database.add_vertex(self.roles.word)
                vertex.name = spelling
            else:
                return None
        else:
            assert vertex.preferred_role == self.roles.word
        return orm.Word(vertex, self._database)

    def get_divisibility(self, spelling: str, add: bool = False) \
            -> typing.Optional['orm.Divisibility']:
        word = self.get_word(spelling, add=add)
        if not word:
            return None
        if not add or word.divisibility.defined:
            return word.divisibility.get()
        vertex = self._database.add_vertex(self.roles.divisibility)
        divisibility = orm.Divisibility(vertex, self._database)
        word.divisibility.set(divisibility)
        return divisibility

    def add_kind(self, *names: str) -> 'orm.Kind':
        """Add a new kind to the knowledge base and return it. The name(s) provided are added as
        words, if necessary, and the kind is associated with them."""
        if not names:
            raise ValueError("Must provide at least one name for new kinds.")
        names = [self.get_word(name, add=True) for name in names]
        vertex = self._database.add_vertex(self._roles.kind)
        kind = orm.Kind(vertex, self._database, validate=False)
        for name in names:
            kind.names.add(name)
        return kind

    def add_instance(self, kind: 'orm.Kind') -> 'orm.Instance':
        """Add a new instance of the given kind to the knowledge base and return it."""
        vertex = self._database.add_vertex(self._roles.instance)
        instance = orm.Instance(vertex, self._database, validate=False)
        instance.kind.set(kind)
        return instance

    def add_time(self, time_stamp: typedefs.TimeStamp = None) -> 'orm.Time':
        """Add a new time to the knowledge base and return it. If a time stamp is provided, and
        a time with that time stamp already exists, return it instead of creating a new time.
        Otherwise, assign the time stamp to the newly created time."""
        if time_stamp is None:
            vertex = self._database.add_vertex(self._roles.time)
            return orm.Time(vertex, self._database)
        vertex = self._database.find_vertex_by_time_stamp(time_stamp)
        if vertex is not None:
            assert vertex.time_stamp == time_stamp
            return orm.Time(vertex, self._database)
        # Insert the timestamped vertex into the sequence, connecting it to its neighbors.
        nearest_vertex = self._database.find_vertex_by_time_stamp(time_stamp, nearest=True)
        vertex = self._database.add_vertex(self._roles.time)
        vertex.time_stamp = time_stamp
        time = orm.Time(vertex, self._database)
        if nearest_vertex is None:
            return time
        if nearest_vertex.time_stamp < time_stamp:
            before = nearest_vertex
            successors = {edge.sink for edge in nearest_vertex.iter_outbound()
                          if (edge.label == self.labels.precedes and
                              edge.sink.time_stamp is not None)}
            after = min(successors, key=lambda successor: successor.time_stamp,
                        default=None)
        else:
            after = nearest_vertex
            predecessors = {edge.source for edge in nearest_vertex.iter_inbound()
                            if (edge.label == self.labels.precedes and
                                edge.source.time_stamp is not None)}
            before = max(predecessors, key=lambda predecessor: predecessor.time_stamp,
                         default=None)
        assert before is None or before.time_stamp < time_stamp
        assert after is None or time_stamp < after.time_stamp
        if before:
            time.earlier_times.add(orm.Time(before, self._database))
        if after:
            time.later_times.add(orm.Time(after, self._database))
        return time

    def now(self) -> 'orm.Time':
        """Add the current time to the knowledge base and return it."""
        return self.add_time(typedefs.TimeStamp(time.time()))

    def add_observation(self, instance: 'orm.Instance', time: 'orm.Time' = None) -> 'orm.Instance':
        """Add a new observation of the given instance at the given time to the knowledge base
        and return it."""
        vertex = self._database.add_vertex(self._roles.observation)
        observation = orm.Instance(vertex, self._database, validate=False)
        observation.instance.set(instance)
        if time is None:
            time = self.add_time()
        observation.time.set(time)
        return observation

    def add_pattern(self, schema_type: typing.Type['schema.Schema'] = None) -> 'orm.Pattern':
        """Add a new pattern which matches the given schema. If no schema is provided, the schema
        defaults to Observation."""
        schema_type = schema_type or orm.Instance
        role = self._database.get_role(schema_type.role_name(), add=True)
        match_representative_vertex = self._database.add_vertex(role)
        match_representative = schema_type(match_representative_vertex, self._database)
        pattern_vertex = self._database.add_vertex(self._roles.pattern)
        pattern = orm.Pattern(pattern_vertex, self._database)
        pattern.match_representative.set(match_representative)
        return pattern

    def get_selector_pattern(self, spelling: str, add: bool = False,
                             schema: typing.Type['schema.Schema'] = None) \
            -> typing.Optional['orm.Pattern']:
        """Return a reusable, named mixin pattern from the knowledge base. If add is True and the
        word is not already associated with a selector pattern, create a new pattern first.
        Otherwise, return None."""
        word = self.get_word(spelling, add=add)
        if not word:
            return None
        if not add or word.selector.defined:
            assert schema is None or \
                   not word.selector.defined or \
                   isinstance(word.selector.get(), schema)
            return word.selector.get()
        pattern = self.add_pattern(schema)
        assert pattern.match_representative.get(validate=False)
        pattern.names.add(word)
        return pattern

    def match(self, pattern: 'orm.Pattern', *,
              partial: bool = False) -> typing.Iterator['orm.PatternMatch']:
        # TODO: Fill in other contextual match values.
        context = {
            self.context.now: self.now()
        }
        yield from pattern.find_matches(context, partial=partial)

    # def to_string(self, vertices: Iterable[VertexID] = None, edges: Iterable[EdgeID] = None)
    #         -> str:
    #     vertices = set(vertices or ())
    #     edges = set(edges or ())
    #
    #     visited_vertices = set()
    #     visited_edges = set()
    #
    #     results = []
    #     for vertex in sorted(vertices,
    #                          key=lambda vertex:
    #                              len(edges.intersection(self.iter_vertex_inbound(vertex)))):
    #         if vertex in visited_vertices:
    #             continue
    #         vertex_str = self._vertex_to_string(vertex, vertices, edges, visited_vertices,
    #                                             visited_edges)
    #         results.append(vertex_str)
    #
    #     for edge in sorted(edges):
    #         if edge in visited_edges:
    #             continue
    #         source = self.get_edge_source(edge)
    #         assert source not in visited_vertices
    #         edge_str = self._vertex_to_string(source, vertices, edges, visited_vertices,
    #                                           visited_edges, force=True)
    #         results.append(edge_str)
    #
    #     return '\n'.join(results)
    #
    # def _vertex_to_string(self, root: VertexID, vertices: Set[VertexID], edges: Set[EdgeID],
    #                       visited_vertices: Set[VertexID], visited_edges: Set[EdgeID], *,
    #                       force: bool = False) -> str:
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
    #             sink_str = self._vertex_to_string(sink, vertices, edges, visited_vertices,
    #                                               visited_edges)
    #             display_pairs.append((label, sink_str))
    #     return '%s[%s]' % (preferred_role, ', '.join('%s=%s' % (key, value)
    #                                                  for key, value in display_pairs))
