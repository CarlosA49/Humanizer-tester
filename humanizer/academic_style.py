"""Technical / academic-paper style pass.

Encodes the recurring rewrite logic seen in human edits of AI-written
technical prose:

* :func:`expand_acronyms`   -- gloss an acronym on first use, then leave it.
* :func:`deflate_modifiers` -- drop inflated filler adjectives/adverbs.
* :func:`decompound_terms`  -- un-stack ``X-based Y`` into ``Y using X``.
* :func:`academic_connectors` -- lead sentences with discourse markers and
  split a long ``..., but ...`` into two sentences.
* :func:`normalize_citations` -- move ``[n]`` / ``[n, m]`` tokens to the end
  of their sentence and merge adjacent ones.  Numbers are NEVER invented or
  changed; this only repositions citations the author already wrote.

Every rule self-gates: it is a no-op unless the run is in academic style
(``ctx.academic_style`` is set, or the tone is ``academic``).  Same pipeline
contract as the rest: deterministic, safe on short/empty input.
"""

from __future__ import annotations

import re
from typing import Dict, List

from .pipeline import Context, _capitalize_first

# Default first-use glosses.  Users can extend / override via ctx.acronyms.
_DEFAULT_ACRONYMS: Dict[str, str] = {
    "UWB": "ultra-wideband (UWB)",
    "YOLO": "YOLO (You Only Look Once)",
    "6DoF": "six degrees of freedom (6DoF)",
    "6-DoF": "six degrees of freedom (6DoF)",
    "IoT": "Internet of Things (IoT)",
    "AI": "artificial intelligence (AI)",
    "ML": "machine learning (ML)",
    "CV": "computer vision (CV)",
    "RFID": "radio-frequency identification (RFID)",
    "GPS": "Global Positioning System (GPS)",
    "API": "application programming interface (API)",
    "CNN": "convolutional neural network (CNN)",
}

# Inflated filler -> plainer / shorter.  Curated phrases only (never blanket
# single-word deletion) so the result stays grammatical.
_DEFLATE = [
    (r"\bgrowing challenges\b", "challenges"),
    (r"\bgrowing concerns?\b", "concerns"),
    (r"\bgrowing number of\b", "many"),
    (r"\bincreasingly important\b", "important"),
    (r"\bincreasingly emphasizes?\b", "focuses on"),
    (r"\bbecome increasingly\b", "become more"),
    (r"\bremains? a significant concern\b", "is still a concern"),
    (r"\ba significant concern\b", "a concern"),
    (r"\bplays? a (?:crucial|vital|key|pivotal) role\b", "is central"),
    (r"\blarge-scale\s+", ""),
    (r"\bstate-of-the-art\s+", ""),
    (r"\bcutting-edge\s+", ""),
    (r"\bcontemporary\s+", ""),
    (r"\bnovel\s+(?=approach|method|system|technique)", ""),
    (r"\s+more effectively\b", ""),
    (r"\bin order to\b", "to"),
    (r"\bwith the aim of\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bit is worth noting that\b", ""),
    (r"\ba wide range of\b", "various"),
    (r"\bin today's world\b", "today"),
]
_DEFLATE_RE = [(re.compile(p, re.IGNORECASE), r) for p, r in _DEFLATE]

# Curated compound un-stacking ("X-based Y" -> "Y using X").  Curated so the
# output is always grammatical (no fragile auto-pluralisation).
_DECOMPOUND = {
    "camera-based object detection": "object detection using cameras",
    "camera-based detection": "detection using cameras",
    "camera-based systems": "systems that use cameras",
    "camera-based system": "a system that uses cameras",
    "vision-based detection": "detection using computer vision",
    "vision-based system": "a system that uses computer vision",
    "edge-based yolov8 implementation": "YOLOv8 running on edge devices",
    "edge-based implementation": "an implementation running on edge devices",
    "marker-based verification": "verification using markers",
    "marker-based methods": "methods that use markers",
    "marker-based pose estimation": "pose estimation using markers",
    "aruco marker-based methods": "methods that use ArUco markers",
    "radio-based tracking": "tracking using radio signals",
    "uwb-based tracking": "tracking using UWB",
    "uwb-assisted indoor localization": "indoor localization supported by UWB",
    "uwb-based indoor localization": "indoor localization using UWB",
    "vision-based tracking": "tracking using computer vision",
}
_DECOMPOUND_RE = [
    (re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE), v)
    for k, v in _DECOMPOUND.items()
]

# Leading weak opener -> academic connector.
_LEAD_SUBS = [
    (re.compile(r"^\s*And\s+", re.IGNORECASE), "In addition, "),
    (re.compile(r"^\s*But\s+", re.IGNORECASE), "However, "),
    (re.compile(r"^\s*So\s+", re.IGNORECASE), "Therefore, "),
    (re.compile(r"^\s*Also,?\s+", re.IGNORECASE), "Additionally, "),
    (re.compile(r"^\s*Plus,?\s+", re.IGNORECASE), "Furthermore, "),
]

