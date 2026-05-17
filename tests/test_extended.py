"""Extended test suite for the AI Humanizer.

Uses ONLY the stable public API:

    from humanizer import Humanizer, analyze, get_tone, list_tones, Pipeline

plus the advanced metrics module (built in parallel):

    from humanizer.advanced_metrics import (
        bigram_perplexity, mtld, sentence_burstiness_profile,
        humanity_score, detailed_report,
    )

All assertions are deliberately robust: types, ranges, comparative /
monotone properties, non-empty and inequality checks -- never exact
rewritten strings or exact metric values.
"""

import os
import unittest

from humanizer import Humanizer, analyze, get_tone, list_tones, Pipeline

# The advanced metrics module is being built by a parallel agent.  Importing
# it may fail (module missing or a name mismatch); that is acceptable ONLY
# for these advanced-metrics tests.  Every test that relies solely on the
# stable humanizer API must still pass regardless.
try:  # pragma: no cover - exercised indirectly
    from humanizer.advanced_metrics import (
        bigram_perplexity,
        mtld,
        sentence_burstiness_profile,
        humanity_score,
        detailed_report,
    )

    _ADVANCED_OK = True
    _ADVANCED_ERR = None
except Exception as exc:  # noqa: BLE001 - we want any import failure
    _ADVANCED_OK = False
    _ADVANCED_ERR = exc

_requires_advanced = unittest.skipUnless(
    _ADVANCED_OK,
    f"humanizer.advanced_metrics unavailable: {_ADVANCED_ERR!r}",
)

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "examples")

# A deliberately robotic, low-diversity, uniform-length sample.
ROBOTIC_SAMPLE = (
    "It is important to note that the system is a very good system. "
    "It is important to note that the system can help people in many ways. "
    "In conclusion, the system is a very good system and a very important "
    "system. Overall, it is important to note that people should use the "
    "system because the system is good and the system is fast and the "
    "system is good for many people in many different situations."
)


def _read_example(tone_name):
    """Read examples/<tone>.in.txt via a path relative to this test file."""
    path = os.path.join(EXAMPLES_DIR, f"{tone_name}.in.txt")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().strip()


class ExampleFileTests(unittest.TestCase):
    """Every tone's example input file exists and is bland AI-ish prose."""

    def test_example_files_exist_and_nonempty(self):
        for name in list_tones():
            text = _read_example(name)
            self.assertTrue(text.strip(), name)
            # Inputs are intentionally repetitive/AI-sounding.
            self.assertGreaterEqual(len(text.split()), 30, name)

    def test_example_files_have_several_sentences(self):
        for name in list_tones():
            text = _read_example(name)
            # 4-7 sentences of bland prose -> at least a few terminators.
            terminators = sum(text.count(c) for c in ".!?")
            self.assertGreaterEqual(terminators, 4, name)


class ToneHumanizeTests(unittest.TestCase):
    """Every tone humanizes its matching example to changed, non-empty text."""

    def test_each_tone_humanizes_its_example(self):
        for name in list_tones():
            with self.subTest(tone=name):
                source = _read_example(name)
                result = Humanizer(tone=name, strength=0.8, seed=11).humanize(
                    source
                )
                self.assertTrue(result.text.strip(), name)
                self.assertNotEqual(result.text, result.original, name)
                self.assertTrue(result.changes, name)
                self.assertEqual(result.tone, name)

    def test_humanize_logs_change_descriptions(self):
        source = _read_example("professional")
        result = Humanizer(tone="professional", strength=0.9, seed=2).humanize(
            source
        )
        self.assertTrue(all(isinstance(c, str) for c in result.changes))
        self.assertGreater(len(result.changes), 0)

    def test_all_tones_run_on_robotic_sample(self):
        for name in list_tones():
            with self.subTest(tone=name):
                r = Humanizer(tone=name, strength=0.6, seed=7).humanize(
                    ROBOTIC_SAMPLE
                )
                self.assertTrue(r.text.strip(), name)


class DeterminismTests(unittest.TestCase):
    def test_same_seed_is_deterministic(self):
        a = Humanizer(tone="casual", strength=0.7, seed=99).humanize(
            ROBOTIC_SAMPLE
        )
        b = Humanizer(tone="casual", strength=0.7, seed=99).humanize(
            ROBOTIC_SAMPLE
        )
        self.assertEqual(a.text, b.text)
        self.assertEqual(a.changes, b.changes)

    def test_different_seeds_differ(self):
        a = Humanizer(tone="storytelling", strength=0.7, seed=1).humanize(
            ROBOTIC_SAMPLE
        )
        b = Humanizer(tone="storytelling", strength=0.7, seed=2).humanize(
            ROBOTIC_SAMPLE
        )
        self.assertNotEqual(a.text, b.text)


