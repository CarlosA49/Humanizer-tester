"""Optional in-text citation markers.

Off by default.  When enabled it inserts *neutral* citation markers next to
claim-like sentences -- it never invents authors, titles, years or sources.

Modes (``ctx.citation_mode``):

* ``"off"``          -- no-op (default).
* ``"placeholder"``  -- appends ``[citation needed]``.
* ``"author-year"``  -- appends ``(Author, Year)`` as a fill-in placeholder.
* ``"numbered"``     -- appends ``[1]``, ``[2]`` ...  If the user supplied a
  reference list (``ctx.sources``) the markers are capped to the number of
  real sources provided and a matching reference list is produced; with no
  sources, numbered markers are still placeholders the user fills in later.

The rule only inserts markers and records the reference lines on
``ctx.references``; the public API stitches the reference block onto the
output.
"""

from __future__ import annotations

import re
from typing import List

from .pipeline import Context

# Cues that a sentence is making a factual / evidential claim worth a cite.
_CLAIM_CUES = re.compile(
    r"\b(stud(?:y|ies)|research|evidence|data|survey|report|"
    r"according to|shows?|demonstrat\w+|prove[ns]?|"
    r"found that|indicates?|suggests?|statistics?|percent|%|"
    r"experts?|analysis|findings?)\b",
    re.IGNORECASE,
)
_NUMBER_CLAIM = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|percent|million|billion|times)\b",
                           re.IGNORECASE)
_TERM_RE = re.compile(r"\s*([.!?])\s*$")

_VALID_MODES = {"off", "placeholder", "author-year", "numbered"}


def _is_claim(sentence: str) -> bool:
    s = sentence.strip()
    if len(s.split()) < 6:
        return False
    return bool(_CLAIM_CUES.search(s) or _NUMBER_CLAIM.search(s))


def _insert_marker(sentence: str, marker: str) -> str:
    m = _TERM_RE.search(sentence)
    if m:
        return f"{sentence[: m.start()]} {marker}{m.group(1)}"
    return f"{sentence.rstrip()} {marker}"


def add_citations(sentences: List[str], ctx: Context) -> List[str]:
    """Insert optional citation markers next to claim-like sentences."""
    mode = getattr(ctx, "citation_mode", "off")
    if mode not in _VALID_MODES or mode == "off":
        return sentences

    sources: List[str] = [s for s in getattr(ctx, "sources", []) if s.strip()]
    references: List[str] = getattr(ctx, "references", [])

    # In numbered mode with a user reference list, never mark more claims than
    # there are real sources -- every [n] must point at something the user
    # actually supplied.
    cap = len(sources) if (mode == "numbered" and sources) else None

    out: List[str] = []
    n = 0
    for sent in sentences:
        if not sent.strip() or not _is_claim(sent):
            out.append(sent)
            continue
        if cap is not None and n >= cap:
            out.append(sent)
            continue

        if mode == "placeholder":
            marker = "[citation needed]"
        elif mode == "author-year":
            marker = "(Author, Year)"
        else:  # numbered
            n += 1
            marker = f"[{n}]"
            if sources:
                references.append(f"[{n}] {sources[n - 1].strip()}")
            else:
                references.append(f"[{n}] (add source)")
        out.append(_insert_marker(sent, marker))
        ctx.log(f"citation: inserted {marker!r}")

    ctx.references = references
    return out
