"""Tests for the strip_ai_red_flags pipeline rule.

Exercises the rule in isolation (a single-rule Pipeline) so each AI
"red flag" can be asserted directly, plus a few end-to-end checks through
the public Humanizer API.  Assertions are deliberately robust: presence /
absence, inequality, determinism and non-emptiness -- never exact strings.
"""

import re
import unittest

from humanizer import Humanizer, Pipeline, list_tones
from humanizer.extra_rules import EXTRA_RULES

# Only this rule, at full strength, so the gated passes fire deterministically.
_ONLY = Pipeline(rules=["strip_ai_red_flags"])


def _run(text, tone="professional", seed=7, strength=1.0):
    return Humanizer(
        tone=tone, strength=strength, seed=seed, pipeline=_ONLY
    ).humanize(text)


def _has_word(text, word):
    return re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE)


class RuleRegistrationTests(unittest.TestCase):
    def test_rule_is_registered_and_selectable(self):
        self.assertIn("strip_ai_red_flags", EXTRA_RULES)
        # Constructing a pipeline with the rule must not raise.
        Pipeline(rules=["strip_ai_red_flags"])

    def test_rule_is_in_every_default_and_tone_pipeline(self):
        from humanizer.pipeline import DEFAULT_PIPELINE, TONE_PIPELINES

        self.assertIn("strip_ai_red_flags", DEFAULT_PIPELINE)
        for name, rules in TONE_PIPELINES.items():
            self.assertIn("strip_ai_red_flags", rules, name)


class EmDashTests(unittest.TestCase):
    def test_em_dash_is_removed(self):
        r = _run("The result is clear — the system works — and it is fast.")
        self.assertNotIn("—", r.text)
        self.assertTrue(r.text.strip())

    def test_double_hyphen_dash_is_removed(self):
        r = _run("It is fast -- really fast -- in every test.")
        self.assertNotIn("--", r.text)

    def test_numeric_range_is_left_alone(self):
        # A bare hyphen with no surrounding spaces is not a dash tell.
        r = _run("The model scored 10-20 points on the benchmark.")
        self.assertIn("10-20", r.text)


class BuzzwordTests(unittest.TestCase):
    def test_corporate_buzzwords_are_replaced(self):
        src = (
            "We will leverage and elevate the robust, innovative platform "
            "to empower the team."
        )
        r = _run(src)
        for bw in ("leverage", "elevate", "robust", "innovative", "empower"):
            self.assertFalse(_has_word(r.text, bw), bw)
        self.assertTrue(r.text.strip())

    def test_buzzword_change_is_logged(self):
        r = _run("This delivers seamless synergy and seamless delivery.")
        self.assertTrue(any("buzzword" in c for c in r.changes))


class PraiseAndPreambleTests(unittest.TestCase):
    def test_impersonal_praise_is_removed(self):
        r = _run("That was a great question, and the data is clear.")
        self.assertFalse(_has_word(r.text, "great question"))
        self.assertTrue(_has_word(r.text, "data"))

    def test_filler_preamble_is_dropped(self):
        r = _run("In other words, the approach simply works.")
        self.assertFalse(r.text.lower().startswith("in other words"))
        self.assertTrue(_has_word(r.text, "works"))


class AnalogyTests(unittest.TestCase):
    def test_cliched_analogy_is_defused(self):
        r = _run("The team runs like a well-oiled machine every day.")
        self.assertNotIn("well-oiled machine", r.text.lower())
        self.assertTrue(r.text.strip())


class ParallelStructureTests(unittest.TestCase):
    def test_not_only_but_also_is_flattened(self):
        r = _run("The tool is not only fast but also affordable.")
        low = r.text.lower()
        self.assertNotIn("not only", low)
        self.assertTrue(_has_word(low, "fast"))
        self.assertTrue(_has_word(low, "affordable"))

    def test_it_is_not_just_x_its_y_is_flattened(self):
        r = _run("It's not just a tool, it's a complete platform.")
        low = r.text.lower()
        self.assertNotIn("not just", low)
        self.assertTrue(_has_word(low, "platform"))


class RuleOfThreeTests(unittest.TestCase):
    def test_triad_cadence_is_broken_without_dropping_items(self):
        r = _run("The design is fast, cheap, and simple.")
        low = r.text.lower()
        # Every item survives.
        for item in ("fast", "cheap", "simple"):
            self.assertTrue(_has_word(low, item), item)
        # The textbook "a, b, and c" cadence is gone.
        self.assertIsNone(re.search(r",\s*\w+,?\s+and\s+\w+", low))


class RobustnessTests(unittest.TestCase):
    def test_deterministic_with_seed(self):
        src = "It's not only robust but also seamless — truly remarkable."
        a = _run(src, seed=42)
        b = _run(src, seed=42)
        self.assertEqual(a.text, b.text)
        self.assertEqual(a.changes, b.changes)

    def test_empty_and_whitespace_do_not_raise(self):
        for text in ("", "   ", "\n"):
            self.assertEqual(_run(text).text.strip(), "")

    def test_praise_only_sentence_is_not_emptied(self):
        # A sentence that is *only* praise must survive (deletion would drop
        # it entirely); content sentences are still cleaned.
        r = _run("Great question! The robust answer is simple.")
        self.assertTrue(r.text.strip())
        self.assertFalse(_has_word(r.text, "robust"))

    def test_every_tone_runs_end_to_end_on_red_flag_text(self):
        src = (
            "It is not just good, it's transformative — a true game-changer. "
            "It is fast, cheap, and scalable. We leverage cutting-edge "
            "innovation. In other words, it works."
        )
        for name in list_tones():
            with self.subTest(tone=name):
                res = Humanizer(
                    tone=name, strength=0.8, seed=11
                ).humanize(src)
                self.assertTrue(res.text.strip(), name)
                self.assertTrue(res.changes, name)
                self.assertNotIn("—", res.text, name)


if __name__ == "__main__":
    unittest.main()