class StrengthTests(unittest.TestCase):
    def test_strength_extremes_both_run(self):
        low = Humanizer(tone="friendly", strength=0.0, seed=4).humanize(
            ROBOTIC_SAMPLE
        )
        high = Humanizer(tone="friendly", strength=0.9, seed=4).humanize(
            ROBOTIC_SAMPLE
        )
        self.assertTrue(low.text.strip())
        self.assertTrue(high.text.strip())

    def test_higher_strength_changes_at_least_as_many(self):
        # Robust / soft property: equality is allowed, only assert >=.
        low = Humanizer(tone="persuasive", strength=0.0, seed=8).humanize(
            ROBOTIC_SAMPLE
        )
        high = Humanizer(tone="persuasive", strength=0.9, seed=8).humanize(
            ROBOTIC_SAMPLE
        )
        self.assertGreaterEqual(len(high.changes), len(low.changes))


class StableMetricsTests(unittest.TestCase):
    """Sanity checks on the built-in analyze() metrics (stable API)."""

    def test_analyze_returns_expected_types(self):
        m = analyze(ROBOTIC_SAMPLE)
        self.assertIsInstance(m.word_count, int)
        self.assertIsInstance(m.perplexity, float)
        self.assertIsInstance(m.burstiness, float)
        self.assertIsInstance(m.mattr, float)

    def test_analyze_handles_empty_and_one_word(self):
        for text in ("", "hello"):
            m = analyze(text)
            self.assertGreaterEqual(m.word_count, 0)
            self.assertIsInstance(m.perplexity, float)

    def test_humanized_robotic_text_is_lexically_richer(self):
        r = Humanizer(tone="casual", strength=0.9, seed=5).humanize(
            ROBOTIC_SAMPLE
        )
        # Repetitive input -> humanized output should be at least as rich.
        self.assertGreaterEqual(
            r.metrics_after.mattr, r.metrics_before.mattr - 1e-9
        )

    def test_custom_pipeline_subset_via_stable_api(self):
        pipe = Pipeline(rules=["strip_ai_tells"])
        r = Humanizer(tone="academic", seed=1, pipeline=pipe).humanize(
            ROBOTIC_SAMPLE
        )
        self.assertNotIn("in conclusion", r.text.lower())

    def test_get_tone_round_trips_through_list_tones(self):
        for name in list_tones():
            tone = get_tone(name)
            self.assertEqual(tone.name, name)


@_requires_advanced
class AdvancedMetricsTypeTests(unittest.TestCase):
    """advanced_metrics: correct types + graceful empty / one-word handling."""

    def test_bigram_perplexity_type(self):
        val = bigram_perplexity(ROBOTIC_SAMPLE)
        self.assertIsInstance(val, (int, float))
        self.assertGreaterEqual(float(val), 0.0)

    def test_mtld_type(self):
        val = mtld(ROBOTIC_SAMPLE)
        self.assertIsInstance(val, (int, float))
        self.assertGreaterEqual(float(val), 0.0)

    def test_sentence_burstiness_profile_type(self):
        prof = sentence_burstiness_profile(ROBOTIC_SAMPLE)
        # A "profile" should be an iterable/collection, not a scalar.
        self.assertTrue(hasattr(prof, "__len__") or hasattr(prof, "__iter__"))

    def test_humanity_score_type(self):
        val = humanity_score(ROBOTIC_SAMPLE)
        self.assertIsInstance(val, (int, float))

    def test_detailed_report_type(self):
        report = detailed_report(ROBOTIC_SAMPLE)
        self.assertIsInstance(report, (dict, str))

    def test_empty_and_one_word_do_not_raise(self):
        for text in ("", " ", "word"):
            # None of these should raise on any advanced metric.
            bigram_perplexity(text)
            mtld(text)
            sentence_burstiness_profile(text)
            humanity_score(text)
            detailed_report(text)


@_requires_advanced
class AdvancedMetricsBehaviourTests(unittest.TestCase):
    """advanced_metrics: comparative/monotone behaviour, kept tolerant."""

    def test_humanized_text_has_higher_mtld(self):
        r = Humanizer(tone="casual", strength=0.9, seed=5).humanize(
            ROBOTIC_SAMPLE
        )
        before = float(mtld(r.original))
        after = float(mtld(r.text))
        self.assertGreater(after, before)

    def test_humanized_humanity_score_not_worse(self):
        r = Humanizer(tone="witty", strength=0.9, seed=3).humanize(
            ROBOTIC_SAMPLE
        )
        before = float(humanity_score(r.original))
        after = float(humanity_score(r.text))
        # Tolerant: humanized should be >= original within a small margin.
        self.assertGreaterEqual(after, before - 1.0)

    def test_detailed_report_runs_for_every_tone(self):
        for name in list_tones():
            with self.subTest(tone=name):
                r = Humanizer(tone=name, strength=0.7, seed=6).humanize(
                    _read_example(name)
                )
                report = detailed_report(r.text)
                self.assertIsInstance(report, (dict, str))
                self.assertTrue(len(report) > 0)


if __name__ == "__main__":
    unittest.main()
