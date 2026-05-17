"""Tests for the reconstruction, citation and synonym-suggestion features.

Robust assertions only (types, ranges, invariants, determinism) -- never
exact rewritten strings.
"""

import unittest

from humanizer import (
    Humanizer,
    list_tones,
    pattern_inventory,
    suggest_synonyms,
)

CLAIMY = (
    "Studies show that 80 percent of users prefer this approach overall. "
    "Research indicates the data demonstrates a clear upward trend. "
    "The team shipped the update on Friday afternoon together."
)

MULTI_PARA = (
    "It is important to note that artificial intelligence is a very good "
    "technology. We should use it because it can make a decision.\n\n"
    "There are many tools that help people. In conclusion, it is a useful "
    "tool that we should adopt."
)


class SuggestSynonymTests(unittest.TestCase):
    def test_returns_list_of_strings(self):
        out = suggest_synonyms("important", "professional", 8)
        self.assertIsInstance(out, list)
        self.assertTrue(out)
        self.assertTrue(all(isinstance(s, str) and s for s in out))

    def test_never_returns_the_word_itself_or_commas(self):
        out = suggest_synonyms("good", "witty", 12)
        for s in out:
            self.assertNotEqual(s.lower(), "good")
            self.assertNotIn(",", s)

    def test_limit_is_respected(self):
        self.assertLessEqual(len(suggest_synonyms("important", "academic", 3)), 3)

    def test_light_verb_phrase_resolves(self):
        self.assertIn("use", [s.lower() for s in suggest_synonyms("make use of", "casual")])

    def test_unknown_word_and_tone_are_safe(self):
        self.assertEqual(suggest_synonyms("xyzzyqq", "casual"), [])
        self.assertEqual(suggest_synonyms("good", "not-a-tone"), [])
        self.assertEqual(suggest_synonyms("", "casual"), [])

    def test_every_tone_can_suggest(self):
        for t in list_tones():
            with self.subTest(tone=t):
                self.assertIsInstance(suggest_synonyms("important", t), list)


class CitationTests(unittest.TestCase):
    def test_off_by_default_adds_no_markers(self):
        r = Humanizer(tone="academic", strength=0.3, seed=1).humanize(CLAIMY)
        self.assertNotIn("[citation needed]", r.text)
        self.assertNotIn("[1]", r.text)
        self.assertNotIn("References", r.text)

    def test_placeholder_marks_claim_sentences(self):
        r = Humanizer(
            tone="casual", strength=0.2, seed=1, citations="placeholder"
        ).humanize(CLAIMY)
        self.assertIn("[citation needed]", r.text)

    def test_numbered_with_sources_caps_and_lists_refs(self):
        srcs = ["Smith J. (2021). A. Journal X.", "Doe A. (2020). B. Press Y."]
        r = Humanizer(
            tone="academic", strength=0.2, seed=1,
            citations="numbered", sources=srcs,
        ).humanize(CLAIMY)
        self.assertIn("[1]", r.text)
        self.assertIn("References", r.text)
        for s in srcs:
            self.assertIn(s, r.text)
        # Never more numbered markers than supplied sources.
        self.assertNotIn("[3]", r.text)

    def test_numbered_without_sources_is_safe(self):
        r = Humanizer(
            tone="academic", strength=0.2, seed=1, citations="numbered"
        ).humanize(CLAIMY)
        self.assertIsInstance(r.text, str)
        self.assertTrue(r.text.strip())

    def test_invalid_mode_falls_back_to_off(self):
        r = Humanizer(
            tone="casual", strength=0.2, seed=1, citations="bogus"
        ).humanize(CLAIMY)
        self.assertNotIn("[citation needed]", r.text)


class RestructureTests(unittest.TestCase):
    def test_default_on_is_deterministic(self):
        a = Humanizer(tone="professional", strength=0.7, seed=5).humanize(CLAIMY)
        b = Humanizer(tone="professional", strength=0.7, seed=5).humanize(CLAIMY)
        self.assertEqual(a.text, b.text)
        self.assertTrue(a.text.strip())

    def test_toggle_changes_behaviour_or_logs(self):
        on = Humanizer(
            tone="professional", strength=0.8, seed=5, restructure=True
        ).humanize(CLAIMY)
        off = Humanizer(
            tone="professional", strength=0.8, seed=5, restructure=False
        ).humanize(CLAIMY)
        self.assertTrue(on.text.strip())
        self.assertTrue(off.text.strip())
        self.assertFalse(
            any(c.startswith("restructure") for c in off.changes)
        )

    def test_paragraph_structure_is_preserved(self):
        r = Humanizer(
            tone="casual", strength=0.5, seed=3
        ).humanize(MULTI_PARA)
        self.assertIn("\n\n", r.text)
        blocks = [b for b in r.text.split("\n\n") if b.strip()]
        self.assertGreaterEqual(len(blocks), 2)

    def test_all_tones_run_with_restructure(self):
        for t in list_tones():
            with self.subTest(tone=t):
                r = Humanizer(tone=t, strength=0.6, seed=9).humanize(CLAIMY)
                self.assertTrue(r.text.strip())


class PatternInventoryTests(unittest.TestCase):
    def test_inventory_shape_and_positivity(self):
        for t in list_tones():
            with self.subTest(tone=t):
                inv = pattern_inventory(t)
                self.assertIsInstance(inv, dict)
                for k in (
                    "structural_transforms", "reframe_templates", "pivots",
                    "nominalizations", "effective_patterns",
                ):
                    self.assertIn(k, inv)
                    self.assertIsInstance(inv[k], int)
                    self.assertGreater(inv[k], 0)
                self.assertGreaterEqual(
                    inv["effective_patterns"], inv["reframe_templates"]
                )


if __name__ == "__main__":
    unittest.main()
