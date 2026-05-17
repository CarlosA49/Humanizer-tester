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

# Only these voices get canned stand-alone fragments injected; formal tones
# stay meaning-preserving.
_FRAGMENT_TONES = {"casual", "storytelling", "witty", "friendly"}


@dataclass
class Context:
    tone: Tone
    rng: Random
    strength: float = 0.5  # 0..1, scales how aggressively rules fire
    changes: List[str] = field(default_factory=list)

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


def _is_proper_token(token: str) -> bool:
    """A token that must keep its casing (acronym, model name, proper noun).

    "YOLOv8", "UWB", "ArUco", "I" must never be lower-cased when a sentence
    is re-opened with a connector/marker.  Heuristic: a digit, an all-caps
    word, or any uppercase letter past position 0 (internal capital) marks a
    name/acronym; a lone "I" is always kept.
    """
    core = re.sub(r"[^A-Za-z0-9]", "", token)
    if not core:
        return False
    if core == "I":
        return True
    if any(c.isdigit() for c in core):
        return True
    if core.isupper() and len(core) > 1:
        return True
    return any(c.isupper() for c in core[1:])


def _lower_first(sentence: str) -> str:
    """Lower-case the first word only when it is an ordinary word.

    Leaves acronyms / model names / proper nouns ("YOLOv8", "UWB") intact so
    re-opening a sentence with a marker does not produce "yOLOv8".
    """
    s = sentence.lstrip()
    if not s:
        return s
    first = s.split(None, 1)[0]
    if _is_proper_token(first):
        return s
    return s[0].lower() + s[1:] if s[:1].isupper() else s


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


# Function words and connectors are left alone: swapping them ("and" ->
# "plus"/"as well as", "with" -> "coupled with") is the single biggest
# source of unnatural, machine-sounding output.
_PROTECTED_LEX = {
    "and", "or", "but", "nor", "so", "yet", "for", "with", "as", "of",
    "to", "in", "on", "at", "by", "is", "are", "was", "were", "be",
    "a", "an", "the", "this", "that", "these", "those", "it", "its",
}


def lexical_substitution(sentences: List[str], ctx: Context) -> List[str]:
    used: Dict[str, set] = {}
    syn = ctx.tone.synonyms
    # Every multi-word key in the tone dictionary, longest first so e.g.
    # "due to the fact that" wins over "the fact that".
    phrase_keys = sorted(
        (k for k in syn if " " in k), key=len, reverse=True
    )
    out = []
    for sent in sentences:
        text = sent
        # A conservative per-sentence cap keeps most of the original wording
        # intact, so substitutions read like word choice, not word salad.
        n_words = len(re.findall(r"[A-Za-z']+", sent))
        budget = max(1, round(0.22 * n_words))
        made = 0

        # Multi-word phrase pass first.
        for key in phrase_keys:
            if made >= budget:
                break
            pat = re.compile(r"\b" + re.escape(key) + r"\b", re.IGNORECASE)

            def _sub(m, key=key):
                nonlocal made
                if made >= budget or not ctx.chance(0.28):
                    return m.group(0)
                pool = [w for w in syn[key] if w not in used.get(key, set())] or syn[key]
                choice = _surprisal_weighted_choice(ctx.rng, pool)
                used.setdefault(key, set()).add(choice)
                made += 1
                ctx.log(f"lexical: {m.group(0)!r} -> {choice!r}")
                return _match_case(m.group(0), choice)

            text = pat.sub(_sub, text)

        # Single-word pass.
        tokens = _TOKEN_RE.findall(text)
        for i, tok in enumerate(tokens):
            if made >= budget:
                break
            low = tok.lower()
            if (
                low in syn
                and low not in _PROTECTED_LEX
                and not _is_proper_token(tok)
                and ctx.chance(0.28)
            ):
                pool = [w for w in syn[low] if w not in used.get(low, set())] or syn[low]
                choice = _surprisal_weighted_choice(ctx.rng, pool)
                used.setdefault(low, set()).add(choice)
                tokens[i] = _match_case(tok, choice)
                made += 1
                ctx.log(f"lexical: {tok!r} -> {choice!r}")
        out.append("".join(tokens))
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
    # Never break an enumeration's ", and X" into a sub-clausal fragment
    # ("..., and background interference." -> "Background interference.").
    # If either side is too short to stand as a clause, don't split here.
    if len(first.split()) < 5 or len(rest.split()) < 5:
        return None
    return first, rest


