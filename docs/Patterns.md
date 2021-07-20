# Patterns

* Patterns must consist of components in the graph, which can be stored 
  persistently. This includes selectors and their match placeholders.
* Patterns must be able to match other patterns to generate new patterns.
* If a pattern component passed to the knowledge base as an update can match 
  repeatedly due to the use of a universal selector such as "all", "any", or 
  "always", the pattern component should be registered automatically as a trigger
  associated with the corresponding kind, so that new instances or observations
  are evaluated to see if they match the pattern and can therefore be updated.
* Patterns remember their matches as persistent entries in the graph, at least 
  for a while, and these matches can be retrieved and accepted or rejected even 
  after the iterator returned by update() or query() has been exhausted.
* If a pattern match is rejected after other pattern matches have taken place, 
  the direct effects it had on the structure and evidence of the graph should be
  withdrawn. Any other pattern matches that matched against structures generated
  by the rejected match should be recursively rejected as well. (The simplest
  way to accomplish this would be to record a pattern match's dependencies on
  previous matches at match time, via special dependency relation edges between
  the matches which can be retraced afterward.)
* A pattern's strength of effect is proportionate to the evidence for it. When a 
  previous pattern's match is contradicted by a newer or stronger one, it is 
  treated as negative evidence for the earlier/weaker pattern. This should lead
  to asymptotic logical consistency of the patterns stored in the graph, with
  accounting at each step for new evidence introduced externally.
* Sufficiently weak patterns are eventually removed from the graph, for the sake
  of resource efficiency.


### Some notes on the relationship to programming languages

A pattern registered as a trigger associated with a kind is functionally roughly
equivalent to a method associated with a class. The creation of new vertices and
edges in the graph serve as the medium for message passing. Thus, if the pattern,
"All triangles have 3 sides," is attached to the "triangle" kind in the knowledge
base, and we have just added a new triangle instance ABC to the KB, this will 
cause the pattern to be activated, and the more specific fact, "Triangle ABC has 3 
sides," will automatically be added to the KB. We can further combine this specific 
fact with other facts we may know about triangle ABC. For example, if we also have 
the pattern, "Triangles with two equal sides are isosceles," and we have the fact,
"Triangle ABC has two equal sides," the addition of, "Triangle ABC has 3 sides,"
will trigger the additional pattern and add the fact, "Triangle ABC is isosceles."

In this way, we can perform automated reasoning through the registration and 
application of patterns to facts (and to each other). Patterns registered as 
triggers in the KB serve as a novel declarative, object-oriented computing 
paradigm, in which the programming elements directly parallel the structure of 
natural language. Combined with a reasonably good parser and a mechanism to 
translate parses into patterns which are passed to update() or query(), we can 
perform automated reasoning directly from natural language inputs. By using 
patterns that generate events (non-auxiliary verbs), rather than states of 
being (strictly using the "be" verb), we can also use this system as an event 
simulator, modeling the unfolding of a story or episode based on expectations 
derived from natural language inputs. Furthermore, we can then query the 
resulting knowledge graph with natural language. In conjunction with a system
for generating natural language from the graph structures returned as matches by
update() and query(), it should be possible to build a programming system whose 
inputs and outputs strictly take the form of natural language utterances.
