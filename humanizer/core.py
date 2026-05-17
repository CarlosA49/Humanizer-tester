"""The public ``Humanizer`` API: tone + pipeline + before/after metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from random import Random
from typing import List, Optional

from .metrics import TextMetrics, analyze, split_sentences
from .pipeline import Context, Pipeline
from .tones import Tone, get_tone, list_tones

__all__ = ["Humanizer", "HumanizeResult", "list_tones"]

# Words spelled with a vowel but pronounced with a consonant (and vice versa).
_AN_EXCEPTIONS = ("hour", "honest", "honour", "honor", "heir")
_A_EXCEPTIONS = ("uni", "use", "user", "one", "once", "euro", "ufo")
_ARTICLE_RE = re.compile(r"\b([Aa])(n?)\s+([A-Za-z]+)")


def _fix_articles(text: str) -> str:
    """Repair a/an after lexical substitution changes the following word."""

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
            f"({self.lexical_delta:+.3f})"
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
        self.pipeline = pipeline or Pipeline()

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
        result_text = _fix_articles(result_text)

        return HumanizeResult(
            original=original,
            text=result_text,
            tone=self.tone.name,
            metrics_before=metrics_before,
            metrics_after=analyze(result_text),
            changes=ctx.changes,
        )
