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


ACA = (
    "Recent studies show that camera-based systems can support object "
    "monitoring [2]. Wang and Zhao [3] used an improved YOLOv8 model and "
    "showed that occlusion can still affect detection performance. To address "
    "this limitation, Xu et al. [5] proposed UWB-based tracking, but it "
    "remains limited in non-line-of-sight conditions in many different cases."
)


class AcademicStyleTests(unittest.TestCase):
    def _run(self, **kw):
        return Humanizer(
            tone="academic", strength=0.4, seed=7, **kw
        ).humanize(ACA)

    def test_no_citation_numbers_are_invented_or_lost(self):
        r = self._run()
        self.assertEqual(
            sorted(__import__("re").findall(r"\d+", r.text)),
            sorted(["2", "3", "5", "8"]),  # 8 from "YOLOv8"
        )
        for n in ("[2]", "[3]", "[5]"):
            self.assertIn(n, r.text)

    def test_citations_moved_to_sentence_end(self):
        r = self._run()
        # No citation token immediately followed by a lowercase word.
        self.assertIsNone(
            __import__("re").search(r"\[\d+\]\s+[a-z]", r.text)
        )

    def test_acronym_expanded_once_and_not_decapitalized(self):
        r = self._run()
        self.assertIn("ultra-wideband (UWB)", r.text)
        self.assertNotIn("yOLO", r.text)
        self.assertNotIn("uWB", r.text)

    def test_compound_unstacked(self):
        r = self._run()
        self.assertNotIn("camera-based systems", r.text)

    def test_inflated_modifier_deflated(self):
        r = Humanizer(tone="academic", strength=0.3, seed=2).humanize(
            "This is increasingly important for large-scale data collection."
        )
        self.assertNotIn("increasingly important", r.text)
        self.assertNotIn("large-scale", r.text)

    def test_et_al_not_split_into_a_new_sentence(self):
        r = self._run()
        self.assertNotIn(". Proposed", r.text)

    def test_function_words_and_names_preserved(self):
        r = self._run()
        self.assertIn("Wang and Zhao", r.text)
        self.assertIn("Xu et al.", r.text)

    def test_deterministic_and_runs_for_all_tones_with_flag(self):
        a = Humanizer(tone="professional", seed=3, academic_style=True).humanize(ACA)
        b = Humanizer(tone="professional", seed=3, academic_style=True).humanize(ACA)
        self.assertEqual(a.text, b.text)
        for t in list_tones():
            with self.subTest(tone=t):
                r = Humanizer(tone=t, seed=1, academic_style=True).humanize(ACA)
                self.assertTrue(r.text.strip())

    def test_custom_acronyms_are_used(self):
        r = Humanizer(
            tone="academic", strength=0.2, seed=1,
            acronyms={"NLOS": "non-line-of-sight (NLOS)"},
        ).humanize("NLOS conditions degrade NLOS tracking accuracy here.")
        self.assertIn("non-line-of-sight (NLOS)", r.text)


class AcademicLexiconExpansionTests(unittest.TestCase):
    def test_domain_vocabulary_present(self):
        from humanizer.academic_lexicon import academic_options

        for w in ("dataset", "leverage", "model", "scalable", "occlusion",
                  "latency", "deploy", "benchmark", "embedded"):
            with self.subTest(word=w):
                self.assertTrue(academic_options(w), w)

    def test_merged_lexicon_prefers_project_options(self):
        from humanizer.academic_lexicon import merged_lexicon

        m = merged_lexicon({"System": ["framework"]})
        self.assertEqual(m["system"][0], "framework")
        # Base options are kept (de-duplicated) after the project ones.
        self.assertIn("architecture", m["system"])
        # New project-only head-words are added.
        m2 = merged_lexicon({"widget": ["component"]})
        self.assertEqual(m2["widget"], ["component"])


class GlossaryTests(unittest.TestCase):
    def test_normalize_is_tolerant(self):
        from humanizer.glossary import normalize_glossary

        g = normalize_glossary(
            {"synonyms": {"System": "framework", "bad": 5},
             "acronyms": {"UWB": "ultra-wideband (UWB)"},
             "protect": ["YOLOv8", "ArUco"],
             "junk": True}
        )
        self.assertEqual(g["synonyms"]["system"], ["framework"])
        self.assertNotIn("bad", g["synonyms"])
        self.assertEqual(g["acronyms"]["UWB"], "ultra-wideband (UWB)")
        self.assertIn("yolov8", g["protect"])
        for bad in (None, [], "x", 42):
            n = normalize_glossary(bad)
            self.assertEqual(n["synonyms"], {})
            self.assertEqual(n["acronyms"], {})

    def test_load_glossary_roundtrip_and_errors(self):
        import json
        import os
        import tempfile

        from humanizer.glossary import load_glossary

        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, "g.json")
            with open(good, "w", encoding="utf-8") as fh:
                json.dump({"protect": ["ArUco"]}, fh)
            self.assertIn("aruco", load_glossary(good)["protect"])

            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            with self.assertRaises(ValueError):
                load_glossary(bad)
            with self.assertRaises(ValueError):
                load_glossary(os.path.join(d, "missing.json"))

    def test_protected_terms_are_never_substituted(self):
        gloss = {"protect": ["framework", "ArUco"]}
        text = (
            "The framework is robust and the framework is scalable. "
            "ArUco markers support the framework in many different cases."
        )
        for seed in (1, 2, 3, 4, 5):
            r = Humanizer(
                tone="academic", strength=0.9, seed=seed, glossary=gloss
            ).humanize(text)
            self.assertIn("framework", r.text)
            self.assertIn("ArUco", r.text)

    def test_glossary_acronym_expanded_and_explicit_wins(self):
        r = Humanizer(
            tone="academic", strength=0.3, seed=1,
            glossary={"acronyms": {"NLOS": "non-line-of-sight (NLOS)"}},
        ).humanize("NLOS conditions reduce NLOS tracking accuracy here.")
        self.assertIn("non-line-of-sight (NLOS)", r.text)

        h = Humanizer(
            tone="academic",
            glossary={"acronyms": {"AI": "from glossary"}},
            acronyms={"AI": "from explicit arg"},
        )
        self.assertEqual(h.acronyms["AI"], "from explicit arg")

    def test_glossary_synonym_preference_can_apply(self):
        gloss = {"synonyms": {"system": ["framework"]}}
        seen = set()
        for seed in range(8):
            r = Humanizer(
                tone="academic", strength=0.9, seed=seed, glossary=gloss
            ).humanize("The system processes data. The system is reliable.")
            seen.update(r.text.split())
        self.assertIn("framework", seen)

    def test_non_academic_tone_ignores_glossary_synonyms(self):
        # Glossary synonyms only steer the academic lexicon path.
        r = Humanizer(
            tone="casual", strength=0.5, seed=1,
            glossary={"protect": ["system"]},
        ).humanize("The system is good.")
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
