# Goals, Actions, and Causality

**TODO**: This functionality is not implemented in code yet. Also, before it is 
implemented, there is another angle that needs to be examined: What happens 
when two or more goals conflict with each other? For example, if the user says, 
"Move the red block to the right," but the user has previously told the system, 
"Never move green blocks," and there is a green block resting on the red block, 
we will need a way to (1) identify that there is a conflict and (2) handle the 
conflict appropriately, e.g., by choosing the higher priority goal or asking 
the user what to do.

## Causality

The system will need to understand the consequences of its actions to some 
degree, either because it was told or because it discovered on its own. In 
other words, it will need a concept of causality: "If I do X, then Y will 
happen." Furthermore, this information will have to be stored on the graph in a
form that is amenable to search.

We cannot simply store causes and effects as pattern and link those patterns 
together via edges with a dedicated CAUSES label, because the mapping between 
pattern nodes from one pattern to the next would be lost. For example, take the 
causal relationship, "If an apple falls above me, it will hit me on the head." 
Here, "it" refers to the same element as "an apple". We cannot causally relate 
any two independent matches for, "An apple falls above me," and, "It will hit 
me on the head," because "it" can refer to something completely unrelated in 
the second pattern. Context is important.

Instead, we need a single "causal pattern" that matches in two parts: a 
condition, and its outcome. When we get a complete match for the condition, we 
should expect a complete match for the outcome. Evidentially, any match attempt 
in which both parts match fully is a positive sample, and any match in which 
the condition matches but the outcome does not (after a reasonable amount of 
time) is a negative sample. When the condition is only partially matched, the 
causal pattern's evidence is unaffected.

## Goals

Now suppose we want to *make* an apple hit me on the head. (What fun!) We 
indicate this by issuing a goal pattern, "Make an apple hit me on the head," 
with a partial match indicating who "me" is and which head is "the head" 
(mine). The system must then search *causal patterns* (not raw factual 
knowledge!) whose outcomes include the unsatisfied relationships described in 
the goal pattern, i.e., that an apple has hit the indicated head. During the 
search, the mapping of the original goal pattern's match will be kept. This 
mapping will be used to initialize the context for further matching while 
searching causal patterns. This allows us to examine the outcome portion of the
causal pattern to verify that at least some of the missing relationships of the 
primary goal will be added should the condition be met. It also allows us to 
determine to what degree their conditions are already met. The portions of 
their conditions which are not met will in turn become goal patterns, 
explicitly marked as subgoals of the original one.

Primary goals (those which are not subgoals) are prioritized according to how 
recently they were issued and how important the user considers them to be. A 
subgoal's "effectiveness" is defined to be the number (and intensity, either 
positive or negative) of its parent goal's missing relationships that will be 
added by the associated causal pattern should the subgoal's outcome be 
satisfied, times the evidence for the associated causal pattern (which 
indicates the causal pattern's probability of success). A subgoal's 
"difficulty" is defined to be the number (and intensity) of unsatisfied 
relationships it introduces. A subgoal's priority relative to others is 
directly proportional to whether there is a direct action associated with it, 
its primary goal's priority, and the subgoal's effectiveness. A subgoal's 
priority is indirectly proportional to its difficulty.

## Actions

The KB must provide a mechanism to define direct actions the system can take. 
These direct actions closely resemble triggers, in that they consist of a 
condition pattern paired with an action hook which receives a match for the 
condition as an argument. However, direct actions are not associated with 
trigger points in the KB; instead, they are triggered during goal search. This 
occurs when the pattern associated with the direct action appears as the 
condition in a causal pattern, the goal search issues a subgoal via that causal
pattern, and the causal pattern's condition is fully satisfied.

Goals and subgoals are marked as triggers in the KB. Thus, subgoals fan out 
like a net around their primary goals in the KB, waiting for their conditions 
to be satisfied. When a goal or subgoal becomes fully satisfied,  it and all 
its (recursive) subgoals are removed from the KB, and, if there is a direct
action is attached to its condition pattern, the direct action is triggered. 
When a direct action is triggered, this may indirectly cause one or more of the 
outcomes of the causal patterns it appears as a condition in to become
satisfied. This, in turn, may cause other goals or subgoals to become 
satisfied, hopefully resulting in a chain reaction that ultimately causes a
top-level goal to be satisfied.

## Play

**TODO**: Explain how play is necessary to learn causality before goals can
incorporate actions. (Otherwise, we get stuck because we can't learn causality
without taking action, but we can't take action without goals. The only 
solution is to play around by performing random actions to bootstrap the
learning of the consequences of each action.)
