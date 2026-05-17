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

from .tones import Tone

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*|[^A-Za-z\s]+|\s+")

# Multi-word synonym keys are matched before single words.
_MULTIWORD_KEYS = (
    "very important", "a lot", "a number of", "in order to",
    "show that", "good idea", "i think",
)

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


def lexical_substitution(sentences: List[str], ctx: Context) -> List[str]:
    used: Dict[str, set] = {}
    syn = ctx.tone.synonyms
    out = []
    for sent in sentences:
        text = sent
        # Multi-word phrase pass first.
        for key in _MULTIWORD_KEYS:
            if key not in syn:
                continue
            pat = re.compile(re.escape(key), re.IGNORECASE)

            def _sub(m, key=key):
                if not ctx.chance(0.5):
                    return m.group(0)
                pool = [w for w in syn[key] if w not in used.get(key, set())] or syn[key]
                choice = ctx.rng.choice(pool)
                used.setdefault(key, set()).add(choice)
                ctx.log(f"lexical: {m.group(0)!r} -> {choice!r}")
                return _match_case(m.group(0), choice)

            text = pat.sub(_sub, text)

        # Single-word pass.
        tokens = _TOKEN_RE.findall(text)
        for i, tok in enumerate(tokens):
            low = tok.lower()
            if low in syn and ctx.chance(0.55):
                pool = [w for w in syn[low] if w not in used.get(low, set())] or syn[low]
                choice = ctx.rng.choice(pool)
                used.setdefault(low, set()).add(choice)
                tokens[i] = _match_case(tok, choice)
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


def vary_sentence_length(sentences: List[str], ctx: Context) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(sentences):
        sent = sentences[i].strip()
        words = sent.split()

        # Split long, run-on sentences -> raises burstiness.
        if len(words) >= 22:
            low = sent.lower()
            best = -1
            for marker in _SPLIT_MARKERS:
                pos = low.find(marker, len(sent) // 3)
                if pos != -1 and (best == -1 or pos < best):
                    best = pos
                    chosen = marker
            if best != -1 and ctx.chance(0.85):
                first = _ensure_terminal(sent[:best])
                rest = sent[best + len(chosen) :].strip()
                second = _capitalize_first(_ensure_terminal(rest))
                ctx.log("burstiness: split a long sentence")
                out.append(first)
                out.append(second)
                i += 1
                continue

        # Merge a very short sentence with the next one.
        if (
            len(words) <= 5
            and i + 1 < len(sentences)
            and ctx.chance(0.5)
        ):
            conn = ctx.rng.choice(ctx.tone.connectors)
            nxt = sentences[i + 1].strip()
            merged = f"{sent.rstrip('.!?')}, {conn} {nxt[0].lower()}{nxt[1:]}"
            ctx.log("burstiness: merged two short sentences")
            out.append(_ensure_terminal(merged))
            i += 2
            continue

        out.append(_ensure_terminal(sent))

        # Occasionally drop a punchy fragment after a long sentence.
        if len(words) >= 16 and ctx.chance(0.3):
            frag = ctx.rng.choice(ctx.tone.fragments)
            ctx.log("burstiness: added a short fragment")
            out.append(frag)
        i += 1
    return out


def inject_discourse_markers(sentences: List[str], ctx: Context) -> List[str]:
    out = []
    budget = max(1, int(len(sentences) * (0.25 + 0.4 * ctx.strength)))
    for idx, sent in enumerate(sentences):
        new = sent
        already = any(new.startswith(s) for s in ctx.tone.starters)
        if budget > 0 and idx != 0 and not already and ctx.chance(0.5):
            starter = ctx.rng.choice(ctx.tone.starters)
            body = new[0].lower() + new[1:] if new[:1].isupper() else new
            new = f"{starter} {body}"
            ctx.log(f"voice: opened a sentence with {starter!r}")
            budget -= 1
        elif budget > 0 and ", " in new and ctx.chance(0.25):
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

DEFAULT_PIPELINE = [
    "strip_ai_tells",
    "lexical_substitution",
    "adjust_contractions",
    "vary_sentence_length",
    "inject_discourse_markers",
]


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