_CITE_RE = re.compile(r"\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]")
_TERM_RE = re.compile(r"([.!?])([\"')\]]*)\s*$")


def _on(ctx: Context) -> bool:
    return bool(getattr(ctx, "academic_style", False)) or ctx.tone.name == "academic"


# --------------------------------------------------------------------------- #
def expand_acronyms(sentences: List[str], ctx: Context) -> List[str]:
    if not _on(ctx):
        return sentences
    table = dict(_DEFAULT_ACRONYMS)
    table.update(getattr(ctx, "acronyms", {}) or {})
    seen = ctx._acro_seen  # first-use is tracked per humanize() run
    out: List[str] = []
    for sent in sentences:
        new = sent
        for acro, full in table.items():
            if acro in seen:
                continue
            # Whole-token match, not already glossed (no '(' right after).
            pat = re.compile(r"(?<![\w(])" + re.escape(acro) + r"(?![\w(])")
            m = pat.search(new)
            if not m:
                continue
            # Don't expand if it already sits inside an existing parenthetical.
            tail = new[m.end(): m.end() + 1]
            if tail == ")":
                continue
            new = new[: m.start()] + full + new[m.end():]
            seen.add(acro)
            ctx.log(f"academic: expanded {acro!r} on first use")
        out.append(new)
    return out


def deflate_modifiers(sentences: List[str], ctx: Context) -> List[str]:
    if not _on(ctx):
        return sentences
    out: List[str] = []
    for sent in sentences:
        new = sent
        for pat, repl in _DEFLATE_RE:
            new2 = pat.sub(repl, new)
            if new2 != new:
                new = new2
        new = re.sub(r"\s{2,}", " ", new)
        new = re.sub(r"\s+([,.;:])", r"\1", new).strip()
        if new and new != sent.strip():
            new = _capitalize_first(new)
            ctx.log("academic: deflated inflated wording")
        out.append(new or sent)
    return out


def decompound_terms(sentences: List[str], ctx: Context) -> List[str]:
    if not _on(ctx):
        return sentences
    out: List[str] = []
    for sent in sentences:
        new = sent
        for pat, repl in _DECOMPOUND_RE:
            def _sub(m, repl=repl):
                g = m.group(0)
                return repl[0].upper() + repl[1:] if g[:1].isupper() else repl
            new2 = pat.sub(_sub, new)
            if new2 != new:
                new = new2
        if new != sent:
            ctx.log("academic: un-stacked an 'X-based Y' compound")
        out.append(new)
    return out


def academic_connectors(sentences: List[str], ctx: Context) -> List[str]:
    if not _on(ctx):
        return sentences
    out: List[str] = []
    for sent in sentences:
        new = sent.strip()
        for pat, repl in _LEAD_SUBS:
            if pat.match(new):
                new = pat.sub(repl, new, count=1)
                ctx.log("academic: led with a discourse connector")
                break

        # Split a long "..., but ..." into two sentences led by "However,".
        words = new.split()
        if len(words) >= 22 and ", but " in new and ctx.chance(0.8):
            head, _, tail = new.partition(", but ")
            head = head.strip().rstrip(",")
            tail = tail.strip()
            if len(head.split()) >= 6 and len(tail.split()) >= 5:
                if head and head[-1] not in ".!?":
                    head += "."
                new = f"{head} However, {tail}"
                ctx.log("academic: split a clause at 'but' -> 'However,'")
        out.append(new)
    return out


def _move_cites_to_end(sentence: str) -> str:
    cites = _CITE_RE.findall(sentence)
    if len(cites) == 0:
        return sentence
    stripped = _CITE_RE.sub("", sentence)
    stripped = re.sub(r"\s{2,}", " ", stripped)
    stripped = re.sub(r"\s+([,.;:!?])", r"\1", stripped).strip()

    # Merge the (already author-written) numbers into one sorted token.
    nums: List[int] = []
    for c in cites:
        for n in re.findall(r"\d+", c):
            v = int(n)
            if v not in nums:
                nums.append(v)
    token = "[" + ", ".join(str(n) for n in sorted(nums)) + "]"

    m = _TERM_RE.search(stripped)
    if m:
        return f"{stripped[: m.start()]} {token}{m.group(1)}{m.group(2)}"
    return f"{stripped.rstrip()} {token}"


def normalize_citations(sentences: List[str], ctx: Context) -> List[str]:
    """Reposition author-written citation tokens to the sentence end.

    Never alters, invents or removes citation numbers -- it only moves and
    de-duplicates the ``[n]`` tokens the author already wrote.
    """
    if not _on(ctx):
        return sentences
    out: List[str] = []
    for sent in sentences:
        if not sent.strip() or not _CITE_RE.search(sent):
            out.append(sent)
            continue
        new = _move_cites_to_end(sent)
        if new != sent:
            ctx.log("academic: moved citation(s) to sentence end")
        out.append(new)
    return out


RULES = {
    "expand_acronyms": expand_acronyms,
    "deflate_modifiers": deflate_modifiers,
    "decompound_terms": decompound_terms,
    "academic_connectors": academic_connectors,
    "normalize_citations": normalize_citations,
}
