# Triggers

A trigger is a pattern attached to a vertex in the graph which is activated for new
matches when adjacent edges are added to that vertex, together with some sort of
action which is taken on the new match. For example, suppose we want to encode the
fact, "Every human is mortal." Then we create a pattern for this, and attach it as a
trigger to the "human" kind, triggered by new inbound "KIND" edges from instances to
the "human" kind. The action assigned to this trigger will be to automatically apply
new matches. When a new instance of "human" is added, the pattern will partially match
against it, and the match will then be applied, automatically adding the property
"mortal" to the new instance.

Triggers can have other actions instead of automatically applying a partial match.
Suppose the user asks, "What are some examples of foods?" and then, after exhausting
the answers the system currently has available, the user says, "Tell me later if you
think of something new later." We can create a pattern for "What are some examples of
foods?" and attach it to the "food" kind as a trigger, with an action of reporting new
matches back to the user.

Yet another trigger action might be to take physical or goal-oriented action in
response to a new match. For example, "Always put empty soda cans you find in the
trash." We attach a pattern to the "can" kind which matches "empty soda can" and
assigns a goal state to the can being in the trash, initiating the appropriate
contextual behavior. (Of course, this depends on goal-oriented mechanisms and external
actions being implemented first.)
