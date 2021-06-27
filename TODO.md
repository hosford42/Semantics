# TODO

## Ongoing Checks

**These items can be marked as "done", but should never be removed, as they should 
be periodically reevaluated, particularly before releases.**

* Refactor any ugly/awkward/non-conforming code. Among other things:
    * All imports should be module imports of the form:
      `import semantic.module.long_name as short_name`
    * `TypeVar` definitions should never be imported from other modules.
    * Each module must be assigned to a layer. No free-floating modules.
    * Modules in a given layer should only import external modules, earlier
      layers, or modules from the same layer as dependencies.
* All unit tests passing.
* Unit tests for all non-trivial execution paths.
* Complete documentation for all modules, classes, methods, and functions. Even
  stuff that's private needs a doc string, because we aren't just documenting for
  the users, but for the repo maintainers.
* No TODOs appearing in the actual source code. Either assimilate them here, or
  complete & remove them altogether.

## One-Time Changes

**These items can be moved to the "Completed" section below when they are done. 
Generally, the TODO text should also be converted to comments and/or documentation 
at the appropriate location(s) in the code.**

### Need to Have

* A `find_by_time_stamp` method in `ControllerInterface`. It makes no sense to have
  a time stamp allocator if we can't reuse the vertices associated with them.
* A method for finding an edge given its source, sink, and label. The `add_edge`
  already checks if an edge exists. This code can be adapted for the new purpose.
* Patterns and pattern matching.
* Supply the fundamental semantic roles, labels, schemas, and other constructs 
  necessary to fully describe the meanings of arbitrary language utterances. (No big 
  deal, right?) Remember that client code should not be tightly bound to the specific 
  choice of roles, labels, and other graph-layer elements. Instead, they should make 
  use of the kb-layer interface. This will decouple the client logic from the graph 
  structure to some degree, improving flexibility later on. In more specific terms, 
  the roles and labels of the graph should not necessarily *have* to line up 
  one-to-one with the output of the semantic parser, even if that is generally the 
  case.

### Nice to Have

* A cleaner process that runs as a background thread, removing graph elements with
  very few evidence samples, very negative evidence means, and/or no recent 
  accesses or updates. Note that to check recent accesses and updates, we'll first 
  need to track access and update times. Another option would be to track *creation* 
  times and access/update *counts*, and remove things with a low usage frequency. 
  The reason any of this is necessary is that, as a design choice, we won't be 
  deleting any graph elements during normal execution based on their evidence 
  samples or means, since we won't know if/when new evidence will be applied; we 
  are better off keeping the tallies around until resources are low or we have at 
  least waited a while for new evidence to come in.
* Journaling, to ensure database integrity and consistency in the event of a system
  failure.
* Choice between interactive transactions (acquiring read & write locks along the
  way to ensure the transaction can be committed, at the expense of tying up 
  resources along the way) or non-interactive transactions (locks are not acquired 
  until the commit operation begins -- just before the changes are applied -- which 
  may result in commit failures if they cannot be acquired).
* Another update-like locking mode, "append" or "extend". Allows new things to be
  added to the graph even when a read lock is held elsewhere, e.g., adding a new
  edge to a vertex despite someone else reading the vertex. This may also necessitate
  a new "exclusive read" mode which can block "append" mode locks from being acquired
  in cases where that could cause problems. The purpose is to reduce lock contention
  where possible.

### Iffy

* For `typedefs.TimeStamp`, should we use a `DateTime`? A `Decimal`? An integer 
  system ticks counter? Sticking with `float` until the need becomes apparent, but 
  it may need reconsidering.
* For `schema.Attribute`, let a string be passed in for the 2nd argument? Then we 
  can move attribute reverse-lookups into the class bodies instead of awkwardly 
  keeping them at the bottom of `orm.py`.
* Instead of clearing out *all* old saves when `Controller.load(clear_expired=True)`
  is called, should we maybe set a configurable age limit or a max number of files?
  I think that it still needs to be done during loading, because we need to verify
  that the files are actually loadable.

### Completed

* Weighted edges. These are important for weighing and comparing evidence for/against
  relationships between semantic elements. We will need at least 2 distinct weight
  types in order to track both the polarity of the evidence and the total amount of
  evidence. Otherwise, we won't know how much to update the polarity when new 
  evidence is added. **DONE**: The weights are added (see `kb_layer.evidence`) and 
  `kb_layer.schema` has been updated to fully utilize them. Now it uses them for the 
  default `preference` implementation, and they are updated whenever value mutator 
  methods are called. NOTE: We really shouldn't *automatically and immediately* 
  remove attribute edges anyway. Instead, we can have a cleanup job that sweeps for 
  edges with either really low evidence means and/or really low evidence sample 
  counts and removes them when space on the server is running short and there are 
  good alternatives present. We should also maybe provide a force-delete method for
  when an edge is added by mistake and needs to be actually removed immediately 
  instead of downweighted. (These should probably be made into their own 
  **TODO**s.)

### Canceled

None, so far.
