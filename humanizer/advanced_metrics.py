"""Stronger text statistics for the AI-Humanizer.

This module builds on :mod:`humanizer.metrics` and :mod:`humanizer.lexicon`
with sharper, more length-robust signals:

* :func:`bigram_perplexity` -- a backoff bigram surprisal model that blends a
  within-text bigram count model with the embedded unigram lexicon.  Smooth,
  predictable (machine) text scores low; varied human text scores higher.
* :func:`mtld` -- Measure of Textual Lexical Diversity, the standard
  forward+reverse factor-count algorithm, robust to document length.
* :func:`sentence_burstiness_profile` -- sentence-length variation summary
  including coefficient of variation and distance to a human target.
* :func:`humanity_score` -- a deterministic 0..100 blend of the above.
* :func:`detailed_report` -- rounded numbers for CLI display.

Pure standard library only; no randomness; deterministic.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Dict, List

from .lexicon import word_probability, word_surprisal
from .metrics import split_sentences, tokenize_words

__all__ = [
    "bigram_perplexity",
    "mtld",
    "sentence_burstiness_profile",
    "humanity_score",
    "detailed_report",
]


def _as_words(words) -> List[str]:
    """Accept a raw string or an already-tokenized sequence of words.

    Passing a ``str`` is a common mistake (it would otherwise be iterated
    character-by-character), so coerce it to word tokens here.
    """
    if isinstance(words, str):
        return tokenize_words(words)
    return list(words)


def bigram_perplexity(words: List[str], k: float = 0.4, lam: float = 0.6) -> float:
    """Perplexity from a backoff bigram surprisal model.

    ``P(w2|w1)`` is estimated by linearly interpolating a within-text bigram
    count model (add-k smoothed over the observed vocabulary) with the unigram
    model from the lexicon, then backing off to :func:`word_probability` for
    pairs whose history ``w1`` was never seen.

    Returns ``2 ** (mean bigram surprisal in bits)``.  Higher means less
    predictable, i.e. more human-like.  Returns ``0.0`` for 0/1-word input.

    ``words`` may be a token list or a raw string (auto-tokenized).
    """
    words = _as_words(words)
    if len(words) < 2:
        return 0.0

    vocab = set(words)
    v = len(vocab)

    # Counts of w1 and of (w1, w2).
    unigram_counts: Counter = Counter(words)
    bigram_counts: Counter = Counter(zip(words[:-1], words[1:]))

    total_bits = 0.0
    n_pairs = len(words) - 1

    for w1, w2 in zip(words[:-1], words[1:]):
        # Unigram probability from the lexicon (always available, > 0).
        p_uni = word_probability(w2)

        c1 = unigram_counts.get(w1, 0)
        if c1 > 0:
            # Add-k smoothed within-text bigram estimate.
            c12 = bigram_counts.get((w1, w2), 0)
            p_bi = (c12 + k) / (c1 + k * v)
            # Interpolate the local bigram model with the global unigram model.
            p = lam * p_bi + (1.0 - lam) * p_uni
        else:
            # Unseen history: back off entirely to the unigram model.
            p = p_uni

        if p <= 0.0:
            p = word_probability(w2)
        total_bits += -math.log2(p)

    mean_surprisal = total_bits / n_pairs
    return 2.0 ** mean_surprisal


def mtld(words: List[str], threshold: float = 0.72) -> float:
    """Measure of Textual Lexical Diversity (length-robust).

    Standard McCarthy & Jarvis algorithm: walk the token stream tracking the
    running type-token ratio; every time the TTR drops to ``threshold`` a
    "factor" is completed and the counter resets.  A partial trailing factor is
    counted fractionally.  The MTLD is the token count divided by the average
    of the forward and reverse factor counts.

    Returns ``0.0`` for empty input and never divides by zero.

    ``words`` may be a token list or a raw string (auto-tokenized).
    """
    words = _as_words(words)
    if not words:
        return 0.0
    if len(words) == 1:
        return 1.0

    def _factor_count(seq: List[str]) -> float:
        factors = 0.0
        types: set = set()
        token_count = 0
        for w in seq:
            token_count += 1
            types.add(w)
            ttr = len(types) / token_count
            if ttr <= threshold:
                factors += 1.0
                types = set()
                token_count = 0
        # Account for any partial trailing factor.
        if token_count > 0:
            ttr = len(types) / token_count
            denom = 1.0 - threshold
            if denom > 0:
                partial = (1.0 - ttr) / denom
            else:
                partial = 0.0
            # Clamp the partial contribution to [0, 1].
            partial = max(0.0, min(1.0, partial))
            factors += partial
        return factors

    fwd = _factor_count(words)
    rev = _factor_count(list(reversed(words)))

    avg_factors = (fwd + rev) / 2.0
    if avg_factors <= 0.0:
        # No factor completed at all -> maximally diverse for this length.
        return float(len(words))
    return len(words) / avg_factors


def sentence_burstiness_profile(text: str) -> Dict:
    """Summarise sentence-length variation.

    Returns a dict with the per-sentence word ``lengths``, their ``mean`` and
    population ``stdev``, the coefficient of variation ``cv`` (stdev/mean), the
    ``burstiness`` value ``(sigma - mu) / (sigma + mu)``, a fixed
    ``human_target_cv`` of 0.55 and the ``gap_to_target`` (absolute distance of
    ``cv`` from that target).  Robust to texts with fewer than 2 sentences.
    """
    sentences = split_sentences(text)
    lengths = [len(tokenize_words(s)) for s in sentences]
    lengths = [n for n in lengths if n > 0]

    human_target_cv = 0.55

    if len(lengths) < 2:
        mean = float(lengths[0]) if lengths else 0.0
        return {
            "lengths": lengths,
            "mean": mean,
            "stdev": 0.0,
            "cv": 0.0,
            "burstiness": 0.0,
            "human_target_cv": human_target_cv,
            "gap_to_target": human_target_cv,
        }

    mean = statistics.fmean(lengths)
    stdev = statistics.pstdev(lengths)
    cv = (stdev / mean) if mean > 0 else 0.0
    burst = (stdev - mean) / (stdev + mean) if (stdev + mean) > 0 else 0.0

    return {
        "lengths": lengths,
        "mean": mean,
        "stdev": stdev,
        "cv": cv,
        "burstiness": burst,
        "human_target_cv": human_target_cv,
        "gap_to_target": abs(cv - human_target_cv),
    }


def _saturating(value: float, midpoint: float) -> float:
    """Smooth, monotone 0..1 curve: 0 at value 0, ~0.5 at ``midpoint``."""
    if value <= 0.0 or midpoint <= 0.0:
        return 0.0
    return value / (value + midpoint)


def humanity_score(text: str) -> float:
    """Deterministic 0..100 blend of perplexity, burstiness and lexical signals.

    Sub-scores (each normalised to 0..1):

    * **perplexity** -- :func:`bigram_perplexity` mapped through a smooth,
      saturating curve so machine-low perplexity yields a small score and
      human-typical perplexity yields a high, saturating score.
    * **burstiness** -- derived from the profile ``cv``: the closer ``cv`` is
      to ``human_target_cv`` the higher the score (linear falloff with gap).
    * **lexical** -- the average of an MTLD curve and the type-token ratio.

    Final weighting: perplexity 0.40, burstiness 0.35, lexical 0.25.  The
    result is clamped to ``[0, 100]``.  No randomness is used.
    """
    words = tokenize_words(text)

    # --- Perplexity sub-score (saturating around a human-typical midpoint). ---
    bp = bigram_perplexity(words)
    perp_sub = _saturating(bp, midpoint=60.0)

    # --- Burstiness sub-score (proximity of cv to the human target). ---
    profile = sentence_burstiness_profile(text)
    target = profile["human_target_cv"]
    gap = profile["gap_to_target"]
    if target > 0:
        burst_sub = max(0.0, 1.0 - (gap / target))
    else:
        burst_sub = 0.0

    # --- Lexical sub-score (MTLD curve blended with type-token ratio). ---
    md = mtld(words)
    mtld_sub = _saturating(md, midpoint=50.0)
    ttr = (len(set(words)) / len(words)) if words else 0.0
    lexical_sub = 0.6 * mtld_sub + 0.4 * ttr

    blended = 0.40 * perp_sub + 0.35 * burst_sub + 0.25 * lexical_sub
    score = blended * 100.0
    return max(0.0, min(100.0, score))


def detailed_report(text: str) -> Dict:
    """Rounded metric bundle for CLI display."""
    words = tokenize_words(text)
    profile = sentence_burstiness_profile(text)
    rounded_profile = {
        "lengths": profile["lengths"],
        "mean": round(profile["mean"], 2),
        "stdev": round(profile["stdev"], 2),
        "cv": round(profile["cv"], 3),
        "burstiness": round(profile["burstiness"], 3),
        "human_target_cv": profile["human_target_cv"],
        "gap_to_target": round(profile["gap_to_target"], 3),
    }
    return {
        "bigram_perplexity": round(bigram_perplexity(words), 3),
        "mtld": round(mtld(words), 3),
        "burstiness_profile": rounded_profile,
        "humanity_score": round(humanity_score(text), 2),
    }
