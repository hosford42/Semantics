# Coordinates

**TODO**: This functionality is only partially implemented. Also, 'coordinate' 
and 'dimension' will probably be renamed to 'quantity' and 'unit'.

## Brainstorming

### Session 1

Suppose we have a spatial coordinate, and we want to store this in the 
knowledge base in a useful and meaningful way. What do we do with x, y, and z? 
I'm thinking we should have Place alongside Time in the ORM, with optional 
coordinates. Probably the coordinate space itself should be in the ORM, along 
with its accompanying distance metric, and the place should identify which 
space it belongs to.

Since we are adding various data nodes (time, place, spelling, etc.) we should 
probably have a unified framework for these kinds of nodes, treating them 
differently from others. One important difference is that unlike other 
elements, data nodes do not have ambiguous or uncertain identities. We
can always point to a unique, specific vertex that corresponds to a data point, 
and we can look up the vertex again later given the data point. Another 
difference is their behavior with respect to patterns and pattern matching. 
Data nodes cannot appear as match representatives in patterns, and when 
patterns match against them, we may have to clone them (minus the attached data 
point) to avoid confabulating memories. 

### Session 2

Upon further reflection, I think not only should places and coordinate systems 
get their own nodes, but each axis of a coordinate system and point along it 
should get its own node. In the current Time implementation, we automatically
connect specific points in time (those with a time stamp) together with a 
PRECEDES relation to enable searching the timeline and comparing times. Times 
without time stamps can then be hooked into this backbone timeline, enabling us 
to set more abstract bounds and ranges on them without knowing their precise 
identities.

Generalizing to higher-dimensional coordinate spaces, we will run into a couple 
of problems. Let's take 2D spatial coordinates, for example. Suppose we want to 
check if point A is to the left of point B. If we try to sequence points along 
the x-axis with a LEFT_OF relation, things break down when we start adding 
multiple points that have the same x coordinate. If we have 10 points at `x=0`
and 10 more at `x=1`, with none in between, we would have to add 100 LEFT_OF 
edges in this case. This could rapidly become very unmanageable and cause 
searching the space to slow to a crawl. Another issue is that we would have to 
have a dedicated edge label for every dimension of every coordinate space, and 
a way to map between the edge labels and the dimensions they refer to.

Both of these issues can be resolved by instead isolating each dimension along 
its own separate sequence. Every single point with `x=0` would have its own 
vertex with a link to the same `x=0` vertex. The `x=0` vertex would know its 
position along the dimension's axis (with a data point), the dimension index in 
the coordinate space (with another data point), and the coordinate space the 
dimension belongs to (with an edge to the coordinate space's vertex). With this 
structure, we can use the same PRECEDES label to link all specific points along 
the x-axis into a backbone with a single chain of edges, as is currently done 
for timestamped Times. To find out whether a given position is to the left of 
another position, we would search the coordinates associated with each position 
for the x coordinate of that position, and then search for a PRECEDES path from 
the first position's x coordinate to the second position's x coordinate. 

There are additional benefits to this approach. We can implement specialized 
search mechanisms that take advantage of the structure. For example, if we 
search to the right of the first position's x coordinate, we can instantly 
prune the search if we reach a stamped x coordinate with a stamp value greater 
than the one we are searching for. If we reach a stamped x coordinate less than
or equal to the one we are searching for, we can instantly return success and 
terminate the search. Another side benefit is that we can generalize the code 
across all the different coordinate spaces instead of writing tailored code for 
each. This could have a significant beneficial impact on code complexity in 
pattern matching, the KB interface, etc.

# Session 3

I was going to use 'quantity' and 'unit' as the fundamental terms to define
numerical values, but I had a realization. It's not enough to specify units.
There are multiple factors required to determine whether you can compare, add,
or otherwise compute with two numbers. Those factors include units, axis, and 
origin at the least. Depending on the context, there may be others, such as the 
time when the measurements were taken. The point is, the one thing that remains 
invariant in all this is the numerical values arranged along the number line. 
Units, axis, origin -- these are all means of mapping consistently from a 
contextual setting to the invariant number line in order to make use of it 
without modification. So the fundamental abstractions are not 'quantity' and 
'unit', but rather, 'number' and 'number line'. We still might need different 
number lines if the type of number isn't directly comparable -- e.g., datetime 
versus float -- but we definitely don't need multiple number lines just because 
a standardized unit has been changed out for another one, or because we changed 
axes. (The only reason we might want a separate line for datetime values is 
because the units vary in size depending on where along the line you are, 
following obscure rules, which can make it difficult to translate between 
values on a datetime line versus a float line. It's a matter of convenience, 
not of necessity.)

One question does remain: Do we want separate lines for floats versus ints?
If we use separate lines, then we can't directly compare them. But if we use
the same line, we need special mechanisms to distinguish ints from floats,
as well as a way to tell the system when one integer is the *next* integer
after a given one. I suspect, though, that the special mechanisms would have
to be present regardless. If we have two separate number lines, we have to
map between them, but we are free to treat PRECEDES as equivalent to SUCCESSOR.
If we use a single number line, we have to tag integers as such, and provide a
SUCCESSOR link in addition to a PRECEDES link, but we can directly compare ints
and floats. I think the advantages of putting them on a single line together
outweigh the disadvantages, so that's the route I'll take.
