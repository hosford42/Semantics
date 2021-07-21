# TODO

## Ongoing Checks

**These items can be marked as "done", but should never be removed, as they should 
be periodically reevaluated, particularly before releases.**

* Refactor any ugly/awkward/non-conforming code. Among other things:
    * All imports should be module imports of the form:
      `from semantic.module import sub_module` or
      `from semantic.module import long_name as short_name`
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

* Contexts need to be made into more than just dictionaries mapping from patterns to
  their images. In order to handle a broader array of pronouns, determiners, and 
  tenses, we will need to add information such as which instances were recently 
  referred to using which words or patterns, who is speaking, who is being spoken 
  to, etc. We will also need to be able to store this information on the graph and
  retrieve it again later if/when a conversation is resumed.
* It should be possible to withdraw a pattern match or a pattern with all of its
  matches. The effects of a pattern match will have to be stored on the graph, so
  they can be undone. This includes the evidence that was applied and where. Add
  `withdraw` methods to `Pattern` and `PatternMatch` to make this happen.
* Supply the fundamental semantic roles, labels, schemas, and other constructs 
  necessary to fully describe the meanings of arbitrary language utterances. (No big 
  deal, right?) Remember that client code should not be tightly bound to the specific 
  choice of roles, labels, and other graph-layer elements. Instead, they should make 
  use of the kb-layer interface. This will decouple the client logic from the graph 
  structure to some degree, improving flexibility later on. In more specific terms, 
  the roles and labels of the graph should not necessarily *have* to line up 
  one-to-one with the output of the semantic parser, even if that is generally the 
  case.
* A cleanup job that sweeps for edges with either really low evidence means and/or 
  really low evidence sample counts and removes them when space on the server is 
  running short and there are good alternatives present
* The README.md file really needs some attention. Right now, it's nothing more than
  an introduction.
  

### Nice to Have

* We need a patter builder. Right now the process is very accident-prone. It's easy
  to accidentally mix levels and connect to patterns instead of match 
  representatives, which causes subtle bugs.
* The unit tests need to be refactored. They are overly complex and have multiple
  assertions per test. They should be split out so there is one assertion per test,
  and named according to the specific requirements they are testing. Also, some 
  tests do not properly isolate the units they are testing, making them technically
  integration tests rather than unit tests.
* Make all exception types defined in the package inherit from the same base type.
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
* Unit test: Loading a save file does not change its contents.
* Unit test: If the latest good save is removed, and a previous good one exists, it 
  will be the one that's loaded.

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
* Should we rename `preferred_role` to just `role`? Sure, schemas can be flexible
  in regard to which types of vertices they can interface to, but the graph layer 
  is supposed to abstract those sorts of things away.
* A force-delete method for when an edge is added by mistake and needs to be removed 
  immediately instead of downweighted.

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
  instead of downweighted. (These have been made into their own **TODO**s.)
* The guarding mechanism for usage counts was broken by the transition to contextual
  locks. Holding a read lock is not sufficient by itself. Holding the registry lock
  for the duration of the usage count update would be sufficient. Holding a write 
  lock to the element would also be sufficient. Both of these options, however, 
  would generate excessive lock contention for commonly used roles and labels. 
  Another alternative would be to get rid of usage counts and require that removal 
  of roles and labels requires a full search for any uses while holding the registry
  lock; this would reduce lock contention for the common operations of vertex and 
  edge creation/deletion while making the rare operations of label and role removal 
  *very* expensive. Yet another alternative would be to add a global lock specific 
  to usage count updates, but I would rather keep global locks to a minimum. (I would
  like to do away with the global registry lock, as well.) I am currently leaning 
  strongly towards the option of eliminating usage counts altogether and making 
  vertex/edge ops fast but role/label removal expensive. **DONE** I went with the
  option of completely removing usage counts.
* A `find_by_time_stamp` method in `ControllerInterface`. It makes no sense to have
  a time stamp allocator if we can't reuse the vertices associated with them.
* We will also need to implement the on-demand behavior of adding new entries to
  the trigger queue whenever a new edge is added to a vertex with one or more attached
  triggers. This has to be done at the graph level, not the kb level, which means
  either the trigger queue and trigger mechanisms are at the graph level, or there
  are generic hooks at the graph level that the kb level can use for this purpose.
  An audit callback hook seems like the best approach here: Attach a callback
  function to a particular vertex which is automatically called whenever a change is
  made to the vertex. It would be the kb's responsibility to ensure the appropriate
  callbacks are implemented and registered. The problem here is that the callbacks
  need to be persistent, which means they cannot refer to a specific kb instance, and
  yet the callbacks need to know about the kb instance in order to inform it of the
  changes to the vertices. Maybe we can implement a graph-level queueing mechanism
  which the kb inspects? If the graph simply records changes in a predetermined
  shared location, then the trigger queue can simply inspect this location for new
  changes that need to be processed. The graph doesn't have to be made aware of the
  kb layer, and yet the kb layer can still maintain control by dictating via the hooks
  which elements are audited and how the audits are recorded in the graph.
* A method for finding an edge given its source, sink, and label. The `add_edge`
  already checks if an edge exists. This code can be adapted for the new purpose.
* Patterns and pattern matching.
* Assign words to languages, with a separate name space for each language in case 
  of conflicts in spelling. Use ISO language codes to identify the languages when 
  looking words up. Separate name allocators are not necessary. The language code 
  can be used in combination with the word's spelling as the key in the name 
  allocator, instead of just using spelling alone. The `Vertex.name` attribute 
  should be renamed to `Vertex.identifier` for clarity. Any methods that refer to 
  word spelling or other language-specific constructs should also take an optional 
  ISO language code to indicate which language is being used. The default language 
  should be a configurable setting. **DONE** I chose not to rename `Vertex.name`
  to `Vertex.identifier` and instead to store spelling and language in the
  vertex's data. Taking this approach means we can name vertices anything we like,
  which can come in handy later if we need to support other uniquely identifiable
  vertex types.
* Kinds need to be specifically identifiable. They correspond to word senses and
  may or may not be shared across languages or multiple words within a language.
  In cases where the user wants to examine a particular word sense, they need a
  way to refer to it other than a word that may ambiguously refer to multiple
  word senses. Give kinds an associated unique string identifier. Make it possible 
  to look up a specific kind by this identifier. Make it possible for a kind to 
  have no associated words, and to associate a kind with any number of words after 
  it has been created.

### Canceled

None, so far.
