# Project Goal

Create an object-oriented programming paradigm which mirrors the semantic 
structure of natural language, English in particular.

```
Classes => kind words, e.g., nouns, verbs, adjectives, and adverbs

Objects => noun phrases

Events => verb phrases

Relations => prepositional phrases and juxtapositional connectives such
    as subject-verb or verb-direct object adjacency.

Properties => adjectival and adverbial phrases
```

Note that object composition is not directly reflected in the semantic 
structure described above. Instead, composition is simply one of many
potential relations between objects. Likewise, object type is specified
as a relation between the object and its class.

Pattern matching is used to create, update, and query the object structure
in memory. These actions correspond roughly to statements and questions
in natural language. Furthermore, the object structure can be annotated
with goals, which are desired structures that can be used with planning
algorithms to determine a course of action. This is, again, accomplished
using pattern matching, and roughly corresponds to commands in natural
language.

Patterns in any of the aforementioned forms can be generic, in which case 
they are stored in the object hierarchy and activated as the object 
structure changes. This should enable the application of general knowledge 
to novel settings, e.g., inference from previous statements as new ones are
encountered, delayed answering of questions which are open-ended or which 
could not be immediately answered, or responding to commands when the 
opportunity to satisfy them arises.

The end result, hopefully, is a system that can implement the semantics
of natural language. This system should act as a dynamic knowledge base
with an explicitly defined ontology that is expressed in the same terms as 
all the other knowledge it holds. Ideally, we can then map arbitrary natural 
language directly to this system to implement an intelligent conversation 
engine and conversation-driven process controller.
