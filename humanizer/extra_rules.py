"""Additional pipeline rules.

These follow the same contract as :mod:`humanizer.pipeline`:
``rule(sentences: list[str], ctx) -> list[str]``.

Every rule is deterministic given ``ctx.rng``, never raises on empty / short /
single-word input, and preserves readable capitalization and terminal
punctuation by leaning on the shared helpers.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List

from .pipeline import Context, _capitalize_first, _ensure_terminal, _match_case

# --------------------------------------------------------------------------- #
# Small shared constants
# --------------------------------------------------------------------------- #
_SUBORDINATORS = ("because", "while", "although", "though", "since", "if", "when")

_HEDGES = ("arguably", "to some extent", "in many cases", "broadly speaking")
_INTENSIFIERS = ("undeniably", "without question", "by a wide margin", "clearly")
_NEUTRAL_HEDGES = ("in practice", "on the whole", "for the most part", "generally")

_HEDGING_TONES = {"academic", "empathetic"}
_ASSERTIVE_TONES = {"confident", "persuasive"}

_REDUNDANCY = (
    ("due to the fact that", "because"),
    ("at this point in time", "now"),
    ("in order to", "to"),
    ("the fact that", "that"),
    ("for the purpose of", "for"),
    ("in spite of the fact that", "although"),
)

_DOUBLE_INTENSIFIERS = ("very", "really", "quite", "so", "just", "actually")


def _split_words(sentence: str) -> List[str]:
    return sentence.split()


def _terminal_punct(sentence: str) -> str:
    s = sentence.rstrip()
    return s[-1] if s and s[-1] in ".!?" else ""


# --------------------------------------------------------------------------- #
# 1. reorder_clauses
# --------------------------------------------------------------------------- #
def reorder_clauses(sentences: List[str], ctx: Context) -> List[str]:
    """Flip a leading subordinate clause to the back (or a trailing one
    to the front)."""
    out: List[str] = []
    lead_re = re.compile(
        r"^\s*(" + "|".join(_SUBORDINATORS) + r")\b(.*?),\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    )
    for sent in sentences:
        new = sent
        if not new.strip():
            out.append(new)
            continue

        term = _terminal_punct(new) or "."
        core = new.strip()
        core_no_term = core[:-1] if core[-1:] in ".!?" else core

        m = lead_re.match(core_no_term)
        if m and ctx.chance(0.4):
            sub_word, sub_rest, main = m.group(1), m.group(2), m.group(3)
            sub_clause = f"{sub_word.lower()}{sub_rest}".strip()
            main = main.strip()
            if main:
                rebuilt = f"{main[0].lower()}{main[1:]} {sub_clause}"
                new = _ensure_terminal(_capitalize_first(rebuilt).rstrip(".!?") + term)
                ctx.log("structure: reordered clauses")
                out.append(new)
                continue

        # Trailing subordinate clause -> move to the front.
        low = core_no_term.lower()
        best = -1
        chosen = ""
        for sub in _SUBORDINATORS:
            marker = " " + sub + " "
            pos = low.find(marker, max(1, len(low) // 4))
            if pos != -1 and (best == -1 or pos < best):
                best = pos
                chosen = sub
        if best != -1 and ctx.chance(0.4):
            head = core_no_term[:best].strip().rstrip(",")
            tail = core_no_term[best + len(chosen) + 2 :].strip()
            if head and tail:
                rebuilt = f"{chosen} {tail}, {head[0].lower()}{head[1:]}"
                new = _ensure_terminal(_capitalize_first(rebuilt).rstrip(".!?") + term)
                ctx.log("structure: reordered clauses")
                out.append(new)
                continue

        out.append(new)
    return out


# --------------------------------------------------------------------------- #
# 2. vary_openers
# --------------------------------------------------------------------------- #
def vary_openers(sentences: List[str], ctx: Context) -> List[str]:
    """Break up runs of sentences that all start with the same word."""
    out: List[str] = []
    prev_opener = None
    streak = 0
    for sent in sentences:
        new = sent
        stripped = new.strip()
        if not stripped:
            out.append(new)
            continue

        words = _split_words(stripped)
        opener = re.sub(r"[^A-Za-z']", "", words[0]).lower() if words else ""

        if opener and opener == prev_opener:
            streak += 1
        else:
            streak = 0
        prev_opener = opener

        if streak >= 1 and len(words) >= 2 and ctx.chance(0.6):
            term = _terminal_punct(stripped) or "."
            body = stripped[:-1] if stripped[-1:] in ".!?" else stripped
            options = []
            if ctx.tone.connectors:
                options.append("connector")
            if ctx.tone.starters:
                options.append("starter")
            options.append("rephrase")
            pick = ctx.rng.choice(options)

            if pick == "connector":
                conn = ctx.rng.choice(ctx.tone.connectors)
                rebuilt = f"{conn} {body[0].lower()}{body[1:]}"
            elif pick == "starter":
                starter = ctx.rng.choice(ctx.tone.starters)
                rebuilt = f"{starter} {body[0].lower()}{body[1:]}"
            else:
                # Light rephrase: drop a leading "It"/"This"/"The" filler so
                # the remaining content carries the opener instead.
                rest = words[1:]
                if rest:
                    rebuilt = " ".join(rest)
                else:
                    rebuilt = body

            new = _ensure_terminal(_capitalize_first(rebuilt).rstrip(".!?") + term)
            ctx.log("voice: varied a repeated opener")
            # Recompute opener so we don't keep firing on the same word.
            nwords = _split_words(new.strip())
            prev_opener = (
                re.sub(r"[^A-Za-z']", "", nwords[0]).lower() if nwords else ""
            )
            streak = 0

        out.append(new)
    return out


# --------------------------------------------------------------------------- #
# 3. inject_hedges_intensifiers
# --------------------------------------------------------------------------- #
def inject_hedges_intensifiers(sentences: List[str], ctx: Context) -> List[str]:
    """Slip a tone-appropriate hedge or intensifier near a clause start."""
    tone = ctx.tone.name
    if tone in _HEDGING_TONES:
        pool, kind = _HEDGES, "hedge"
    elif tone in _ASSERTIVE_TONES:
        pool, kind = _INTENSIFIERS, "intensifier"
    else:
        pool, kind = _NEUTRAL_HEDGES, "qualifier"

    out: List[str] = []
    for sent in sentences:
        new = sent
        stripped = new.strip()
        words = _split_words(stripped)
        if len(words) < 4 or not ctx.chance(0.35):
            out.append(new)
            continue

        phrase = ctx.rng.choice(pool)
        low = stripped.lower()

        # Already present? skip.
        if phrase in low:
            out.append(new)
            continue

        term = _terminal_punct(stripped) or "."
        body = stripped[:-1] if stripped[-1:] in ".!?" else stripped

        # Prefer inserting just after a mid-sentence comma (clause boundary);
        # otherwise insert after the opening word.
        comma = body.find(", ")
        if comma != -1 and comma + 2 < len(body):
            head = body[: comma + 2]
            tail = body[comma + 2 :].strip()
            if tail:
                rebuilt = f"{head}{phrase}, {tail[0].lower()}{tail[1:]}"
            else:
                rebuilt = body
        else:
            # Front the phrase as a sentence adverbial rather than wedging it
            # between a determiner and its noun ("The, hedge, model" reads
            # badly).  This keeps the clause grammatical.
            rebuilt = f"{phrase}, {body[0].lower()}{body[1:]}"

        new = _ensure_terminal(_capitalize_first(rebuilt).rstrip(".!?") + term)
        ctx.log(f"voice: inserted a {kind}")
        out.append(new)
    return out


# --------------------------------------------------------------------------- #
# 4. prune_redundancy
# --------------------------------------------------------------------------- #
def prune_redundancy(sentences: List[str], ctx: Context) -> List[str]:
    """Collapse wordy padding and drop adjacent duplicate words."""
    out: List[str] = []
    for sent in sentences:
        new = sent
        if not new.strip():
            out.append(new)
            continue
        changed = False

        for phrase, repl in _REDUNDANCY:
            pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)

            def _sub(m, repl=repl):
                return _match_case(m.group(0), repl)

            new2 = pat.sub(_sub, new)
            if new2 != new:
                changed = True
                new = new2

        # Doubled intensifiers: "very very" -> "very".
        for word in _DOUBLE_INTENSIFIERS:
            pat = re.compile(
                r"\b(" + re.escape(word) + r")(\s+\1\b)+", re.IGNORECASE
            )
            new2 = pat.sub(lambda m: m.group(1), new)
            if new2 != new:
                changed = True
                new = new2

        # Any adjacent duplicate word (case-insensitive), keep first form.
        dup = re.compile(r"\b([A-Za-z']+)(\s+)\1\b", re.IGNORECASE)
        while True:
            new2 = dup.sub(lambda m: m.group(1), new, count=1)
            if new2 == new:
                break
            changed = True
            new = new2

        new = re.sub(r"\s{2,}", " ", new)
        new = re.sub(r"\s+([,.;:!?])", r"\1", new).strip()

        if changed:
            new = _capitalize_first(new) if new else new
            ctx.log("concision: pruned redundancy")
        out.append(new if new else sent)
    return out


# --------------------------------------------------------------------------- #
# 5. soften_passive
# --------------------------------------------------------------------------- #
_PASSIVE_RE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(?:being\s+)?"
    r"([a-z]+(?:ed|en|wn|de|me))\b",
    re.IGNORECASE,
)

_PASSIVE_LIGHTEN = {
    "can be seen": "shows",
    "can be observed": "shows",
    "is being used": "works",
    "are being used": "work",
    "was done": "happened",
    "were done": "happened",
    "is needed": "matters",
    "are needed": "matter",
}


def soften_passive(sentences: List[str], ctx: Context) -> List[str]:
    """Nudge simple agentless passives toward lighter phrasing, only where
    it is clearly safe; otherwise leave the sentence unchanged."""
    tone = ctx.tone.name
    # Assertive tones push hardest on passive voice; hedging tones the least.
    if tone in _ASSERTIVE_TONES:
        base = 0.55
    elif tone in _HEDGING_TONES:
        base = 0.25
    else:
        base = 0.4

    out: List[str] = []
    for sent in sentences:
        new = sent
        stripped = new.strip()
        if len(_split_words(stripped)) < 3:
            out.append(new)
            continue

        low = stripped.lower()

        # Bail out if there is an explicit agent ("by ..."): rewriting that
        # safely is out of scope, so leave it unchanged.
        has_agent = re.search(r"\bby\s+[A-Za-z]", stripped) is not None

        replaced = False
        if not has_agent and ctx.chance(base):
            for src, dst in _PASSIVE_LIGHTEN.items():
                pat = re.compile(re.escape(src), re.IGNORECASE)
                m = pat.search(new)
                if m:
                    new = (
                        new[: m.start()]
                        + _match_case(m.group(0), dst)
                        + new[m.end() :]
                    )
                    replaced = True
                    break

            if not replaced and _PASSIVE_RE.search(new):
                # Generic light touch: turn "X is/are <verb>ed" with no agent
                # into a softer "X tends to <verb>" only when the participle
                # ends in "ed" (regular verb) -- safe & readable.
                def _soft(m):
                    aux, part = m.group(1), m.group(2)
                    if part.lower().endswith("ed") and len(part) > 4:
                        stem = part[:-2]
                        if stem.endswith(("at", "iz", "is", "us")):
                            stem = part[:-1]  # keep an 'e'
                        return f"tends to {stem}"
                    return m.group(0)

                new2 = _PASSIVE_RE.sub(_soft, new, count=1)
                if new2 != new:
                    new = new2
                    replaced = True

        if replaced:
            new = re.sub(r"\s{2,}", " ", new).strip()
            new = _capitalize_first(_ensure_terminal(new))
            ctx.log("voice: reduced passive")
        out.append(new)
    return out


# --------------------------------------------------------------------------- #
EXTRA_RULES: Dict[str, Callable[[List[str], Context], List[str]]] = {
    "reorder_clauses": reorder_clauses,
    "vary_openers": vary_openers,
    "inject_hedges_intensifiers": inject_hedges_intensifiers,
    "prune_redundancy": prune_redundancy,
    "soften_passive": soften_passive,
}
