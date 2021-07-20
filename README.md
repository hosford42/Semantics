# Semantics

*A Python library for modeling the semantics of natural language.*

## Introduction

*Semantics* is a Python library for representing, storing, and manipulating the 
semantic content of natural language, in a format designed to closely mirror
the structure of natural language. *Semantics* can be used as a knowledge graph,
but it is capable of much more. 

### Patterns

One of the core features of *Semantics* is its pattern matching capabilities. A
natural language utterance can be modeled as a pattern, which is then used to
update or query the knowledge graph. Patterns can even be attached to the graph
and triggered by later updates, potentially supporting automated reasoning
capabilities.

In contrast to the syntax of predicates in propositional logic, *Semantics* patterns 
are designed to closely mirror the structure of the natural language utterances they 
represent. This means that the output of a natural language parser can be mapped with 
minimal effort to *Semantics* patterns. A pattern is itself a graph, essentially
comprising a detailed grammar tree of the utterance it represents. Searching the
knowledge graph is simply a matter of aligning the structure of the pattern with
a subgraph of the knowledge graph.

### Evidence

Another core feature of *Semantics* is its use of accumulated evidence to determine
the truth/falsehood of statements. This is in contrast to more rigid knowledge graph
designs which are brittle in the face of conflicting or contradictory assertions. Many
knowledge graphs are all-or-nothing, following the assertions made by their users 
without question, ignoring the possibility of mistakes or uncertainty. *Semantics* is
built from the ground up with the assumption that *all* knowledge is subject to error,
revision, and uncertainty. 
