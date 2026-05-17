"""On-demand synonym suggestions for a single word or compound.

Backs the web UI's double-click feature: given a selected word (or a
hyphenated / multi-word compound) and a tone, return tone-appropriate
replacement options drawn from that tone's curated dictionary, so every
suggestion is one the humanizer itself would consider grammatically sound.
"""

from __future__ import annotations

import re
from typing import List

from .paraphrase_patterns import NOMINALIZATIONS
from .tones import get_tone

_CLEAN_RE = re.compile(r"^[\W_]+|[\W_]+$")


def _norm(token: str) -> str:
    return _CLEAN_RE.sub("", token or "").lower().strip()


def suggest_synonyms(word: str, tone: str = "casual", limit: int = 12) -> List[str]:
    """Return up to ``limit`` tone-appropriate synonyms for ``word``.

    Looks the selection up as a whole phrase first (handles hyphenated and
    multi-word compounds), then falls back to the last word.  The original
    surface form is never returned, results are de-duplicated and order is
    stable (curated/tone-preferred options first).  Unknown words return an
    empty list rather than raising.
    """
    try:
        t = get_tone(tone)
    except KeyError:
        return []

    syn = t.synonyms
    raw = (word or "").strip()
    if not raw:
        return []

    candidates: List[str] = []

    whole = _norm(raw)
    spaced = re.sub(r"[-_/]+", " ", whole).strip()
    for key in (whole, spaced):
        if key and key in syn:
            candidates = list(syn[key])
            break

    # Light-verb / nominalisation phrases ("make use of" -> "use").
    if not candidates:
        for phrase, verb in NOMINALIZATIONS.items():
            if phrase == spaced or phrase == whole:
                candidates = [verb]
                break

    if not candidates:
        parts = re.split(r"[\s\-_/]+", whole)
        if len(parts) > 1:
            last = parts[-1]
            if last in syn:
                # Re-attach the compound's prefix so the suggestion still
                # fits where the user clicked (e.g. "well-known" -> last
                # word "known" -> "well-recognized").
                prefix = raw[: raw.lower().rfind(last)]
                candidates = [f"{prefix}{alt}" for alt in syn[last]]

    seen = set()
    out: List[str] = []
    for c in candidates:
        cl = c.strip()
        key = cl.lower()
        # A comma-bearing option ("fine, somehow") reads wrong dropped inline,
        # so it is excluded from click-to-replace suggestions.
        if not cl or "," in cl or key == whole or key in seen:
            continue
        seen.add(key)
        out.append(cl)
        if len(out) >= max(1, limit):
            break
    return out
