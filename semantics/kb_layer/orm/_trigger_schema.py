import logging

from semantics.kb_layer import schema
from semantics.kb_layer import schema_registry

from semantics.kb_layer.orm._pattern_schema import Pattern
from semantics.kb_layer.orm._hook_schema import Hook

_logger = logging.getLogger(__name__)


@schema_registry.register
class Trigger(schema.Schema):
    """A trigger is an association between a pattern and an action to be taken on its matches. A
    triggers is registered with one or more vertices in the graph, referred to as its trigger
    points. When changes occur to a trigger point, the trigger's pattern is checked for new matches
    in the neighborhood of the trigger point. For each new match that is found, the action is
    performed. This schema only serves to represent the trigger in the database. The actual trigger
    behavior is implemented in the TriggerQueue class."""

    trigger_points = schema.attribute('TRIGGER', outbound=False, plural=True)
    condition = schema.attribute('CONDITION', Pattern)
    action = schema.attribute('ACTION', Hook)
