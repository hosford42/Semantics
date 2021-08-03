"""The Object-Relational Model to map from semantic structures to graph elements."""

from semantics.kb_layer import schema
from semantics.kb_layer.orm._divisibility_schema import Divisibility
from semantics.kb_layer.orm._hook_schema import Hook
from semantics.kb_layer.orm._instance_schema import Instance
from semantics.kb_layer.orm._kind_schema import Kind
from semantics.kb_layer.orm._number_schema import Number, MAGIC_COMPARISON_METHOD_NAMES
from semantics.kb_layer.orm._pattern_match_schema import PatternMatch
from semantics.kb_layer.orm._pattern_schema import Pattern, MatchMapping
from semantics.kb_layer.orm._time_schema import Time
from semantics.kb_layer.orm._trigger_schema import Trigger
from semantics.kb_layer.orm._word_schema import Word

__all__ = [
    'Divisibility',
    'Hook',
    'Instance',
    'Kind',
    'MAGIC_COMPARISON_METHOD_NAMES',
    'MatchMapping',
    'Number',
    'PatternMatch',
    'Pattern',
    'Time',
    'Trigger',
    'Word'
]


# =================================================================================================
# Attribute reverse-lookups. These have to be defined after the schema classes are, because they
# form cyclic references with the class definitions of the schemas they take as arguments.
# =================================================================================================


schema.Schema.represented_pattern = schema.attribute('MATCH_REPRESENTATIVE', Pattern,
                                                     outbound=False)
schema.Schema.represented_patterns = schema.attribute('MATCH_REPRESENTATIVE', Pattern,
                                                      outbound=False, plural=True)
schema.Schema.triggers = schema.attribute('TRIGGER', Trigger, plural=True)

Word.kind = schema.attribute('NAME', Kind, outbound=False, plural=False)
Word.kinds = schema.attribute('NAME', Kind, outbound=False, plural=True)
Word.selector = schema.attribute('NAME', Pattern, outbound=False, plural=False)
Word.selectors = schema.attribute('NAME', Pattern, outbound=False, plural=True)
Word.divisibility = schema.attribute('NAME', Divisibility, outbound=False, plural=False)
Word.divisibilities = schema.attribute('NAME', Divisibility, outbound=False, plural=True)

Kind.instances = schema.attribute('KIND', Instance, outbound=False, plural=True,
                                  minimum_preference=0.5)

Time.earlier_times = schema.attribute('PRECEDES', Time, outbound=False, plural=True)
Time.later_times = schema.attribute('PRECEDES', Time, outbound=True, plural=True)
Time.observations = schema.attribute('TIME', Instance, outbound=False, plural=True)

Number.lesser_values = schema.attribute('LESS_THAN', Number, outbound=False, plural=True)
Number.greater_values = schema.attribute('LESS_THAN', Number, outbound=True, plural=True)

Instance.instance = schema.attribute('INSTANCE', Instance, outbound=True, plural=False)
Instance.instances = schema.attribute('INSTANCE', Instance, outbound=True, plural=True)
Instance.observations = schema.attribute('INSTANCE', Instance, outbound=False, plural=True)
Instance.actor = schema.attribute('ACTOR', Instance, outbound=True, plural=False)

Pattern.template = schema.attribute('TEMPLATE', Pattern, outbound=True, plural=False)
Pattern.selectors = schema.attribute('SELECTOR', Pattern, outbound=True, plural=True)
Pattern.children = schema.attribute('CHILD', Pattern, outbound=True, plural=True)

PatternMatch.selectors = schema.attribute('SELECTOR', PatternMatch, outbound=True, plural=True)
PatternMatch.children = schema.attribute('CHILD', PatternMatch, outbound=True, plural=True)
