import unittest

from humanizer import Humanizer, Pipeline, analyze, get_tone, list_tones
from humanizer.metrics import burstiness, split_sentences
from humanizer.pipeline import Context, lexical_substitution
from random import Random

AI_SAMPLE = (
    "It is important to note that artificial intelligence is a very good "
    "technology. It is important to note that it can help people in many "
    "ways. In conclusion, it is a very important tool that we should use. "
    "Additionally, it can make things easy and it can make things fast and "
    "it can make things good for many people in many different situations."
)


class ToneTests(unittest.TestCase):
    def test_all_tones_load_with_vocabulary(self):
        self.assertGreaterEqual(len(list_tones()), 9)
        for name in list_tones():
            tone = get_tone(name)
            self.assertGreater(tone.vocabulary_size, 150, name)
            self.assertTrue(tone.starters)
            self.assertTrue(tone.fragments)
            self.assertTrue(tone.connectors)

    def test_unknown_tone_raises(self):
        with self.assertRaises(KeyError):
            get_tone("nope")


class MetricsTests(unittest.TestCase):
    def test_burstiness_uniform_is_low(self):
        self.assertLess(burstiness([10, 10, 10, 10]), -0.5)

    def test_burstiness_varied_is_higher(self):
        uniform = burstiness([10, 10, 10, 10])
        varied = burstiness([2, 18, 4, 25, 7])
        self.assertGreater(varied, uniform)

    def test_analyze_empty(self):
        m = analyze("")
        self.assertEqual(m.word_count, 0)

    def test_split_sentences(self):
        self.assertEqual(len(split_sentences("One. Two! Three?")), 3)


class HumanizeTests(unittest.TestCase):
    def test_output_changes_and_is_nonempty(self):
        r = Humanizer(tone="casual", strength=0.8, seed=1).humanize(AI_SAMPLE)
        self.assertTrue(r.text.strip())
        self.assertNotEqual(r.text, r.original)
        self.assertTrue(r.changes)

    def test_ai_tells_removed(self):
        r = Humanizer(tone="professional", strength=0.9, seed=3).humanize(AI_SAMPLE)
        self.assertNotIn("it is important to note that", r.text.lower())
        self.assertNotIn("in conclusion", r.text.lower())

    def test_deterministic_with_seed(self):
        a = Humanizer(tone="witty", strength=0.7, seed=42).humanize(AI_SAMPLE)
        b = Humanizer(tone="witty", strength=0.7, seed=42).humanize(AI_SAMPLE)
        self.assertEqual(a.text, b.text)

    def test_seeds_differ(self):
        a = Humanizer(tone="friendly", strength=0.7, seed=1).humanize(AI_SAMPLE)
        b = Humanizer(tone="friendly", strength=0.7, seed=2).humanize(AI_SAMPLE)
        self.assertNotEqual(a.text, b.text)

    def test_metrics_move_toward_human(self):
        r = Humanizer(tone="casual", strength=0.9, seed=5).humanize(AI_SAMPLE)
        # Repetitive AI text -> humanized should be lexically richer & burstier.
        self.assertGreater(r.metrics_after.mattr, r.metrics_before.mattr)
        self.assertGreater(
            r.metrics_after.burstiness, r.metrics_before.burstiness - 0.05
        )

    def test_all_tones_run(self):
        for name in list_tones():
            r = Humanizer(tone=name, strength=0.6, seed=9).humanize(AI_SAMPLE)
            self.assertTrue(r.text.strip(), name)

    def test_empty_input(self):
        r = Humanizer().humanize("")
        self.assertEqual(r.text, "")

    def test_custom_pipeline_subset(self):
        pipe = Pipeline(rules=["strip_ai_tells"])
        r = Humanizer(tone="academic", seed=1, pipeline=pipe).humanize(AI_SAMPLE)
        self.assertNotIn("in conclusion", r.text.lower())

    def test_invalid_pipeline_rule(self):
        with self.assertRaises(ValueError):
            Pipeline(rules=["does_not_exist"])

    def test_contractions_expand_for_academic(self):
        ctx = Context(tone=get_tone("academic"), rng=Random(0), strength=1.0)
        from humanizer.pipeline import adjust_contractions
        out = adjust_contractions(["It's a test and don't worry."], ctx)
        self.assertIn("it is", out[0].lower())
        self.assertIn("do not", out[0].lower())

    def test_articles_are_repaired(self):
        from humanizer.core import _fix_articles
        self.assertEqual(_fix_articles("a especially good idea"), "an especially good idea")
        self.assertEqual(_fix_articles("an big problem"), "a big problem")
        self.assertEqual(_fix_articles("a honest answer"), "an honest answer")
        self.assertEqual(_fix_articles("an university"), "a university")

    def test_lexical_substitution_replaces_words(self):
        ctx = Context(tone=get_tone("professional"), rng=Random(1), strength=1.0)
        out = lexical_substitution(["This is a very good and important idea."], ctx)
        self.assertNotEqual(out[0], "This is a very good and important idea.")


if __name__ == "__main__":
    unittest.main()
