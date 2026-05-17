"""Text statistics: perplexity proxy, burstiness, and lexical diversity.

These three signals are the heart of most "AI text detectors", so the
humanizer measures them before and after rewriting and tries to push them
toward human-typical ranges:

* perplexity  -- how (un)predictable the word choices are.  Machine text is
                 usually *low* perplexity (smooth, expected words).
* burstiness  -- how much sentence length varies.  Humans write in bursts:
                 a long sentence, then a short one.  Machine text is uniform.
* lexical     -- vocabulary richness / variety (type-token based measures).
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import List

from .lexicon import word_surprisal

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[A-Z0-9])")


def tokenize_words(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


_ABBREV = (
    "al.", "et al.", "e.g.", "i.e.", "etc.", "vs.", "cf.", "fig.", "eq.",
    "no.", "ref.", "dr.", "mr.", "mrs.", "ms.", "prof.", "sr.", "jr.",
    "approx.", "dept.", "ed.", "eds.", "vol.", "pp.", "p.",
)


def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENT_SPLIT_RE.split(text)
    # Re-join where the split fell after a known abbreviation ("et al.",
    # "e.g.") rather than a real sentence boundary.
    merged: List[str] = []
    for part in parts:
        if merged:
            tail = merged[-1].rstrip().lower()
            if any(tail.endswith(a) for a in _ABBREV):
                merged[-1] = merged[-1].rstrip() + " " + part.lstrip()
                continue
        merged.append(part)
    return [p.strip() for p in merged if p.strip()]


@dataclass
class TextMetrics:
    word_count: int
    sentence_count: int
    perplexity: float
    burstiness: float
    sentence_len_mean: float
    sentence_len_stdev: float
    type_token_ratio: float
    mattr: float  # moving-average type-token ratio (length-robust)

    def as_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "perplexity": round(self.perplexity, 3),
            "burstiness": round(self.burstiness, 3),
            "sentence_len_mean": round(self.sentence_len_mean, 2),
            "sentence_len_stdev": round(self.sentence_len_stdev, 2),
            "type_token_ratio": round(self.type_token_ratio, 3),
            "mattr": round(self.mattr, 3),
        }


def perplexity(words: List[str]) -> float:
    """2 ** (mean per-word surprisal).  Higher == less predictable."""
    if not words:
        return 0.0
    mean_surprisal = sum(word_surprisal(w) for w in words) / len(words)
    return 2.0 ** mean_surprisal


def burstiness(sentence_lengths: List[int]) -> float:
    """Coefficient-of-variation burstiness in roughly [-1, 1].

    B = (sigma - mu) / (sigma + mu).  Near -1 == very uniform (machine-like),
    higher == more variation in sentence length (human-like).
    """
    if len(sentence_lengths) < 2:
        return 0.0
    mu = statistics.fmean(sentence_lengths)
    sigma = statistics.pstdev(sentence_lengths)
    if mu + sigma == 0:
        return 0.0
    return (sigma - mu) / (sigma + mu)


def _mattr(words: List[str], window: int = 25) -> float:
    """Moving-average type-token ratio: stable across document lengths."""
    if not words:
        return 0.0
    if len(words) <= window:
        return len(set(words)) / len(words)
    ratios = []
    for i in range(len(words) - window + 1):
        chunk = words[i : i + window]
        ratios.append(len(set(chunk)) / window)
    return sum(ratios) / len(ratios)


def analyze(text: str) -> TextMetrics:
    words = tokenize_words(text)
    sentences = split_sentences(text)
    sent_lengths = [len(tokenize_words(s)) for s in sentences] or [len(words)]

    ttr = (len(set(words)) / len(words)) if words else 0.0
    return TextMetrics(
        word_count=len(words),
        sentence_count=len(sentences),
        perplexity=perplexity(words),
        burstiness=burstiness(sent_lengths),
        sentence_len_mean=statistics.fmean(sent_lengths) if sent_lengths else 0.0,
        sentence_len_stdev=statistics.pstdev(sent_lengths) if len(sent_lengths) > 1 else 0.0,
        type_token_ratio=ttr,
        mattr=_mattr(words),
    )
