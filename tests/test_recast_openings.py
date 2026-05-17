"""Tests for the recast_openings pipeline rule.

The rule paraphrases / reconstructs the opening of a paragraph (its
introduction) and of each sentence.  Exercised in isolation (single-rule
Pipeline) so each reconstruction can be asserted directly, plus end-to-end
determinism / robustness checks.  Assertions are deliberately robust:
presence / absence, non-emptiness and determinism -- never exact strings.
"""

import re
import unittest

from humanizer import Humanizer, Pipeline, list_tones
from humanizer.extra_rules import EXTRA_RULES

_ONLY = Pipeline(rules=["recast_openings"])


def _run(text, tone="professional", seed=7, strength=1.0):
    return Humanizer(
        tone=tone, strength=strength, seed=seed, pipeline=_ONLY
    ).humanize(text)


def _has_word(text, word):
    return re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE)


class RegistrationTests(unittest.TestCase):
    def test_rule_registered_and_in_pipelines(self):
        from humanizer.pipeline import DEFAULT_PIPELINE, TONE_PIPELINES

        self.assertIn("recast_openings", EXTRA_RULES)
        Pipeline(rules=["recast_openings"])
        self.assertIn("recast_openings", DEFAULT_PIPELINE)
        for name, rules in TONE_PIPELINES.items():
            self.assertIn("recast_openings", rules, name)

    def test_runs_before_lexical_substitution(self):
        from humanizer.pipeline import DEFAULT_PIPELINE

        self.assertLess(
            DEFAULT_PIPELINE.index("recast_openings"),
            DEFAULT_PIPELINE.index("lexical_substitution"),
        )


class MetaIntroductionTests(unittest.TestCase):
    def test_in_this_article_intro_is_reconstructed(self):
        r = _run("In this article, we will explore the benefits of testing.")
        low = r.text.lower()
        self.assertNotIn("in this article", low)
        self.assertNotIn("we will explore", low)
        self.assertTrue(_has_word(low, "benefits"))
        self.assertTrue(r.text.strip())

    def test_this_guide_will_show_intro_is_reconstructed(self):
        r = _run("This guide will walk you through the setup process.")
        self.assertFalse(r.text.lower().startswith("this guide"))
        self.assertTrue(_has_word(r.text, "setup"))

    def test_lets_dive_in_intro_is_reconstructed(self):
        r = _run("Let's dive into how the parser works.")
        self.assertNotIn("dive into", r.text.lower())
        self.assertTrue(_has_word(r.text, "parser"))


class OpeningFrameTests(unittest.TestCase):
    def test_there_is_x_that_is_rebuilt(self):
        r = _run("There is a bug that breaks the login flow.")
        low = r.text.lower()
        self.assertFalse(low.startswith("there is"))
        self.assertTrue(_has_word(low, "bug"))
        self.assertTrue(_has_word(low, "login"))

    def test_there_are_x_that_is_rebuilt(self):
        r = _run("There are several tools that help developers ship faster.")
        low = r.text.lower()
        self.assertFalse(low.startswith("there are"))
        self.assertTrue(_has_word(low, "tools"))
        self.assertTrue(_has_word(low, "developers"))

    def test_it_is_clear_that_becomes_adverb(self):
        r = _run("It is clear that the approach scales well.")
        low = r.text.lower()
        self.assertFalse(low.startswith("it is clear that"))
        self.assertTrue(low.startswith("clearly"))
        self.assertTrue(_has_word(low, "scales"))

    def test_throat_clearing_lead_in_is_dropped(self):
        r = _run("To begin with, the model needs clean data.")
        self.assertFalse(r.text.lower().startswith("to begin with"))
        self.assertTrue(_has_word(r.text, "model"))

    def test_nominalized_opener_becomes_verb(self):
        r = _run("The use of caching reduces latency a lot.")
        self.assertTrue(r.text.lower().startswith("using"))
        self.assertTrue(_has_word(r.text, "caching"))


class RobustnessTests(unittest.TestCase):
    def test_introduction_is_reconstructed_in_a_paragraph(self):
        para = (
            "In this post, we will discuss the design. "
            "The system is fast. It scales cleanly."
        )
        r = _run(para)
        self.assertNotIn("in this post", r.text.lower())
        self.assertTrue(_has_word(r.text, "design"))
        # The later sentences still survive.
        self.assertTrue(_has_word(r.text, "scales"))

    def test_plain_text_is_left_untouched(self):
        # No opening frame -> bit-for-bit unchanged, no logged change.
        src = "The cat sat on the mat. The dog ran outside quickly."
        r = _run(src)
        self.assertEqual(r.text, src)
        self.assertFalse(
            any(c.startswith("structure:") for c in r.changes)
        )

    def test_deterministic_with_seed(self):
        src = "In this guide, we will explore there is a trick that helps."
        a = _run(src, seed=21)
        b = _run(src, seed=21)
        self.assertEqual(a.text, b.text)
        self.assertEqual(a.changes, b.changes)

    def test_empty_and_whitespace_do_not_raise(self):
        for text in ("", "   ", "\n"):
            self.assertEqual(_run(text).text.strip(), "")

    def test_every_tone_runs_end_to_end(self):
        src = (
            "In this article, we will explore the idea. There is a method "
            "that works. It is clear that it helps. To begin with, try it."
        )
        for name in list_tones():
            with self.subTest(tone=name):
                res = Humanizer(
                    tone=name, strength=0.8, seed=11
                ).humanize(src)
                self.assertTrue(res.text.strip(), name)
                self.assertTrue(res.changes, name)
                self.assertNotIn("in this article", res.text.lower(), name)


if __name__ == "__main__":
    unittest.main()
