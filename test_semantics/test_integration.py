import time
import unittest

from semantics.data_types.typedefs import TimeStamp
from semantics.kb_layer.knowledge_base import KnowledgeBase


class TestIntegration(unittest.TestCase):

    def test_statement_update(self):
        kb = KnowledgeBase()

        # Define "singular" and "plural", for the purposes of matching.
        phrase_number_kind = kb.add_kind('%PHRASE_NUMBER%')
        singular = kb.add_instance(phrase_number_kind)
        singular.name.set(kb.get_word('singular', add=True))
        plural = kb.add_instance(phrase_number_kind)
        plural.name.set(kb.get_word('plural', add=True))

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
        selector_an = kb.get_selector('an', add=True)
        selector_an.match.phrase_number.set(singular)
        pattern_an_apple = kb.add_pattern('apple')
        pattern_an_apple.selector.set(selector_an)

        # Create a pattern that will match "an apple fell".
        # NOTES:
        #   * kb.patterns.match_start_time() returns a built-in pattern that contextually matches
        #     the current time when the call to kb.update() or kb.query() is made.
        #   * Getting an attribute of the selector's match placeholder returns another placeholder
        #     with the appropriate relationship to the match placeholder.
        #   * Calling a method on the 'predicate' attribute of a match placeholder indicates that
        #     the indicated method of the matched value must return a True value for a match to take
        #     place.
        selector_ed_suffix = kb.get_selector('-ed', add=True)
        selector_ed_suffix.match.time.get().predicate.precedes(kb.patterns.match_start_time())
        pattern_an_apple_fell = kb.add_pattern('fall')
        pattern_an_apple_fell.selector.set(selector_ed_suffix)
        pattern_an_apple_fell.actor.set(pattern_an_apple)

        # Apply the pattern as a statement to update the graph. This should modify the structure of
        # the graph by adding (indirect) observations which structurally mirror the pattern, and
        # which can later be matched by queries.
        # NOTES:
        #   * A match object is an immutable mapping from pattern components to graph elements.
        #   * Accepting a match returned by update() tells the knowledge base to update the graph to
        #     incorporate the structure of the pattern into the graph using the given elements,
        #     making the matched subgraph isomorphic to the pattern, and then apply positive
        #     evidence to the subgraph.
        #   * Unconditionally accepting the first match and then breaking has the effect of taking
        #     whatever match the knowledge base deems most probable based on previous evidence
        #     (which is none, in this case).
        for match in kb.update(pattern_an_apple_fell):
            # We must accept a match, or else no updates to the graph will take place.
            match.accept()
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
        match_count = 0
        for match in kb.query(pattern_an_apple_fell):
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