def vary_sentence_length(sentences: List[str], ctx: Context) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(sentences):
        sent = sentences[i].strip()
        words = sent.split()

        # Split only genuine run-ons, and only once.  Conservative mode
        # chops less: an over-split paragraph reads flat and machine-like,
        # and keeping one long sentence among shorter ones is exactly what
        # lifts the human length spread.
        if len(words) >= 24:
            split = _split_once(sent, ctx)
            if split and ctx.chance(0.85):
                first, rest = split
                ctx.log("burstiness: split a long sentence")
                out.append(first)
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
            merged = f"{sent.rstrip('.!?')}, {conn} {_lower_first(nxt)}"
            ctx.log("burstiness: merged two short sentences")
            out.append(_ensure_terminal(merged))
            i += 2
            continue

        out.append(_ensure_terminal(sent))

        # Drop a punchy stand-alone fragment after a longer sentence -- only
        # for narrative / casual tones, where a canned aside fits the voice.
        # Formal tones (academic, professional, …) keep their own wording so
        # the text stays meaning-preserving and never reads like noise.
        if (
            ctx.tone.name in _FRAGMENT_TONES
            and len(words) >= 14
            and ctx.chance(0.45)
        ):
            frag = ctx.rng.choice(ctx.tone.fragments)
            ctx.log("burstiness: added a short fragment")
            out.append(frag)
        i += 1
    return out


# A sentence already opening with one of these reads as "marked"; adding
# another marker on top is the stacked-transition AI tell, so we skip it.
_LEADING_MARKERS = {
    "however", "moreover", "furthermore", "additionally", "therefore",
    "thus", "consequently", "hence", "notably", "crucially", "importantly",
    "arguably", "clearly", "honestly", "overall", "first", "finally",
    "meanwhile", "still", "instead", "besides", "ultimately", "indeed",
    "similarly", "conversely", "nonetheless", "nevertheless", "accordingly",
}


def _is_marked_opening(sentence: str, ctx: Context) -> bool:
    s = sentence.lstrip()
    if any(s.startswith(st) for st in ctx.tone.starters):
        return True
    m = re.match(r"([A-Za-z']+)\s*,", s)
    return bool(m and m.group(1).lower() in _LEADING_MARKERS)


def inject_discourse_markers(sentences: List[str], ctx: Context) -> List[str]:
    out = []
    # Natural, not spammy: markers are allowed, but never two in a row and
    # never stacked on an already-marked opening (the real machine tell), and
    # proper nouns keep their casing.
    budget = max(1, int(len(sentences) * (0.3 + 0.4 * ctx.strength)))
    prev_added = False
    for idx, sent in enumerate(sentences):
        new = sent
        if (
            budget > 0
            and idx != 0
            and not prev_added
            and not _is_marked_opening(new, ctx)
            and ctx.chance(0.5)
        ):
            starter = ctx.rng.choice(ctx.tone.starters)
            new = f"{starter} {_lower_first(new)}"
            ctx.log(f"voice: opened a sentence with {starter!r}")
            budget -= 1
            prev_added = True
        else:
            prev_added = False
        out.append(new)
    return out


RULES: Dict[str, Callable[[List[str], Context], List[str]]] = {
    "strip_ai_tells": strip_ai_tells,
    "lexical_substitution": lexical_substitution,
    "adjust_contractions": adjust_contractions,
    "vary_sentence_length": vary_sentence_length,
    "inject_discourse_markers": inject_discourse_markers,
}

# Registered after definition to avoid a circular import (extra_rules imports
# Context and the helpers from this module).
from .extra_rules import EXTRA_RULES  # noqa: E402

RULES.update(EXTRA_RULES)

DEFAULT_PIPELINE = [
    "strip_ai_tells",
    "strip_ai_red_flags",
    "recast_openings",
    "prune_redundancy",
    "lexical_substitution",
    "adjust_contractions",
    "humanize_phrasing",
    "reorder_clauses",
    "soften_passive",
    "vary_sentence_length",
    "inject_hedges_intensifiers",
    "vary_openers",
    "inject_discourse_markers",
]

# Tones can override the rule order / subset.  Anything not listed here falls
# back to DEFAULT_PIPELINE.
TONE_PIPELINES: Dict[str, List[str]] = {
    "academic": [
        "strip_ai_tells", "strip_ai_red_flags", "recast_openings",
        "prune_redundancy", "lexical_substitution", "adjust_contractions",
        "humanize_phrasing", "reorder_clauses", "inject_hedges_intensifiers",
        "vary_sentence_length", "vary_openers", "inject_discourse_markers",
    ],
    "confident": [
        "strip_ai_tells", "strip_ai_red_flags", "recast_openings",
        "prune_redundancy", "soften_passive", "lexical_substitution",
        "adjust_contractions", "humanize_phrasing",
        "inject_hedges_intensifiers", "vary_sentence_length",
        "vary_openers", "inject_discourse_markers",
    ],
    "storytelling": [
        "strip_ai_tells", "strip_ai_red_flags", "recast_openings",
        "lexical_substitution", "adjust_contractions", "humanize_phrasing",
        "reorder_clauses", "vary_sentence_length", "vary_openers",
        "inject_discourse_markers",
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
