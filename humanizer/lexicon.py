"""Frequency data and stopword lists used by the perplexity proxy.

No external models are required.  The perplexity estimate is built from an
embedded Zipf-style frequency table of the most common English words plus a
fallback rule for out-of-vocabulary (rare) words.  Rare words carry more
"surprisal", so text full of common, predictable words scores low perplexity
(machine-like) while varied/uncommon vocabulary scores higher (human-like).
"""

from __future__ import annotations

import math

# The ~190 most frequent English words, ordered by rank (rank 1 = most common).
# Rank is turned into a probability with a Zipf approximation, so the exact
# ordering only needs to be roughly right to give a stable, useful proxy.
_COMMON_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see", "other",
    "than", "then", "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first", "well", "way",
    "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "is", "are", "was", "were", "been", "has", "had", "did", "said", "made",
    "many", "much", "more", "very", "such", "through", "where", "while", "should", "before",
    "between", "those", "both", "under", "during", "against", "without", "within", "however", "therefore",
    "thus", "hence", "moreover", "furthermore", "although", "though", "since", "until", "upon", "across",
    "another", "every", "each", "few", "less", "least", "own", "same", "different", "important",
    "great", "small", "large", "long", "high", "old", "right", "big", "real", "best",
    "better", "sure", "able", "early", "young", "little", "still", "going", "thing", "things",
    "something", "someone", "anything", "everything", "nothing", "always", "never", "often", "sometimes", "really",
    "actually", "maybe", "perhaps", "quite", "rather", "almost", "enough", "around", "again", "away",
]

# Probability of a common word via a Zipf law: p(rank) ~ 1 / (rank * H_N).
_N = len(_COMMON_WORDS)
_H_N = sum(1.0 / (r + 1) for r in range(_N))  # harmonic-ish normaliser
_WORD_RANK = {w: i for i, w in enumerate(_COMMON_WORDS)}

# Probability mass we assume the common list covers.  The remaining mass is
# shared by the long tail of rarer words, giving each a small probability and
# therefore high surprisal.
_COMMON_MASS = 0.92
_RARE_VOCAB_ESTIMATE = 40000  # rough size of the "rest of English"

STOPWORDS = frozenset(_COMMON_WORDS[:120]) | {
    "am", "being", "doing", "having", "does", "shall", "may", "might", "must",
    "ought", "need", "dare", "yes", "okay", "ok",
}


def word_probability(word: str) -> float:
    """Return an estimated unigram probability for ``word`` (lower-cased)."""
    rank = _WORD_RANK.get(word)
    if rank is not None:
        zipf = (1.0 / (rank + 1)) / _H_N
        return _COMMON_MASS * zipf
    # Out-of-vocabulary: spread the leftover mass over the long tail.
    return (1.0 - _COMMON_MASS) / _RARE_VOCAB_ESTIMATE


def word_surprisal(word: str) -> float:
    """Surprisal in bits: ``-log2(p)``.  Rare words -> larger value."""
    return -math.log2(word_probability(word))
