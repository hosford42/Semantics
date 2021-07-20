* **Reference Counts**: Each object has a reference count which is incremented when 
  references are created and decremented when references are destroyed.
* **Role and Labels**: For roles and labels, references include the vertices and 
  edges, respectively, which are mapped to those roles and labels.
* **Cursors**: To read, modify, or delete an object, a cursor must access the 
  object via a reference to the object.
* **Write Access**: If a single reference to an object exists among all cursors of all
  threads, that reference can be used to modify or delete the referenced object.
* **Read Access**: If more than one reference to an object exists among all cursors of
  all threads, none of the references can be used to modify or delete the referenced 
  object.
* **Metadata**: Changes to the reference count are not considered modifications to 
  the object.  
* **Side Effects**: If modification or deletion of an object entails modification or 
  deletion of other related objects, the cursor used to modify or delete the object 
  must hold references to all affected objects. All affected objects must 
  simultaneously satisfy the appropriate conditions for modification or deletion by 
  the same cursor.
* **Non-Blocking**: In the event that a modification or deletion is initiated but 
  the conditions for the change and any potential side effects are not met, no change 
  will take place and an error will be raised in the calling thread.
* **Transactions**: Multiple sequentially ordered change requests can be submitted as 
  a unit, in which case all changes are either applied or rejected as a unit.

```python3

from semantics.graph_layer.graph_db import GraphDB

kb = GraphDB()

# Operations performed outside a transaction are executed immediately.
KIND = kb.get_role('KIND', add=True)
INSTANCE = kb.get_role('INSTANCE', add=True)
HAS_KIND = kb.get_label('HAS_KIND', add=True)
kind_vertex = kb.add_vertex(KIND)

# Operations requested within a transaction are not performed until the transaction
# is committed, either by explicitly calling transaction.commit() or automatically
# at the exit of the transaction provided it has not been canceled. If an exception
# occurs during the transaction, it is automatically canceled instead of being
# committed. All operations within the transaction are canceled if the transaction
# is canceled, leaving the kb's state unchanged from before the transaction began.
# The effects of each operation are cached so that read accesses to objects after 
# write operations to the same objects within the same transaction return the 
# results that *will* be returned later in the case where the transaction is 
# successfully committed. 
with kb.connect() as t:
  instance_vertex = t.add_vertex(INSTANCE)
  t.add_edge(HAS_KIND, instance_vertex, kind_vertex)

```