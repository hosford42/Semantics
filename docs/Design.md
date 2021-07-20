# Layers

From least abstract to most abstract:

* **Data Types** => *Indices, allocators, Python built-in types*
* **Data Structures** => *ControllerData, VertexData, etc.*
* **Data Control** => *Controller (persistent data), Transaction (pending changes)*
* **Graph** => *GraphDB, Connection, Vertex, etc.*
* **Knowledge Base** => *KnowledgeBase, Schema, Word, Kind, Statement, Query, etc.*

Each layer rests fully on the one before it, abstracting away and hiding implementation
details, so that at the top level we can simply interact with objects that have clear
semantic intent.
