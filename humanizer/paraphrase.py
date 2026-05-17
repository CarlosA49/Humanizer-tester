"""Sentence & paragraph reconstruction engine.

A curated set of structural transforms (expletive trimming, light-verb
unpacking, cleft / importance / cause / recommendation reframing, topic
fronting, coordinate-list reflow) plus a paragraph reflow pass.  Surface
wording is pulled from the tone-flavoured banks in
:mod:`humanizer.paraphrase_patterns`, so the *effective* pattern space is in
the thousands per tone while every transform stays hand-written and safe.

Same contract as the rest of the pipeline: ``rule(sentences, ctx) ->
sentences``; deterministic via ``ctx.rng``; never raises on short / empty /
single-word input; capitalisation and terminal punctuation preserved.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional

from .paraphrase_patterns import NOMINALIZATIONS, TONE_FRAMES, TONE_PIVOTS
from .pipeline import Context, _capitalize_first, _ensure_terminal, _match_case

_IMPORTANT_ADJ = (
    "important", "key", "crucial", "vital", "essential", "critical",
    "significant", "pivotal", "paramount", "fundamental",
)

_TERM_RE = re.compile(r"([.!?])\s*$")


def _terminal(sent: str) -> str:
    m = _TERM_RE.search(sent.strip())
    return m.group(1) if m else "."


def _strip_term(sent: str) -> str:
    return _TERM_RE.sub("", sent.strip()).strip()


def _lc_first(s: str) -> str:
    s = s.strip()
    return (s[0].lower() + s[1:]) if s else s


def _fill(template: str, x: str, y: str = "") -> str:
    return template.replace("{x}", _lc_first(x)).replace("{y}", _lc_first(y))


def _frame(ctx: Context, relation: str) -> Optional[str]:
    bank = TONE_FRAMES.get(ctx.tone.name, {}).get(relation)
    return ctx.rng.choice(bank) if bank else None


# --------------------------------------------------------------------------- #
# Structural transforms.  Each takes (sentence, ctx) and returns a rewritten
# sentence, or None when it does not apply.
# --------------------------------------------------------------------------- #
_THERE_RE = re.compile(
    r"^\s*there\s+(?:is|are|was|were)\s+(.+?)\s+(?:that|which|who)\s+(.+?)\s*$",
    re.IGNORECASE,
)


def t_expletive_there(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    m = _THERE_RE.match(_strip_term(sent))
    if not m:
        return None
    np, vp = m.group(1).strip(), m.group(2).strip()
    if len(np.split()) < 1 or len(vp.split()) < 2:
        return None
    return _ensure_terminal(_capitalize_first(f"{np} {vp}").rstrip(".!?") + term)


_IT_SCAFFOLD_RE = re.compile(
    r"^\s*it\s+(?:is|was)\s+(?:also\s+)?"
    r"(?:important|worth|interesting|clear|notable|essential|crucial|"
    r"useful|evident|obvious)\s+(?:to\s+\w+\s+)?that\s+(.+?)\s*$",
    re.IGNORECASE,
)


def t_expletive_it(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    m = _IT_SCAFFOLD_RE.match(_strip_term(sent))
    if not m:
        return None
    body = m.group(1).strip()
    if len(body.split()) < 3:
        return None
    return _ensure_terminal(_capitalize_first(body).rstrip(".!?") + term)


def t_nominalization(sent: str, ctx: Context) -> Optional[str]:
    new = sent
    hit = False
    for phrase, repl in NOMINALIZATIONS.items():
        pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        new2 = pat.sub(lambda m: _match_case(m.group(0), repl), new)
        if new2 != new:
            hit = True
            new = new2
    return new if hit else None


_IMPORTANCE_RE = re.compile(
    r"^\s*(.+?)\s+(?:is|are)\s+(?:a |an |the )?(?:very |highly |really |"
    r"quite )?(?:" + "|".join(_IMPORTANT_ADJ) + r")\b"
    r"(?:\s+because\s+(.+?))?\s*$",
    re.IGNORECASE,
)


def t_importance_reframe(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    m = _IMPORTANCE_RE.match(_strip_term(sent))
    if not m:
        return None
    x = m.group(1).strip()
    y = (m.group(2) or "").strip()
    if len(x.split()) < 2:
        return None
    tmpl = _frame(ctx, "cause" if y else "importance")
    if not tmpl:
        return None
    out = _fill(tmpl, x, y)
    return _ensure_terminal(_capitalize_first(out).rstrip(".!?") + term)


_CAUSE_RE = re.compile(r"^\s*(.+?),?\s+because\s+(.+?)\s*$", re.IGNORECASE)


def t_cause_reframe(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    m = _CAUSE_RE.match(_strip_term(sent))
    if not m:
        return None
    x, y = m.group(1).strip(), m.group(2).strip()
    if len(x.split()) < 2 or len(y.split()) < 2:
        return None
    tmpl = _frame(ctx, "cause")
    if not tmpl:
        return None
    return _ensure_terminal(_capitalize_first(_fill(tmpl, x, y)).rstrip(".!?") + term)


_RECO_RE = re.compile(
    r"^\s*(?:we|you|one|teams?|users?)\s+"
    r"(?:should|must|need to|ought to|have to)\s+(.+?)\s*$",
    re.IGNORECASE,
)


def t_recommendation_reframe(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    m = _RECO_RE.match(_strip_term(sent))
    if not m:
        return None
    x = m.group(1).strip()
    if len(x.split()) < 2:
        return None
    tmpl = _frame(ctx, "recommendation")
    if not tmpl:
        return None
    return _ensure_terminal(_capitalize_first(_fill(tmpl, x)).rstrip(".!?") + term)


_TOPIC_RE = re.compile(
    r"^\s*(.+?),\s+((?:in|for|with|by|after|before|despite|without|through|"
    r"across|during|under|amid|given)\s+[^,]+?)\s*$",
    re.IGNORECASE,
)


def t_topic_front(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    m = _TOPIC_RE.match(_strip_term(sent))
    if not m:
        return None
    head, phrase = m.group(1).strip(), m.group(2).strip()
    if len(head.split()) < 3 or len(phrase.split()) < 2:
        return None
    rebuilt = f"{_capitalize_first(phrase)}, {_lc_first(head)}"
    return _ensure_terminal(rebuilt.rstrip(".!?") + term)


_TRIPLE_AND_RE = re.compile(r"^(.*?\S)\s+and\s+(\S.*?\S)\s+and\s+(\S.*)$")


def t_list_reflow(sent: str, ctx: Context) -> Optional[str]:
    term = _terminal(sent)
    body = _strip_term(sent)
    if "," in body or body.lower().count(" and ") != 2:
        return None
    m = _TRIPLE_AND_RE.match(body)
    if not m:
        return None
    a, b, c = (g.strip() for g in m.groups())
    if min(len(a.split()), len(b.split()), len(c.split())) < 1:
        return None
    return _ensure_terminal(f"{a}, {b}, and {c}".rstrip(".!?") + term)


TRANSFORMS: List[Callable[[str, Context], Optional[str]]] = [
    t_expletive_there,
    t_expletive_it,
    t_nominalization,
    t_importance_reframe,
    t_cause_reframe,
    t_recommendation_reframe,
    t_topic_front,
    t_list_reflow,
]

# Per-transform firing weight: concision/light-verb transforms are always
# safe and fire readily; reframes are stronger and gated harder so the text
# is restructured, not mangled.
_BASE_CHANCE: Dict[str, float] = {
    "t_expletive_there": 0.7,
    "t_expletive_it": 0.7,
    "t_nominalization": 0.85,
    "t_importance_reframe": 0.5,
    "t_cause_reframe": 0.45,
    "t_recommendation_reframe": 0.5,
    "t_topic_front": 0.45,
    "t_list_reflow": 0.6,
}


def restructure_sentences(sentences: List[str], ctx: Context) -> List[str]:
    """Apply tone-aware structural reconstruction to each sentence.

    No-ops unless ``ctx.restructure`` is set.  At most two transforms touch a
    given sentence (light-verb unpacking may stack with one reframe) so output
    stays readable.
    """
    if not getattr(ctx, "restructure", True):
        return sentences

    out: List[str] = []
    for sent in sentences:
        if not sent.strip():
            out.append(sent)
            continue
        new = sent
        applied = 0
        for fn in TRANSFORMS:
            if applied >= 2:
                break
            base = _BASE_CHANCE.get(fn.__name__, 0.5)
            if not ctx.chance(base):
                continue
            try:
                cand = fn(new, ctx)
            except Exception:  # noqa: BLE001 - a transform must never break the run
                cand = None
            if cand and cand.strip() and cand != new:
                new = cand
                applied += 1
                ctx.log(f"restructure: {fn.__name__[2:]}")
        out.append(new)
    return out


# --------------------------------------------------------------------------- #
# Paragraph reflow (called from core, operates on a list of paragraphs).
# --------------------------------------------------------------------------- #
def reflow_paragraphs(paragraphs: List[str], ctx: Context) -> List[str]:
    """Vary paragraph rhythm: open some paragraphs with a tone pivot and fold
    a very short orphan paragraph into the next one.

    Deterministic; safe for 0/1 paragraph input; never empties the document.
    """
    if not getattr(ctx, "restructure", True) or len(paragraphs) < 2:
        return paragraphs

    pivots = TONE_PIVOTS.get(ctx.tone.name, [])
    merged: List[str] = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i].strip()
        if not para:
            i += 1
            continue
        # Fold a short orphan (< 14 words) into the following paragraph.
        if (
            len(para.split()) < 14
            and i + 1 < len(paragraphs)
            and paragraphs[i + 1].strip()
            and ctx.chance(0.4)
        ):
            nxt = paragraphs[i + 1].strip()
            merged.append(f"{_ensure_terminal(para)} {nxt}")
            ctx.log("restructure: folded a short paragraph")
            i += 2
            continue
        merged.append(para)
        i += 1

    if pivots:
        for idx in range(1, len(merged)):
            p = merged[idx]
            already = any(p.startswith(pv) for pv in pivots)
            if not already and ctx.chance(0.3):
                pv = ctx.rng.choice(pivots)
                merged[idx] = f"{pv} {_lc_first(p)}"
                ctx.log("restructure: opened a paragraph with a pivot")
    return merged or paragraphs
