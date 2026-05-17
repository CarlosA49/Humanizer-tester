"""Additional pipeline rules.

These follow the same contract as :mod:`humanizer.pipeline`:
``rule(sentences: list[str], ctx) -> list[str]``.

Every rule is deterministic given ``ctx.rng``, never raises on empty / short /
single-word input, and preserves readable capitalization and terminal
punctuation by leaning on the shared helpers.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Tuple

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

# --------------------------------------------------------------------------- #
# AI "red flag" tables (consumed by strip_ai_red_flags)
# --------------------------------------------------------------------------- #
# Em-dash overuse: the em-dash, the double-hyphen and a space-padded hyphen
# used as a dash.  The bare en-dash is intentionally left alone so numeric
# ranges (e.g. "10-20" written as "10–20") survive untouched.
_DASH_RE = re.compile(r"\s*(?:—|--)\s*|\s+-\s+")

# Vague / corporate buzzwords -> plainer, varied wording.  Word-boundary
# matched and case-preserving so only whole words are touched.
_BUZZWORDS: Dict[str, Tuple[str, ...]] = {
    "elevate": ("lift", "improve", "raise"),
    "elevates": ("improves", "lifts", "raises"),
    "elevating": ("improving", "lifting"),
    "elevated": ("improved", "lifted", "raised"),
    "delve": ("dig", "look", "get"),
    "delves": ("digs", "looks"),
    "delving": ("digging", "looking"),
    "innovative": ("new", "fresh", "original", "inventive"),
    "innovation": ("new idea", "breakthrough", "fresh thinking"),
    "cutting-edge": ("modern", "advanced", "new"),
    "state-of-the-art": ("modern", "top", "leading"),
    "game-changer": ("big deal", "turning point", "real shift"),
    "game-changing": ("major", "big", "decisive"),
    "groundbreaking": ("new", "first-of-its-kind", "original"),
    "robust": ("strong", "solid", "reliable", "sturdy"),
    "seamless": ("smooth", "easy", "clean"),
    "seamlessly": ("smoothly", "easily", "cleanly"),
    "synergy": ("teamwork", "good fit", "overlap"),
    "synergies": ("overlaps", "shared wins"),
    "leverage": ("use", "tap", "draw on"),
    "leverages": ("uses", "taps", "draws on"),
    "leveraging": ("using", "tapping"),
    "leveraged": ("used", "tapped"),
    "harness": ("use", "tap", "put to work"),
    "harnesses": ("uses", "taps"),
    "harnessing": ("using", "tapping"),
    "unlock": ("open up", "enable", "reveal"),
    "unlocks": ("opens up", "enables"),
    "unlocking": ("opening up", "enabling"),
    "empower": ("enable", "equip", "let"),
    "empowers": ("lets", "enables", "equips"),
    "empowering": ("enabling", "equipping"),
    "foster": ("build", "encourage", "grow"),
    "fosters": ("builds", "encourages"),
    "fostering": ("building", "encouraging"),
    "showcase": ("show", "highlight", "present"),
    "showcases": ("shows", "highlights"),
    "showcasing": ("showing", "highlighting"),
    "underscore": ("highlight", "stress", "point up"),
    "underscores": ("highlights", "stresses"),
    "underscoring": ("highlighting", "stressing"),
    "pivotal": ("key", "central", "crucial"),
    "holistic": ("whole", "overall", "all-round"),
    "streamline": ("simplify", "tidy up", "smooth out"),
    "streamlines": ("simplifies", "tidies up"),
    "streamlined": ("simplified", "tidied", "leaner"),
    "spearhead": ("lead", "head", "drive"),
    "spearheaded": ("led", "headed", "drove"),
    "practical": ("useful", "hands-on", "real-world", "down-to-earth"),
    "myriad": ("many", "countless", "a lot of"),
    "plethora": ("plenty", "a lot", "no shortage"),
    "paramount": ("vital", "key", "top"),
}
_BUZZWORD_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(w) for w in sorted(_BUZZWORDS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)

# Redundant "filler" preamble that only restates the point -> dropped when it
# leads a sentence.
_PREAMBLES = (
    "in other words", "to put it simply", "simply put", "put simply",
    "that is to say", "in essence", "at its core", "to clarify",
    "to reiterate", "as previously mentioned", "as previously stated",
    "as mentioned earlier", "as noted earlier", "needless to say",
    "it goes without saying that", "what this means is that",
    "the bottom line is that", "when all is said and done",
)
_PREAMBLE_RE = re.compile(
    r"^\s*(?:" + "|".join(re.escape(p) for p in _PREAMBLES) + r")\b[\s,:.—-]*",
    re.IGNORECASE,
)

# Exaggerated / impersonal praise and assistant-style flattery -> softened or
# removed (an empty target deletes the phrase).
_PRAISE: Tuple[Tuple[str, str], ...] = (
    ("that's a great question", ""),
    ("what a great question", ""),
    ("great question", ""),
    ("excellent question", ""),
    ("fantastic question", ""),
    ("that's a great point", ""),
    ("great point", ""),
    ("excellent point", ""),
    ("i would be happy to", "i'll"),
    ("i'd be happy to", "i'll"),
    ("i'm glad you asked", ""),
    ("i hope this helps", ""),
    ("hope this helps", ""),
    ("happy to help", ""),
    ("stands as a testament to", "shows"),
    ("is a testament to", "shows"),
    ("a testament to", "a sign of"),
    ("truly remarkable", "notable"),
    ("truly transformative", "significant"),
    ("incredibly powerful", "effective"),
    ("absolutely essential", "essential"),
    ("highly commendable", "solid"),
)

# Forced / clichéd analogies -> plain phrasing.
_ANALOGIES: Tuple[Tuple[str, str], ...] = (
    ("like a well-oiled machine", "smoothly"),
    ("a well-oiled machine", "a smooth operation"),
    ("a double-edged sword", "a trade-off"),
    ("the tip of the iceberg", "just the start"),
    ("tip of the iceberg", "just the start"),
    ("a perfect storm of", "a pile-up of"),
    ("think of it like", "consider"),
    ("think of it as", "consider it"),
    ("much like", "like"),
    ("akin to", "like"),
)

# "Not only/just X but (also) Y" -> "X and Y" (kills the parallel scaffold
# while keeping both halves).
_PARALLEL_CONJ_RE = re.compile(
    r"\bnot\s+(?:only|just)\s+([^,.;:!?]+?)\s*,?\s+but(?:\s+also)?\s+"
    r"([^,.;:!?]+)",
    re.IGNORECASE,
)
# "It's not just X, it's Y." -> keep the affirmative half ("It's Y.").
_PARALLEL_ECHO_RE = re.compile(
    r"^\s*(it'?s|it is|this is|that is|that'?s|this'?s)\s+not\s+just\s+"
    r"[^,.;:!?]+,\s*(it'?s|it is|this is|that is|that'?s|this'?s)\s+"
    r"([^.;:!?]+)([.;:!?]?)\s*$",
    re.IGNORECASE,
)

# A textbook "rule of three" list of short items -> rebalanced so the
# three-beat cadence is broken without dropping any item.
_TRIAD_RE = re.compile(
    r"\b([A-Za-z][\w'-]*(?:\s[\w'-]+){0,2}),\s+"
    r"([A-Za-z][\w'-]*(?:\s[\w'-]+){0,2}),?\s+and\s+"
    r"([A-Za-z][\w'-]*(?:\s[\w'-]+){0,2})\b"
)
_TRIAD_TEMPLATES = (
    "{a} and {b}, along with {c}",
    "{a}, plus {b} and {c}",
    "{a} and {b} (and {c})",
)

# --------------------------------------------------------------------------- #
# Opening-reconstruction tables (consumed by recast_openings)
# --------------------------------------------------------------------------- #
# Templated "meta" introductions ("In this article we will explore X") -> the
# topic itself, so the paragraph opens on substance instead of throat-clearing.
_META_DOC = (
    r"essays?|articles?|papers?|posts?|guides?|pieces?|sections?|chapters?"
    r"|blogs?|reports?|tutorials?|videos?|discussions?|threads?"
)
_META_VERB = (
    r"discuss|explore|examine|look at|cover|delve into|dig into|talk about"
    r"|present|describe|outline|introduce|walk you through|go over"
    r"|break down|unpack|dive into|take a look at"
)
_RECAST_META = (
    re.compile(
        r"^\s*in\s+this\s+(?:" + _META_DOC + r")\s*,?\s*(?:i|we|this|it)?\s*"
        r"(?:will|aims?\s+to|would\s+like\s+to|am\s+going\s+to|are\s+going\s+to"
        r"|'ll|want\s+to|wish\s+to|seek\s+to|hope\s+to|intend\s+to|plan\s+to)?"
        r"\s*(?:" + _META_VERB + r")\b\s*:?\s*(?P<topic>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*this\s+(?:" + _META_DOC + r")\s+(?:will|aims?\s+to|seeks?\s+to"
        r"|sets?\s+out\s+to|is\s+going\s+to|intends?\s+to)\s+(?:" + _META_VERB
        + r")\b\s*:?\s*(?P<topic>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:let's|let\s+us)\s+(?:dive|delve|jump|get|take\s+a\s+look"
        r"|take\s+a\s+closer\s+look)\s+(?:in|into|right\s+in|started\s+with"
        r"|at)\s*:?\s*(?P<topic>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:today|here|in\s+this\s+section|in\s+what\s+follows|below)"
        r"\s*,?\s*(?:i|we)\s+(?:will|want\s+to|wish\s+to|are\s+going\s+to"
        r"|'ll|would\s+like\s+to)\s+(?:" + _META_VERB
        + r")\b\s*:?\s*(?P<topic>.+)$",
        re.IGNORECASE,
    ),
)

# Empty-subject "there is/are X that ..." -> a direct subject opening.
_RECAST_THERE_SING = re.compile(
    r"^\s*there\s+(?:is|was)\s+(?P<art>an?|the|one|each|every|no)\s+"
    r"(?P<noun>.+?)\s+(?:that|which|who)\s+(?P<rest>.+)$",
    re.IGNORECASE,
)
_RECAST_THERE_PLUR = re.compile(
    r"^\s*there\s+(?:are|were)\s+(?P<quant>many|several|some|a\s+few"
    r"|numerous|a\s+number\s+of|various|countless|multiple)?\s*"
    r"(?P<noun>.+?)\s+(?:that|which|who)\s+(?P<rest>.+)$",
    re.IGNORECASE,
)

# "It is <adj> that <clause>" -> "<Adverb>, <clause>".
_IT_IS_ADV = {
    "clear": "Clearly", "obvious": "Obviously", "evident": "Evidently",
    "likely": "Likely", "unlikely": "Unlikely", "true": "Indeed",
    "important": "Importantly", "interesting": "Interestingly",
    "surprising": "Surprisingly", "notable": "Notably",
    "possible": "Possibly", "apparent": "Apparently",
    "understandable": "Understandably", "clear enough": "Clearly",
}
_RECAST_IT_IS = re.compile(
    r"^\s*it\s+is\s+(?P<adj>" + "|".join(re.escape(a) for a in _IT_IS_ADV)
    + r")\s+that\s+(?P<rest>.+)$",
    re.IGNORECASE,
)

# Throat-clearing lead-ins that delay the point -> dropped.
_RECAST_THROAT = re.compile(
    r"^\s*(?:to\s+begin\s+with|to\s+start\s+with|to\s+start|first\s+of\s+all"
    r"|first\s+off|for\s+starters|at\s+the\s+outset|before\s+we\s+begin"
    r"|before\s+diving\s+in|before\s+we\s+dive\s+in|first\s+and\s+foremost)"
    r"\s*[,:.]?\s+(?P<rest>.+)$",
    re.IGNORECASE,
)

# A nominalized opener -> its verb form.
_RECAST_USE_OF = re.compile(
    r"^\s*the\s+use\s+of\s+(?P<rest>.+)$", re.IGNORECASE
)


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
# 6. strip_ai_red_flags
# --------------------------------------------------------------------------- #
def _has_alpha(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def _tidy(text: str) -> str:
    """Repair punctuation/spacing artifacts left by the scrubbing passes."""
    text = re.sub(r"\s*,(?:\s*,)+", ", ", text)        # ", ," -> ", "
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)        # " ," -> ","
    text = re.sub(r"([,;:])\s*([.!?])", r"\2", text)    # ", ." -> "."
    text = re.sub(r"^\s*[,;:]\s*", "", text)            # leading punctuation
    return re.sub(r"\s{2,}", " ", text).strip()


def strip_ai_red_flags(sentences: List[str], ctx: Context) -> List[str]:
    """Detect and remove the common tells of AI writing.

    Targets, per sentence: em-dash overuse, the "not just X, it's Y" /
    "not only X but also Y" parallel scaffold, the rule-of-three list cadence,
    vague corporate buzzwords, exaggerated/impersonal praise, forced clichéd
    analogies and redundant filler preamble.  (The "no personal anecdote" /
    flat-vibe flags describe an *absence* and cannot be fixed by deletion, so
    they are deliberately out of scope here.)

    Deterministic given ``ctx.rng``; never raises and never emits an empty
    sentence -- any pass that would strip a sentence to nothing is reverted.
    """
    out: List[str] = []
    for sent in sentences:
        original = sent
        new = sent
        if not new.strip():
            out.append(new)
            continue

        term = _terminal_punct(new) or "."

        # 1. Em-dash overuse -> comma (the single clearest tell; unconditional).
        dashed = _DASH_RE.sub(", ", new)
        if dashed != new:
            new = dashed
            ctx.log("ai-flag: replaced an em-dash")

        # 2. Redundant filler preamble that only restates the point.
        if _PREAMBLE_RE.match(new) and ctx.chance(0.85):
            depreamble = _PREAMBLE_RE.sub("", new, count=1)
            if depreamble != new and _has_alpha(depreamble):
                new = depreamble
                ctx.log("ai-flag: dropped filler preamble")

        # 3. Exaggerated / impersonal praise.
        for phrase, repl in _PRAISE:
            pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            if pat.search(new) and ctx.chance(0.85):
                cand = pat.sub(lambda m, r=repl: _match_case(m.group(0), r)
                               if r else "", new)
                if _has_alpha(cand):
                    new = cand
                    ctx.log("ai-flag: removed impersonal praise")

        # 4. Forced / clichéd analogies.
        for phrase, repl in _ANALOGIES:
            pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            if pat.search(new) and ctx.chance(0.8):
                new = pat.sub(lambda m, r=repl: _match_case(m.group(0), r), new)
                ctx.log("ai-flag: defused a forced analogy")

        # 5. "Not only/just X but (also) Y" -> "X and Y".
        if _PARALLEL_CONJ_RE.search(new) and ctx.chance(0.8):
            conj = _PARALLEL_CONJ_RE.sub(
                lambda m: f"{m.group(1).strip()} and {m.group(2).strip()}",
                new,
                count=1,
            )
            if conj != new:
                new = conj
                ctx.log("ai-flag: flattened a parallel structure")

        # 5b. "It's not just X, it's Y." -> keep the affirmative half.
        echo = _PARALLEL_ECHO_RE.match(new)
        if echo and _has_alpha(echo.group(3)) and ctx.chance(0.8):
            subject = _match_case(echo.group(1), echo.group(1))
            tail = echo.group(3).strip()
            rebuilt = f"{subject} {tail}{echo.group(4) or ''}"
            if _has_alpha(rebuilt):
                new = rebuilt
                ctx.log("ai-flag: flattened a parallel structure")

        # 6. Vague / corporate buzzwords -> plainer wording.
        def _debuzz(match: "re.Match") -> str:
            word = match.group(0)
            if not ctx.chance(0.8):
                return word
            pool = _BUZZWORDS[word.lower()]
            choice = pool[ctx.rng.randrange(len(pool))]
            ctx.log(f"ai-flag: replaced buzzword {word.lower()!r}")
            return _match_case(word, choice)

        new = _BUZZWORD_RE.sub(_debuzz, new)

        # 7. Rule-of-three list cadence -> rebalanced (no item dropped).
        if _TRIAD_RE.search(new) and ctx.chance(0.7):
            tmpl = ctx.rng.choice(_TRIAD_TEMPLATES)

            def _rebalance(m: "re.Match", tmpl=tmpl) -> str:
                return tmpl.format(
                    a=m.group(1), b=m.group(2), c=m.group(3)
                )

            rebalanced = _TRIAD_RE.sub(_rebalance, new, count=1)
            if rebalanced != new:
                new = rebalanced
                ctx.log("ai-flag: broke a rule-of-three list")

        new = _tidy(new)
        if not _has_alpha(new):
            out.append(original)
            continue
        if new != original:
            new = _ensure_terminal(_capitalize_first(new).rstrip(".!?") + term)
        out.append(new)
    return out


# --------------------------------------------------------------------------- #
# 7. recast_openings
# --------------------------------------------------------------------------- #
def recast_openings(sentences: List[str], ctx: Context) -> List[str]:
    """Paraphrase / reconstruct the *opening* of a paragraph or sentence.

    The first sentence is the paragraph's introduction, so it is treated as
    the introduction and recast a little more eagerly than the rest.  Each
    sentence's opening frame is rebuilt rather than just word-swapped:

    * templated "meta" intros ("In this article we will explore X") -> X
    * empty-subject "There is/are X that ..." -> a direct subject opening
    * "It is <adj> that <clause>" -> "<Adverb>, <clause>"
    * throat-clearing lead-ins ("To begin with, ...") -> dropped
    * a nominalized "The use of X ..." opener -> "Using X ..."

    The reconstruction runs before the lexical-paraphrase rule, so the
    rebuilt opening is then paraphrased and tone-flavoured like the rest of
    the text.  Deterministic given ``ctx.rng``; it draws no randomness when
    no opening frame matches, so untouched text is bit-for-bit unchanged.
    """
    out: List[str] = []
    for idx, sent in enumerate(sentences):
        original = sent
        if not sent.strip():
            out.append(sent)
            continue

        # The introduction (first sentence) is recast more readily.
        base = 0.9 if idx == 0 else 0.7
        term = _terminal_punct(sent) or "."
        rebuilt = None
        why = ""

        for pat in _RECAST_META:
            m = pat.match(sent)
            if m and _has_alpha(m.group("topic")):
                rebuilt = m.group("topic").strip()
                why = "reconstructed a templated introduction"
                break

        if rebuilt is None:
            m = _RECAST_THROAT.match(sent)
            if m and _has_alpha(m.group("rest")):
                rebuilt = m.group("rest").strip()
                why = "dropped a throat-clearing opener"

        if rebuilt is None:
            m = _RECAST_IT_IS.match(sent)
            if m and _has_alpha(m.group("rest")):
                adv = _IT_IS_ADV[m.group("adj").lower()]
                rebuilt = f"{adv}, {m.group('rest').strip()}"
                why = "recast an 'it is ... that' opener"

        if rebuilt is None:
            m = _RECAST_THERE_SING.match(sent)
            if m and _has_alpha(m.group("noun")) and _has_alpha(
                m.group("rest")
            ):
                rebuilt = (
                    f"{m.group('art')} {m.group('noun').strip()} "
                    f"{m.group('rest').strip()}"
                )
                why = "rebuilt an empty-subject opener"

        if rebuilt is None:
            m = _RECAST_THERE_PLUR.match(sent)
            if m and _has_alpha(m.group("noun")) and _has_alpha(
                m.group("rest")
            ):
                quant = (m.group("quant") or "").strip()
                lead = f"{quant} " if quant else ""
                rebuilt = (
                    f"{lead}{m.group('noun').strip()} "
                    f"{m.group('rest').strip()}"
                )
                why = "rebuilt an empty-subject opener"

        if rebuilt is None:
            m = _RECAST_USE_OF.match(sent)
            if m and _has_alpha(m.group("rest")):
                rebuilt = f"Using {m.group('rest').strip()}"
                why = "recast a nominalized opener"

        if rebuilt is not None and ctx.chance(base):
            candidate = _ensure_terminal(
                _capitalize_first(rebuilt).rstrip(".!?") + term
            )
            if _has_alpha(candidate):
                ctx.log(f"structure: {why}")
                out.append(candidate)
                continue

        out.append(original)
    return out


# --------------------------------------------------------------------------- #
EXTRA_RULES: Dict[str, Callable[[List[str], Context], List[str]]] = {
    "reorder_clauses": reorder_clauses,
    "vary_openers": vary_openers,
    "inject_hedges_intensifiers": inject_hedges_intensifiers,
    "prune_redundancy": prune_redundancy,
    "soften_passive": soften_passive,
    "strip_ai_red_flags": strip_ai_red_flags,
    "recast_openings": recast_openings,
}
