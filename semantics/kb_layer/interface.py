"""
Shared functionality provided by both knowledge bases and transactional connections to them.
"""
import logging
import time
import typing

from semantics.data_types import typedefs, languages
from semantics.graph_layer import elements
from semantics.graph_layer import graph_db
from semantics.graph_layer import interface
from semantics.kb_layer import builtin_roles, builtin_labels, builtin_patterns, trigger_queues, \
    schema_registry, evidence
from semantics.kb_layer import orm
from semantics.kb_layer import schema

_logger = logging.getLogger(__name__)


class KnowledgeBaseInterface:
    """The outward-facing, public interface of the knowledge base."""

    def __init__(self, db: interface.GraphDBInterface, roles: 'builtin_roles.BuiltinRoles' = None,
                 labels: 'builtin_labels.BuiltinLabels' = None,
                 context: 'builtin_patterns.BuiltinPatterns' = None,
                 default_language: languages.Language = None):
        self._default_language = default_language or languages.Language('eng')
        self._database = db
        self._roles = builtin_roles.BuiltinRoles(db) if roles is None else roles
        self._labels = builtin_labels.BuiltinLabels(db) if labels is None else labels
        self._context = builtin_patterns.BuiltinPatterns(self) if context is None else context
        self._trigger_queue = trigger_queues.TriggerQueue(self)

    @property
    def database(self) -> graph_db.GraphDB:
        """The graph database the knowledge base resides in."""
        self._database: graph_db.GraphDB
        return self._database

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

    @property
    def trigger_queue(self) -> 'trigger_queues.TriggerQueue':
        """The queue of trigger events that have not yet been processed."""
        return self._trigger_queue

    @property
    def default_language(self) -> languages.Language:
        """The default language assumed by the system when none is specified."""
        return self._default_language

    def get_word(self, spelling: str, language: languages.Language = None, *,
                 add: bool = False) -> typing.Optional['orm.Word']:
        """Return a word from the knowledge base. If add is True, and the word does not exist
        already, create it first. Otherwise, return None."""
        if language is None:
            language = self._default_language
        name = 'WORD:' + str(language) + '|' + spelling
        vertex = self._database.find_vertex(name)
        if vertex is None:
            if add:
                vertex: elements.Vertex = self._database.add_vertex(self.roles.word)
                vertex.name = name
                vertex.set_data_key('spelling', spelling)
                vertex.set_data_key('language', language)
            else:
                return None
        else:
            assert vertex.preferred_role == self.roles.word
            assert vertex.get_data_key('spelling') == spelling
            assert vertex.get_data_key('language') == language

        return orm.Word(vertex, self._database)

    def get_divisibility(self, spelling: str, language: languages.Language = None, *,
                         add: bool = False) \
            -> typing.Optional['orm.Divisibility']:
        word = self.get_word(spelling, language, add=add)
        if not word:
            return None
        if not add or word.divisibility.defined:
            return word.divisibility.get()
        vertex = self._database.add_vertex(self.roles.divisibility)
        divisibility = orm.Divisibility(vertex, self._database)
        word.divisibility.set(divisibility)
        return divisibility

    # def add_kind(self, *names: str) -> 'orm.Kind':
    #     """Add a new kind to the knowledge base and return it. The name(s) provided are added as
    #     words, if necessary, and the kind is associated with them."""
    #     if not names:
    #         raise ValueError("Must provide at least one name for new kinds.")
    #     names = [self.get_word(name, add=True) for name in names]
    #     vertex = self._database.add_vertex(self._roles.kind)
    #     kind = orm.Kind(vertex, self._database, validate=False)
    #     for name in names:
    #         kind.names.add(name)
    #     return kind

    def get_kind_by_identifier(self, identifier: str, *,
                               add: bool = False) -> typing.Optional['orm.Kind']:
        """Return a kind from the knowledge base. If add is True, and the kind does not exist
        already, create it first. Otherwise, return None."""
        if not identifier:
            raise ValueError("Name must not be the empty string.")
        name = 'KIND:' + identifier
        vertex = self._database.find_vertex(name)
        if vertex is None:
            if add:
                vertex: elements.Vertex = self._database.add_vertex(self.roles.kind)
                vertex.name = name
            else:
                return None
        else:
            assert vertex.preferred_role == self.roles.kind
        return orm.Kind(vertex, self._database)

    def get_kind(self, word: str, sense: int, language: languages.Language = None, *,
                 add: bool = False) -> typing.Optional['orm.Kind']:
        if language is None:
            language = self._default_language
        if not word:
            raise ValueError("Word must not be empty string.")
        name = str(language) + '|' + word + '|' + str(sense)
        kind = self.get_kind_by_identifier(name, add=add)
        if kind is None:
            assert not add
            return None
        word = self.get_word(word, language, add=True)
        kind.names.add(word)
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
        vertex = self._database.add_vertex(self._roles.instance)
        observation = orm.Instance(vertex, self._database, validate=False)
        observation.instance.set(instance)
        if time is None:
            time = self.add_time()
        observation.time.set(time)
        return observation

    def add_pattern(self, schema_type: typing.Type['schema.Schema'] = None) -> 'orm.Pattern':
        """Add a new pattern which matches the given schema. If no schema is provided, the schema
        defaults to Instance."""
        schema_type = schema_type or orm.Instance
        role = self._database.get_role(schema_type.role_name(), add=True)
        match_representative_vertex = self._database.add_vertex(role)
        match_representative = schema_type(match_representative_vertex, self._database)
        pattern_vertex = self._database.add_vertex(self._roles.pattern)
        pattern = orm.Pattern(pattern_vertex, self._database)
        pattern.match_representative.set(match_representative)
        return pattern

    def get_selector_pattern(self, spelling: str, language: languages.Language = None,
                             schema: typing.Type['schema.Schema'] = None, *,
                             add: bool = False) -> typing.Optional['orm.Pattern']:
        """Return a reusable, named mixin pattern from the knowledge base. If add is True and the
        word is not already associated with a selector pattern, create a new pattern first.
        Otherwise, return None."""
        word = self.get_word(spelling, language, add=add)
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

    def get_current_context(self) -> 'orm.MatchMapping':
        # TODO: Fill in other contextual match values.
        context = {
            self.context.now: self.now()
        }
        return {key: (value, 1.0) for key, value in context.items()}

    def match(self, pattern: 'orm.Pattern', *, partial: bool = False,
              context: 'orm.MatchMapping' = None) -> typing.Iterator['orm.PatternMatch']:
        if context is None:
            context = self.get_current_context()
        yield from pattern.find_matches(context, partial=partial)

    def get_hook(self, callback: typing.Callable) -> 'orm.Hook':
        module_name = getattr(callback, '__module__', None)
        function_name = getattr(callback, '__qualname__', None)
        if (not module_name or not function_name or not callable(callback) or
                '__main__' in module_name or '<locals>' in function_name):
            raise ValueError("Only named functions residing in importable modules can act as "
                             "hooks.")
        hook_name = 'HOOK:' + module_name + '|' + function_name
        vertex = self._database.find_vertex(hook_name)
        if vertex is None:
            vertex: elements.Vertex = self._database.add_vertex(self.roles.hook)
            vertex.name = hook_name
            vertex.set_data_key('module_name', module_name)
            vertex.set_data_key('function_name', function_name)
        else:
            assert vertex.preferred_role == self.roles.hook
            assert vertex.get_data_key('module_name') == module_name
            assert vertex.get_data_key('function_name') == function_name
        return orm.Hook(vertex, self._database)

    def add_trigger(self, condition: 'orm.Pattern',
                    action: typing.Union['orm.Hook', typing.Callable], *,
                    partial: bool = False) -> 'orm.Trigger':
        if not isinstance(action, orm.Hook):
            action = self.get_hook(action)
        action.validate()

        # Add a trigger vertex to the graph and connect it to the pattern and the action.
        vertex = self._database.add_vertex(self.roles.trigger)
        trigger = orm.Trigger(vertex, self._database)
        trigger.condition.set(condition)
        trigger.action.set(action)
        trigger.vertex.set_data_key('partial', partial)

        # Search the pattern for links from match representatives to non-pattern vertices and add
        # the trigger to each non-pattern vertex, making it into a trigger point.
        for _pattern, trigger_point in condition.iter_trigger_points():
            trigger_point: schema.Schema
            trigger_point.triggers.add(trigger)
            trigger_point.vertex.audit = True

        return trigger

    def core_dump(self, log_level=logging.DEBUG) -> None:
        if not _logger.isEnabledFor(log_level):
            return

        def log(*args, **kwargs):
            _logger.log(log_level, *args, **kwargs)

        log("Core dump for %s:", self)
        for vertex in sorted(self._database.get_all_vertices(), key=lambda v: v.index):
            value = schema_registry.get_schema(vertex, self._database)
            log("    %s %s", value, evidence.get_evidence(vertex))
            for edge in sorted(vertex.iter_outbound(), key=lambda e: (e.label.name, e.sink.index)):
                sink_vertex = edge.sink
                sink_value = schema_registry.get_schema(sink_vertex, self._database)
                log("        %s: %s %s", edge.label.name, sink_value, evidence.get_evidence(edge))
