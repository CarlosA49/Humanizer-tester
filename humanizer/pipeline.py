"""The humanizing pipeline: an ordered, configurable set of rewrite rules.

Each rule is a function ``rule(sentences, ctx) -> sentences``.  The
:class:`Pipeline` runs them in order.  Rules are deliberately small and
independent so a tone can choose its own rule order / subset.

The rules target the three detector signals:

* ``strip_ai_tells``           -- removes machine-typical boilerplate
* ``lexical_substitution``     -- raises lexical variety + perplexity
* ``adjust_contractions``      -- tone-correct register
* ``vary_sentence_length``     -- raises burstiness (split/merge/fragment)
* ``inject_discourse_markers`` -- human texture, raises perplexity
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from random import Random
from typing import Callable, Dict, List

from .lexicon import word_surprisal
from .tones import Tone

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*|[^A-Za-z\s]+|\s+")

_CONTRACTIONS = {
    "do not": "don't", "does not": "doesn't", "did not": "didn't",
    "is not": "isn't", "are not": "aren't", "was not": "wasn't",
    "were not": "weren't", "have not": "haven't", "has not": "hasn't",
    "had not": "hadn't", "will not": "won't", "would not": "wouldn't",
    "should not": "shouldn't", "could not": "couldn't", "can not": "can't",
    "cannot": "can't", "it is": "it's", "that is": "that's",
    "there is": "there's", "they are": "they're", "we are": "we're",
    "you are": "you're", "i am": "I'm", "i will": "I'll",
    "you will": "you'll", "they will": "they'll", "we will": "we'll",
    "let us": "let's", "going to": "gonna",
}
_EXPANSIONS = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "haven't": "have not", "hasn't": "has not",
    "hadn't": "had not", "won't": "will not", "wouldn't": "would not",
    "shouldn't": "should not", "couldn't": "could not", "can't": "cannot",
    "it's": "it is", "that's": "that is", "there's": "there is",
    "they're": "they are", "we're": "we are", "you're": "you are",
    "i'm": "I am", "i'll": "I will", "you'll": "you will",
    "let's": "let us", "gonna": "going to",
}

_SPLIT_MARKERS = (", and ", ", but ", ", so ", ", which ", "; ", ", yet ")
# Tried only when no comma-led break exists, so very long run-ons that lack
# punctuation ("X is good and X is fast and ...") still get carved up.
_FALLBACK_SPLIT_MARKERS = (
    " because ", " which means ", " given that ", " and ", " but ",
    " so that ", " while ", " yet ",
)


@dataclass
class Context:
    tone: Tone
    rng: Random
    strength: float = 0.5  # 0..1, scales how aggressively rules fire
    changes: List[str] = field(default_factory=list)
    restructure: bool = True  # apply tone-aware sentence/paragraph rebuilding
    citation_mode: str = "off"  # off | placeholder | author-year | numbered
    sources: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    academic_style: bool = False  # technical-paper transforms (always on for academic tone)
    acronyms: Dict[str, str] = field(default_factory=dict)  # extra first-use glosses
    _acro_seen: set = field(default_factory=set)

    def chance(self, base: float) -> bool:
        return self.rng.random() < min(1.0, base * (0.4 + 1.2 * self.strength))

    def log(self, msg: str) -> None:
        self.changes.append(msg)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _match_case(source: str, replacement: str) -> str:
    if source.isupper() and len(source) > 1:
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _ensure_terminal(sentence: str) -> str:
    s = sentence.strip()
    if s and s[-1] not in ".!?":
        s += "."
    return s


def _capitalize_first(sentence: str) -> str:
    s = sentence.lstrip()
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1 :]
    return s


def _surprisal_weighted_choice(rng: Random, pool: List[str]) -> str:
    """Pick from ``pool`` biased toward rarer (higher-surprisal) options.

    Predictable, common substitutes keep perplexity low (machine-like); a
    deterministic surprisal weighting pulls the choice toward the less common,
    more "human" options while keeping every option reachable.  Determinism is
    preserved because only ``rng`` is consulted.
    """
    if len(pool) <= 1:
        return pool[0] if pool else ""
    weights: List[float] = []
    for opt in pool:
        parts = opt.split()
        # Floor at 1.0 so even very common options stay reachable; raise to a
        # power to make the rare-word preference meaningful, not marginal.
        s = word_surprisal(parts[-1].lower()) if parts else 1.0
        weights.append(max(s, 1.0) ** 1.5)
    total = sum(weights)
    r = rng.random() * total
    upto = 0.0
    for opt, w in zip(pool, weights):
        upto += w
        if r <= upto:
            return opt
    return pool[-1]


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
def strip_ai_tells(sentences: List[str], ctx: Context) -> List[str]:
    out = []
    for sent in sentences:
        new = sent
        low = new.lower()
        for tell, repls in ctx.tone.ai_tells.items():
            idx = low.find(tell)
            while idx != -1:
                repl = ctx.rng.choice(repls)
                original = new[idx : idx + len(tell)]
                new = new[:idx] + _match_case(original, repl) + new[idx + len(tell) :]
                new = re.sub(r"\s{2,}", " ", new).replace(" ,", ",").strip()
                ctx.log(f"ai-tell: removed {tell!r}")
                low = new.lower()
                idx = low.find(tell)
        out.append(_capitalize_first(new) if new else new)
    return [s for s in out if s]


# Connectives / auxiliaries / pronouns academic prose keeps verbatim -- the
# human edits never thesaurus-swap these, and doing so reads badly.
_FUNCTION_WORDS = frozenset("""
a an the and or but nor so yet for of to in on at by with from into onto over
under as is are was were be been being am do does did has have had can could
will would shall should may might must this that these those it its they them
their we us our you your he she his her him not no than then thus hence also
because however therefore additionally furthermore moreover while since
although though if when which who whom whose what where whether both either
neither each every any some such only very more most less least about
""".split())

_PROTECT_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)")


def _protected_spans(text: str):
    return [(m.start(), m.end()) for m in _PROTECT_RE.finditer(text)]


def _in_spans(a: int, b: int, spans) -> bool:
    return any(a < e and b > s for s, e in spans)


def _is_proper_or_acronym(tok: str, first_alpha: bool) -> bool:
    """Heuristic: protect names / acronyms / model identifiers.

    Skips ALL-CAPS tokens (UWB), tokens with an internal capital or digit
    (YOLOv8, ArUco, Hailo-8L), and mid-sentence Capitalized words (author
    names like Wang/Zhao/Xu).  A sentence-initial capitalized common word is
    still eligible.
    """
    if any(ch.isdigit() for ch in tok):
        return True
    if len(tok) > 1 and tok.isupper():
        return True
    if any(c.isupper() for c in tok[1:]):
        return True
    if tok[:1].isupper() and not first_alpha:
        return True
    return False


_LEAD_WORD_RE = re.compile(r"[A-Za-z][\w'’.-]*")


def _lower_body(s: str) -> str:
    """Lower the first letter for ``Connector, <body>`` joins, but keep a
    leading proper noun / acronym / author name capitalised."""
    st = s.lstrip()
    toks = _LEAD_WORD_RE.findall(st[:64])
    if not toks:
        return s
    w0 = toks[0]
    if _is_proper_or_acronym(w0, True):
        return s
    if w0[:1].isupper():
        nxt = toks[1] if len(toks) > 1 else ""
        after = st[len(w0):].lstrip()[:1]
        if nxt[:1].isupper() or nxt.lower() in ("et", "al") or after == "[":
            return s
    return st[:1].lower() + st[1:]


def lexical_substitution(sentences: List[str], ctx: Context) -> List[str]:
    used: Dict[str, set] = {}
    syn = ctx.tone.synonyms
    academic = getattr(ctx, "academic_style", False) or ctx.tone.name == "academic"
    # Academic edits keep most words and stay in a common register; the
    # thesaurus pressure is dialled back and rare-word bias is dropped.
    phrase_chance = 0.20 if academic else 0.62
    word_chance = 0.18 if academic else 0.68

    def _pick(pool):
        if academic:
            return ctx.rng.choice(pool)
        return _surprisal_weighted_choice(ctx.rng, pool)

    phrase_keys = sorted(
        (k for k in syn if " " in k), key=len, reverse=True
    )
    out = []
    for sent in sentences:
        text = sent
        for key in phrase_keys:
            pat = re.compile(r"\b" + re.escape(key) + r"\b", re.IGNORECASE)

            def _sub(m, key=key):
                if _in_spans(m.start(), m.end(), _protected_spans(m.string)):
                    return m.group(0)
                if not ctx.chance(phrase_chance):
                    return m.group(0)
                pool = [w for w in syn[key] if w not in used.get(key, set())] or syn[key]
                choice = _pick(pool)
                used.setdefault(key, set()).add(choice)
                ctx.log(f"lexical: {m.group(0)!r} -> {choice!r}")
                return _match_case(m.group(0), choice)

            text = pat.sub(_sub, text)

        # Single-word pass (span-aware so names / acronyms / citations and
        # parenthetical glosses are never thesaurus-swapped).
        spans = _protected_spans(text)
        pieces: List[str] = []
        seen_alpha = False
        last = 0
        for m in _TOKEN_RE.finditer(text):
            tok = m.group(0)
            pieces.append(tok)
            idx = len(pieces) - 1
            is_word = bool(tok) and tok[0].isalpha()
            first_alpha = is_word and not seen_alpha
            if is_word:
                seen_alpha = True
            low = tok.lower()
            if (
                is_word
                and low in syn
                and not _in_spans(m.start(), m.end(), spans)
                and not (academic and _is_proper_or_acronym(tok, first_alpha))
                and not (academic and low in _FUNCTION_WORDS)
                and ctx.chance(word_chance)
            ):
                pool = [w for w in syn[low] if w not in used.get(low, set())] or syn[low]
                choice = _pick(pool)
                used.setdefault(low, set()).add(choice)
                pieces[idx] = _match_case(tok, choice)
                ctx.log(f"lexical: {tok!r} -> {choice!r}")
            last = m.end()
        out.append("".join(pieces) + text[last:])
    return out


def adjust_contractions(sentences: List[str], ctx: Context) -> List[str]:
    mode = ctx.tone.contraction_mode
    if mode == "keep":
        return sentences
    table = _CONTRACTIONS if mode == "contract" else _EXPANSIONS
    out = []
    for sent in sentences:
        new = sent
        for src, dst in table.items():
            pat = re.compile(r"\b" + re.escape(src) + r"\b", re.IGNORECASE)
            new2 = pat.sub(lambda m: _match_case(m.group(0), dst), new)
            if new2 != new:
                ctx.log(f"register: {src!r} -> {dst!r}")
                new = new2
        out.append(new)
    return out


def _split_once(sent: str, ctx: Context, lo_frac: float = 3.0):
    """Split ``sent`` at the earliest connector past ``len/lo_frac``.

    Comma-led breaks are preferred; bare conjunctions are a fallback so long
    run-ons without punctuation still break (which keeps the maximum sentence
    length down and stops the length spread from overshooting the human
    target).  Returns ``(first, rest)`` or ``None`` when no usable break
    exists.
    """
    low = sent.lower()

    def _earliest(markers, start):
        best = -1
        chosen = ""
        for marker in markers:
            pos = low.find(marker, start)
            if pos != -1 and (best == -1 or pos < best):
                best = pos
                chosen = marker
        return best, chosen

    # Prefer a break past ~1/3 (keeps the first piece from being trivially
    # short).  If nothing is there, retry from a small floor so a genuine
    # run-on still breaks instead of surviving whole and skewing the spread.
    start = int(len(sent) / lo_frac)
    floor = max(8, len(sent) // 9)

    best, chosen = _earliest(_SPLIT_MARKERS, start)
    if best == -1:
        best, chosen = _earliest(_FALLBACK_SPLIT_MARKERS, start)
    if best == -1:
        best, chosen = _earliest(_SPLIT_MARKERS, floor)
    if best == -1:
        best, chosen = _earliest(_FALLBACK_SPLIT_MARKERS, floor)
    if best == -1:
        return None
    first = _ensure_terminal(sent[:best])
    rest = _capitalize_first(_ensure_terminal(sent[best + len(chosen) :].strip()))
    return first, rest


def vary_sentence_length(sentences: List[str], ctx: Context) -> List[str]:
    # Academic prose is measured: a higher split gate and no punchy fragments,
    # so citation-bearing clause lists are not shattered.
    academic = getattr(ctx, "academic_style", False) or ctx.tone.name == "academic"
    # In academic style, principled clause splitting is handled by
    # academic_connectors (", but " -> ". However,"); disable the heuristic
    # run-on splitter so it never breaks an "X, and showed Y" clause.
    split_gate = 10_000 if academic else 19
    out: List[str] = []
    i = 0
    while i < len(sentences):
        sent = sentences[i].strip()
        words = sent.split()

        # Split long, run-on sentences -> raises burstiness.  A lower gate and
        # repeated passes carve sharp long/short contrasts while keeping the
        # maximum length bounded, so the spread lands near the human target
        # instead of blowing past it.
        if len(words) >= split_gate:
            split = _split_once(sent, ctx)
            if split and ctx.chance(0.88):
                first, rest = split
                ctx.log("burstiness: split a long sentence")
                out.append(first)
                # One extra pass, and only on a still-very-long tail, so a
                # genuine long sentence survives in the mix (it is the high
                # end of the spread that lifts the length CV toward the human
                # target -- carving everything flat would lower it).
                if len(rest.split()) >= 24:
                    nxt = _split_once(rest, ctx)
                    if nxt and ctx.chance(0.6):
                        mid, rest = nxt
                        ctx.log("burstiness: split a long sentence")
                        out.append(mid)
                out.append(rest)
                i += 1
                continue

        # Merge a very short sentence with the next one.  Kept deliberately
        # infrequent so short lines mostly survive (they widen the spread).
        if (
            len(words) <= 5
            and i + 1 < len(sentences)
            and ctx.chance(0.32)
        ):
            conn = ctx.rng.choice(ctx.tone.connectors)
            nxt = sentences[i + 1].strip()
            merged = f"{sent.rstrip('.!?')}, {conn} {nxt[0].lower()}{nxt[1:]}"
            ctx.log("burstiness: merged two short sentences")
            out.append(_ensure_terminal(merged))
            i += 2
            continue

        out.append(_ensure_terminal(sent))

        # Drop a punchy stand-alone fragment after a longer sentence.  Kept
        # moderate so short lines contrast with long ones without flooding the
        # text and pushing the length CV past the human target.  Suppressed in
        # academic style (technical prose does not use punchy fragments).
        if not academic and len(words) >= 14 and ctx.chance(0.45):
            frag = ctx.rng.choice(ctx.tone.fragments)
            ctx.log("burstiness: added a short fragment")
            out.append(frag)
        i += 1
    return out


def inject_discourse_markers(sentences: List[str], ctx: Context) -> List[str]:
    out = []
    academic = getattr(ctx, "academic_style", False) or ctx.tone.name == "academic"
    # Academic prose already gets one leading connector per sentence from
    # academic_connectors; keep this pass sparse and never wedge mid-sentence
    # asides into technical text.
    if academic:
        budget = int(len(sentences) * 0.12)
    else:
        budget = max(1, int(len(sentences) * (0.35 + 0.5 * ctx.strength)))
    for idx, sent in enumerate(sentences):
        new = sent
        already = any(new.startswith(s) for s in ctx.tone.starters)
        if budget > 0 and idx != 0 and not already and ctx.chance(0.5):
            starter = ctx.rng.choice(ctx.tone.starters)
            body = _lower_body(new)
            new = f"{starter} {body}"
            ctx.log(f"voice: opened a sentence with {starter!r}")
            budget -= 1
        elif (
            not academic
            and budget > 0
            and ", " in new
            and ctx.chance(0.25)
        ):
            inter = ctx.rng.choice(ctx.tone.interjections)
            head, _, tail = new.partition(", ")
            new = f"{head}, {inter}, {tail}"
            ctx.log(f"voice: inserted aside {inter!r}")
            budget -= 1
        out.append(new)
    return out


RULES: Dict[str, Callable[[List[str], Context], List[str]]] = {
    "strip_ai_tells": strip_ai_tells,
    "lexical_substitution": lexical_substitution,
    "adjust_contractions": adjust_contractions,
    "vary_sentence_length": vary_sentence_length,
    "inject_discourse_markers": inject_discourse_markers,
}

# Registered after definition to avoid a circular import (these modules import
# Context and the helpers from this module).
from .extra_rules import EXTRA_RULES  # noqa: E402
from .paraphrase import restructure_sentences  # noqa: E402
from .citations import add_citations  # noqa: E402
from .academic_style import RULES as _ACADEMIC_RULES  # noqa: E402

RULES.update(EXTRA_RULES)
RULES["restructure_sentences"] = restructure_sentences
RULES["add_citations"] = add_citations
RULES.update(_ACADEMIC_RULES)

# Academic-style rules self-gate (no-op unless academic_style / academic
# tone), so they can sit in every pipeline.  Cleanup transforms run early;
# citation normalization runs dead last so tokens always finish at the
# sentence end.
DEFAULT_PIPELINE = [
    "strip_ai_tells",
    "prune_redundancy",
    "decompound_terms",
    "deflate_modifiers",
    "expand_acronyms",
    "lexical_substitution",
    "adjust_contractions",
    "reorder_clauses",
    "restructure_sentences",
    "academic_connectors",
    "soften_passive",
    "vary_sentence_length",
    "inject_hedges_intensifiers",
    "vary_openers",
    "inject_discourse_markers",
    "add_citations",
    "normalize_citations",
]

# Tones can override the rule order / subset.  Anything not listed here falls
# back to DEFAULT_PIPELINE.
TONE_PIPELINES: Dict[str, List[str]] = {
    "academic": [
        "strip_ai_tells", "prune_redundancy", "decompound_terms",
        "deflate_modifiers", "expand_acronyms", "lexical_substitution",
        "adjust_contractions", "reorder_clauses", "restructure_sentences",
        "academic_connectors", "inject_hedges_intensifiers",
        "vary_sentence_length", "vary_openers", "inject_discourse_markers",
        "add_citations", "normalize_citations",
    ],
    "confident": [
        "strip_ai_tells", "prune_redundancy", "soften_passive",
        "lexical_substitution", "adjust_contractions", "restructure_sentences",
        "inject_hedges_intensifiers", "vary_sentence_length",
        "vary_openers", "inject_discourse_markers", "add_citations",
        "normalize_citations",
    ],
    "storytelling": [
        "strip_ai_tells", "lexical_substitution", "adjust_contractions",
        "reorder_clauses", "restructure_sentences", "vary_sentence_length",
        "vary_openers", "inject_discourse_markers", "add_citations",
        "normalize_citations",
    ],
}


def pipeline_for_tone(tone_name: str) -> "Pipeline":
    """Return the preferred :class:`Pipeline` for ``tone_name``."""
    return Pipeline(rules=list(TONE_PIPELINES.get(tone_name, DEFAULT_PIPELINE)))


@dataclass
class Pipeline:
    """An ordered list of rule names, runnable against split sentences."""

    rules: List[str] = field(default_factory=lambda: list(DEFAULT_PIPELINE))

    def __post_init__(self) -> None:
        unknown = [r for r in self.rules if r not in RULES]
        if unknown:
            raise ValueError(f"Unknown pipeline rules: {unknown}")

    def run(self, sentences: List[str], ctx: Context) -> List[str]:
        for name in self.rules:
            sentences = RULES[name](sentences, ctx)
        return sentences
