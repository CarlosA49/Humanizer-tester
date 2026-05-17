"""The public ``Humanizer`` API: tone + pipeline + before/after metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from random import Random
from typing import List, Optional

from .advanced_metrics import humanity_score
from .metrics import TextMetrics, analyze, split_sentences
from .pipeline import Context, Pipeline, pipeline_for_tone
from .tones import Tone, get_tone, list_tones

__all__ = ["Humanizer", "HumanizeResult", "list_tones"]

# Words spelled with a vowel but pronounced with a consonant (and vice versa).
_AN_EXCEPTIONS = ("hour", "honest", "honour", "honor", "heir")
_A_EXCEPTIONS = ("uni", "use", "user", "one", "once", "euro", "ufo")
_ARTICLE_RE = re.compile(r"\b([Aa])(n?)\s+([A-Za-z]+)")
# Tidy punctuation artifacts the higher substitution rate can leave behind:
# space-before-punctuation and runs of repeated commas/terminators.
_SPACE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_DUP_COMMA_RE = re.compile(r",(?:\s*,)+")
_COMMA_TERM_RE = re.compile(r",\s*([.!?])")
# Em-dash overuse is a top AI tell, and some tone starters/asides carry one
# ("Bottom line —", "Spoiler alert —").  This is the final, system-wide
# guarantee that no em-dash, double-hyphen or space-padded hyphen-as-dash
# survives in any output; a bare hyphen ("10-20") is left untouched.
_AI_DASH_RE = re.compile(r"\s*(?:—|--)\s*|\s+-\s+")


def _tidy_punctuation(text: str) -> str:
    text = _AI_DASH_RE.sub(", ", text)
    text = _SPACE_PUNCT_RE.sub(r"\1", text)
    text = _DUP_COMMA_RE.sub(",", text)
    text = _COMMA_TERM_RE.sub(r"\1", text)
    text = re.sub(r"^\s*,\s*", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()
# A run of two or more articles (e.g. "the the", "the a") collapses to the
# last one — the article the substituted phrase brought with it.
_DUP_ARTICLE_RE = re.compile(
    r"\b((?:an?|the)\s+){2,}(?=[A-Za-z])", re.IGNORECASE
)


def _fix_articles(text: str) -> str:
    """Repair article glitches introduced by lexical substitution.

    Lexical replacements can be article-led phrases (e.g. ``plan`` ->
    ``"the strategy"``). When the original word already had an article this
    yields a doubled article (``the the strategy``); collapse those, keeping
    the last article and its capitalization, then fix ``a``/``an`` agreement.
    """

    def _collapse(m: re.Match) -> str:
        run = m.group(0)
        last = m.group(1)
        # Preserve a leading capital (e.g. sentence start "The the ...").
        if run[:1].isupper():
            last = last[:1].upper() + last[1:]
        return last

    text = _DUP_ARTICLE_RE.sub(_collapse, text)

    def repl(m: re.Match) -> str:
        art, n, word = m.group(1), m.group(2), m.group(3)
        low = word.lower()
        vowel = low[0] in "aeiou"
        if low.startswith(_AN_EXCEPTIONS):
            vowel = True
        elif low.startswith(_A_EXCEPTIONS):
            vowel = False
        correct = art + ("n" if vowel else "")
        return f"{correct} {word}"

    return _ARTICLE_RE.sub(repl, text)


@dataclass
class HumanizeResult:
    original: str
    text: str
    tone: str
    metrics_before: TextMetrics
    metrics_after: TextMetrics
    changes: List[str]
    humanity_before: float = 0.0
    humanity_after: float = 0.0

    @property
    def humanity_delta(self) -> float:
        return self.humanity_after - self.humanity_before

    @property
    def perplexity_delta(self) -> float:
        return self.metrics_after.perplexity - self.metrics_before.perplexity

    @property
    def burstiness_delta(self) -> float:
        return self.metrics_after.burstiness - self.metrics_before.burstiness

    @property
    def lexical_delta(self) -> float:
        return self.metrics_after.mattr - self.metrics_before.mattr

    def summary(self) -> str:
        b, a = self.metrics_before, self.metrics_after
        return (
            f"tone={self.tone}  changes={len(self.changes)}\n"
            f"  perplexity {b.perplexity:7.2f} -> {a.perplexity:7.2f} "
            f"({self.perplexity_delta:+.2f})\n"
            f"  burstiness {b.burstiness:7.3f} -> {a.burstiness:7.3f} "
            f"({self.burstiness_delta:+.3f})\n"
            f"  lexical    {b.mattr:7.3f} -> {a.mattr:7.3f} "
            f"({self.lexical_delta:+.3f})\n"
            f"  humanity   {self.humanity_before:7.1f} -> {self.humanity_after:7.1f} "
            f"({self.humanity_delta:+.1f}) / 100"
        )


class Humanizer:
    """Rewrite machine-sounding text toward a chosen human tone.

    Example::

        h = Humanizer(tone="casual", strength=0.6, seed=7)
        result = h.humanize("It is important to note that ...")
        print(result.text)
        print(result.summary())
    """

    def __init__(
        self,
        tone: str = "casual",
        strength: float = 0.5,
        seed: Optional[int] = None,
        pipeline: Optional[Pipeline] = None,
    ) -> None:
        self.tone: Tone = get_tone(tone)
        self.strength = max(0.0, min(1.0, float(strength)))
        self.seed = seed
        self.pipeline = pipeline or pipeline_for_tone(self.tone.name)

    def humanize(self, text: str) -> HumanizeResult:
        original = text or ""
        metrics_before = analyze(original)

        ctx = Context(
            tone=self.tone,
            rng=Random(self.seed),
            strength=self.strength,
        )
        sentences = split_sentences(original) or ([original] if original.strip() else [])
        rewritten = self.pipeline.run(sentences, ctx)
        result_text = " ".join(s.strip() for s in rewritten if s.strip())
        result_text = _tidy_punctuation(_fix_articles(result_text))

        return HumanizeResult(
            original=original,
            text=result_text,
            tone=self.tone.name,
            metrics_before=metrics_before,
            metrics_after=analyze(result_text),
            changes=ctx.changes,
            humanity_before=humanity_score(original),
            humanity_after=humanity_score(result_text),
        )
