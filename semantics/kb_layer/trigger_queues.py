import itertools
import typing

from semantics.kb_layer import schema, orm, schema_registry

if typing.TYPE_CHECKING:
    import semantics.kb_layer.interface as kb_interface
    import semantics.graph_layer.interface as graph_db_interface


class TriggerQueue:

    def __init__(self, kb: 'kb_interface.KnowledgeBaseInterface',
                 db: 'graph_db_interface.GraphDBInterface'):
        self._kb = kb
        self._db = db

    @property
    def pending(self) -> bool:
        """Whether there are pending trigger events that need to be processed."""
        return self._db.get_vertex_audit_count() > 0

    def process_one(self) -> bool:
        """If there are pending trigger events, process the first one. Return whether an event
        was processed or not."""
        vertex = self._db.pop_least_recently_audited_vertex()
        if vertex is None:
            return False

        schema_instance = schema.Schema(vertex, self._db)
        print("Trigger point:", schema_registry.get_schema(vertex, self._db))

        for trigger in schema_instance.triggers:
            condition: orm.Pattern = trigger.condition.get()
            if not isinstance(condition, orm.Pattern) or not condition.is_valid:
                continue
            action: orm.Hook = trigger.action.get()
            if not isinstance(action, orm.Hook) or not action.is_valid:
                continue
            partial = trigger.vertex.get_data_key('partial', False)
            context = self._kb.get_current_context()
            for pattern, trigger_point in condition.iter_trigger_points():
                assert pattern not in context
                for candidate in pattern.find_match_candidates(context, neighbor=vertex):
                    context[pattern] = candidate
                    for match in self._kb.match(condition, partial=partial, context=context):
                        # TODO: How do we make sure it's a *new* match?
                        action(match)
                if pattern in context:
                    del context[pattern]

        return True

    def process_all(self) -> int:
        """Process all pending trigger events, returning the number of processed events upon
        completion."""
        count = 0
        while self.process_one():
            count += 1
        return count
