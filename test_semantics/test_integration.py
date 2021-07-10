import unittest

from semantics.kb_layer.knowledge_base import KnowledgeBase
from semantics.kb_layer.orm import Time, Instance


class TestIntegration(unittest.TestCase):

    def test_statement_update(self):
        """Create an empty knowledge base. Add the statement, 'An apple fell,' to the contents of
        the knowledge base by updating it with a pattern. Verify that the knowledge was added by
        querying the knowledge base afterward with the same pattern."""

        kb = KnowledgeBase()

        # Define "singular" and "plural", for the purposes of matching. This will normally be done
        # just once, when the knowledge base is first created.
        singular = kb.get_divisibility('singular', add=True)
        # plural = kb.get_divisibility('plural', add=True)

        # Create a pattern that will match "an apple".
        # NOTES:
        #   * Selectors act to modulate search in the knowledge base, whereas patterns determine
        #     what graph structures must be present for a match to occur.
        #   * The 'match' attribute of selectors acts as a placeholder for the observation or
        #     instance being matched. Setting an attribute of 'match' tells the selector that the
        #     matched observation or instance must have that value for the given attribute.
        #   * Selector match placeholders can be updated repeatedly. The same rules of evidence that
        #     apply to graph structures also apply to selector match placeholder structures. This
        #     means that each time you modify a selector match placeholder, this is weighed against
        #     previous usage to adjust the selector's behavior incrementally. You can also accept
        #     or reject a match returned by update() or query() to modulate selector behavior in a
        #     similar fashion using contextual cues, rather than (or in addition to) defining the
        #     selector's behavior up front like this.
        #   * When a string is passed to add_pattern(), it is treated as a kind name. The word and
        #     kind are automatically added, if necessary. If there are multiple kinds with the same
        #     name, the pattern connects to all of them with equally divided evidence, so that the
        #     intended meaning can be determined contextually based on the structural aspects of
        #     the pattern and the matched subgraph(s). Accepting or rejecting a match returned by
        #     update() or query() will apply evidence towards the pattern's connection to the
        #     matched kind and against the pattern's connections to the other kinds sharing the same
        #     name, influencing later match results for that same pattern.
        selector_an = kb.get_selector_pattern('an', add=True)
        selector_an.match.divisibility.set(singular)
        pattern_an_apple = kb.add_pattern(Instance)
        pattern_an_apple.selectors.add(selector_an)
        pattern_an_apple.match.kinds.update(kb.get_word('apple', add=True).kinds)

        # Create a pattern that will match "an apple fell".
        # NOTES:
        #   * kb.context.now is a built-in pattern that *contextually* matches the current time when
        #     the call to kb.update() or kb.query() is made. This is in contrast to kb.now(), which
        #     returns the *literal* current time.
        #   * During matching, the 'PRECEDES' relation for time patterns does not have to directly
        #     match two times connected by an edge of that type. It will also match two times for
        #     which the time stamps are in the correct order. This is for efficiency's sake, so we
        #     don't have to add an edge connecting every pair of times with time stamps.
        pattern_before_now = kb.add_pattern(Time)
        pattern_before_now.children.add(kb.context.now)
        pattern_before_now.match.later_times.add(kb.context.now.match)
        selector_ed_suffix = kb.get_selector_pattern('-ed', add=True)
        selector_ed_suffix.match.time.set(pattern_before_now)
        pattern_an_apple_fell = kb.add_pattern(Instance)
        pattern_an_apple_fell.selectors.add(selector_ed_suffix)
        pattern_an_apple_fell.children.add(pattern_an_apple)
        pattern_an_apple_fell.match.kinds.update(kb.get_word('fall', add=True).kinds)
        pattern_an_apple_fell.match.actor.set(pattern_an_apple.match)

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        # NOTES:
        #   * A match object is an immutable mapping from pattern components to graph elements.
        #   * Applying a match tells the knowledge base to update the graph to incorporate the
        #     structure of the pattern into the graph using the given elements, making the matched
        #     subgraph isomorphic to the pattern, and then apply positive evidence to the subgraph.
        #   * Unconditionally applying the first match and then breaking has the effect of taking
        #     whatever match the knowledge base deems most probable based on previous evidence
        #     (which is none, in this case).
        for match in pattern_an_apple_fell.find_matches(partial=True):
            # We must apply a match, or else no updates to the graph will take place.
            match.apply()
            break

        # Take note of the time at which the statement was made. Since the statement was in past
        # tense, the event should precede this time.
        current_time = kb.now()

        # Verify that there is exactly one match in the database for the pattern, and that the
        # observations have the expected structural relationships.
        # NOTES:
        #   * The matched subgraph may only be *approximately* isomorphic to the pattern being
        #     matched. The is_isomorphic() method of the match will tell you whether the match is
        #     exact or merely approximate.
        #   * For queries, as opposed to updates, we use match.accept() instead of match.apply() to
        #     apply positive evidence to the match without modifying the graph's structure.
        match_count = 0
        for match in pattern_an_apple_fell.find_matches():
            match_count += 1
            self.assertTrue(match.is_isomorphic())
            # Below, we explicitly perform all the checks that were performed in the above call
            # to 'is_isomorphic()'.
            observed_fall = match[pattern_an_apple_fell]
            observed_apple = match[pattern_an_apple]
            self.assertEqual(observed_apple, observed_fall.actor.get())
            # NOTE: The 'precedes' method should return an Evidence instance, which is then
            #       automatically converted to a boolean value for the assertion.
            self.assertTrue(observed_fall.time.get().precedes(current_time))
        self.assertEqual(1, match_count)
