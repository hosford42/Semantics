## Schema

It's probably best to keep the data as a directed graph. In natural language, one type of 
object can be used as another, entirely different type of object. (Example: Verbing of
nouns, e.g., "I cheesed the burgers.") It should be possible to define "schemas", which
act as object-oriented interfaces to the underlying graph. A schema should be able to
check and report back whether the underlying graph has the appropriate local structure 
to satisfy treating a particular vertex as an object of a particular type. It should
also have appropriate behavior to handle cases where the expected structure requirements
are not satisfied. Ideally, we would define properties of the schema declaratively,
rather than procedurally. Here's an example:

```python

def attribute(*_args, **_kwargs):
    raise NotImplementedError()

class Schema:
    def __init__(self, vertex):
        self._vertex = vertex

    raise NotImplementedError()

class Kind(Schema):    
    raise NotImplementedError()

class Object(Schema): 
    kind = attribute(
        "kind",  # The name of the attribute, for error messages, etc.
        schema=Kind,  # The schema the attribute's value is wrapped with when present
        outbound=True,  # Directionality of the edge
        edge_label="KIND",  # Label of the edge
        min_count=0,  # Minimum *expected* number of edges
        max_count=1,  # Maximum *expected* number of edges
        preference=lambda edge, sink: ...,  # Key used for picking when more than expected
                                            # number of edges is present
    )

vertex = ...
obj = Object(vertex)
```
