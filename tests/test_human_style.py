"""Tests for the humanize_phrasing rule (the "Human-version" style).

The rule simplifies heavy academic wording, softens over-strong claims,
and generalizes long specific enumerations.  Exercised in isolation
(single-rule Pipeline) plus end-to-end determinism / robustness checks.
Assertions are robust: presence / absence, non-emptiness, determinism.
"""

import re
import unittest

from humanizer import Humanizer, Pipeline, get_tone, list_tones
from humanizer.extra_rules import EXTRA_RULES

_ONLY = Pipeline(rules=["humanize_phrasing"])


def _run(text, tone="academic", seed=7, strength=1.0):
    return Humanizer(
        tone=tone, strength=strength, seed=seed, pipeline=_ONLY
    ).humanize(text)


def _has_word(text, word):
    return re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE)


class RegistrationTests(unittest.TestCase):
    def test_registered_and_in_pipelines(self):
        from humanizer.pipeline import DEFAULT_PIPELINE, TONE_PIPELINES

        self.assertIn("humanize_phrasing", EXTRA_RULES)
        Pipeline(rules=["humanize_phrasing"])
        self.assertIn("humanize_phrasing", DEFAULT_PIPELINE)
        for name, rules in TONE_PIPELINES.items():
            self.assertIn("humanize_phrasing", rules, name)

    def test_runs_after_lexical_substitution(self):
        from humanizer.pipeline import DEFAULT_PIPELINE

        self.assertGreater(
            DEFAULT_PIPELINE.index("humanize_phrasing"),
            DEFAULT_PIPELINE.index("lexical_substitution"),
        )


class SimplifyTests(unittest.TestCase):
    def test_heavy_academic_wording_is_simplified(self):
        r = _run(
            "The system has the ability to detect objects with respect to size."
        )
        low = r.text.lower()
        self.assertNotIn("has the ability to", low)
        self.assertNotIn("with respect to", low)
        self.assertTrue(_has_word(low, "detect"))

    def test_remains_dependent_on_is_simplified(self):
        r = _run("YOLOv8 remains dependent on visual access to the object.")
        self.assertNotIn("remains dependent on", r.text.lower())
        self.assertTrue(_has_word(r.text, "visual"))


class SoftenClaimTests(unittest.TestCase):
    def test_demonstrates_that_is_hedged(self):
        r = _run("The experiment demonstrates that the method proves that it works.")
        low = r.text.lower()
        self.assertNotIn("demonstrates that", low)
        self.assertNotIn("proves that", low)
        self.assertIn("suggests that", low)

    def test_support_the_use_of_is_softened(self):
        r = _run("These studies support the use of YOLOv8 in the system.")
        low = r.text.lower()
        self.assertNotIn("support the use of", low)
        self.assertTrue(_has_word(low, "yolov8"))

    def test_will_improve_is_hedged(self):
        r = _run("The upgrade will improve accuracy and will increase speed.")
        low = r.text.lower()
        self.assertNotIn("will improve", low)
        self.assertNotIn("will increase", low)
        self.assertIn("may", low)


class EnumerationTests(unittest.TestCase):
    def test_long_enumeration_is_generalized(self):
        r = _run(
            "It selects bags, laptops, mobile phones, wallets, and keys daily."
        )
        low = r.text.lower()
        # Lead items survive; the tail is generalized, nothing fabricated.
        self.assertTrue(_has_word(low, "bags"))
        self.assertTrue(_has_word(low, "laptops"))
        self.assertTrue(
            any(t in low for t in ("others", "the like", "other things"))
        )
        # The full five-item list no longer appears verbatim.
        self.assertFalse(_has_word(low, "keys") and _has_word(low, "wallets"))

    def test_short_list_is_left_alone(self):
        src = "It detects bags and keys."
        r = _run(src)
        self.assertEqual(r.text, src)


class AcademicTransitionTests(unittest.TestCase):
    def test_academic_tone_has_transition_starters(self):
        starters = get_tone("academic").starters
        for t in ("Furthermore,", "Moreover,", "Thus,"):
            self.assertIn(t, starters)


class RobustnessTests(unittest.TestCase):
    def test_plain_text_is_left_untouched(self):
        src = "The cat sat on the mat. The dog ran outside quickly."
        r = _run(src)
        self.assertEqual(r.text, src)
        self.assertFalse(any(c.startswith("style:") for c in r.changes))

    def test_deterministic_with_seed(self):
        src = (
            "The study demonstrates that A, B, C, D, and E remain dependent "
            "on visual access and support the use of the tool."
        )
        a = _run(src, seed=31)
        b = _run(src, seed=31)
        self.assertEqual(a.text, b.text)
        self.assertEqual(a.changes, b.changes)

    def test_empty_and_whitespace_do_not_raise(self):
        for text in ("", "   ", "\n"):
            self.assertEqual(_run(text).text.strip(), "")

    def test_every_tone_runs_end_to_end(self):
        src = (
            "The framework demonstrates that detection is capable of "
            "handling small target size, obstruction, lighting variation, "
            "and background interference. It supports the use of the system."
        )
        for name in list_tones():
            with self.subTest(tone=name):
                res = Humanizer(
                    tone=name, strength=0.8, seed=11
                ).humanize(src)
                self.assertTrue(res.text.strip(), name)
                self.assertTrue(res.changes, name)


if __name__ == "__main__":
    unittest.main()
