"""Tone-flavoured reconstruction & paraphrasing pattern banks.

This module is pure data plus a small inventory helper.  The paraphrase
*engine* (:mod:`humanizer.paraphrase`) owns a curated set of structural
transforms (clause reordering, expletive trimming, light-verb unpacking,
cleft/topic reframing, paragraph reflow, ...).  Each transform draws its
surface wording from the per-tone slot banks defined here, so the effective
pattern space -- structural transforms x tone-flavoured fills -- runs into the
thousands per tone while staying hand-curated and maintainable.

Nothing here is random; the engine selects deterministically via ``ctx.rng``.
"""

from __future__ import annotations

from typing import Dict, List

TONES: List[str] = [
    "academic", "casual", "confident", "empathetic", "friendly",
    "persuasive", "professional", "storytelling", "witty",
]

# --------------------------------------------------------------------------- #
# Shared: light-verb / nominalisation unpacking ("make a decision" -> "decide")
# Raises concision and perplexity for every tone; inherited, not per-tone.
# --------------------------------------------------------------------------- #
NOMINALIZATIONS: Dict[str, str] = {
    "make a decision": "decide",
    "make a choice": "choose",
    "reach a conclusion": "conclude",
    "come to a conclusion": "conclude",
    "give an explanation": "explain",
    "provide an explanation": "explain",
    "provide a description": "describe",
    "give a description": "describe",
    "carry out an analysis": "analyze",
    "conduct an analysis": "analyze",
    "perform an evaluation": "evaluate",
    "carry out an evaluation": "evaluate",
    "do an assessment": "assess",
    "make an assessment": "assess",
    "take into consideration": "consider",
    "give consideration to": "consider",
    "make an improvement": "improve",
    "make improvements": "improve",
    "bring about a change": "change",
    "make a contribution": "contribute",
    "make a comparison": "compare",
    "draw a comparison": "compare",
    "have an impact on": "affect",
    "have an effect on": "affect",
    "make use of": "use",
    "put to use": "use",
    "make a recommendation": "recommend",
    "give a recommendation": "recommend",
    "make a suggestion": "suggest",
    "provide assistance": "help",
    "offer assistance": "help",
    "give an indication": "indicate",
    "make a determination": "determine",
    "conduct an investigation": "investigate",
    "carry out an investigation": "investigate",
    "make a discovery": "discover",
    "reach an agreement": "agree",
    "come to an agreement": "agree",
    "make an attempt": "try",
    "make an effort": "try",
    "place an emphasis on": "emphasize",
    "put an emphasis on": "emphasize",
    "give priority to": "prioritize",
    "make a prediction": "predict",
    "provide confirmation": "confirm",
    "give approval": "approve",
    "make a request": "request",
    "have a preference for": "prefer",
    "take action on": "act on",
    "give a response": "respond",
    "make a statement": "state",
    "draw a distinction": "distinguish",
    "have knowledge of": "know",
    "have an understanding of": "understand",
    "be in agreement with": "agree with",
    "be of the opinion that": "think",
    "be in possession of": "have",
}

# --------------------------------------------------------------------------- #
# Per-tone reframing FRAMES.
#
# Keyed by rhetorical relation.  ``{x}`` / ``{y}`` are slots the engine fills
# with clauses pulled out of the original sentence.  Multiple variants per
# relation per tone give the combinatorial depth.
# --------------------------------------------------------------------------- #
def _frames() -> Dict[str, Dict[str, List[str]]]:
    common_importance = [
        "what really matters here is {x}",
        "the part that counts is {x}",
        "{x} is the piece worth holding onto",
    ]
    common_cause = [
        "{y}, and that is why {x}",
        "{x} — the reason being {y}",
        "because {y}, {x}",
    ]
    common_contrast = [
        "{x}; even so, {y}",
        "{x} — yet {y}",
        "{x}. The flip side: {y}",
    ]
    common_reco = [
        "the move is to {x}",
        "worth doing: {x}",
        "{x} — that is the call",
    ]
    common_evidence = [
        "the evidence points one way: {x}",
        "what the data says is {x}",
        "{x}, and that bears out",
    ]
    common_sequence = [
        "first {x}; then {y}",
        "{x}, and from there {y}",
        "start with {x}, build to {y}",
    ]

    F: Dict[str, Dict[str, List[str]]] = {}
    for t in TONES:
        F[t] = {
            "importance": list(common_importance),
            "cause": list(common_cause),
            "contrast": list(common_contrast),
            "recommendation": list(common_reco),
            "evidence": list(common_evidence),
            "sequence": list(common_sequence),
        }

    F["academic"]["importance"] += [
        "of central concern here is {x}",
        "{x} is, arguably, the salient consideration",
        "it is {x} that proves consequential",
    ]
    F["academic"]["cause"] += [
        "given that {y}, it follows that {x}",
        "{x}, insofar as {y}",
        "{x}; this obtains because {y}",
    ]
    F["academic"]["evidence"] += [
        "the findings substantiate {x}",
        "{x}, a pattern the data supports",
        "evidence converges on {x}",
    ]
    F["casual"]["importance"] += [
        "honestly, the main thing is {x}",
        "{x} is what it really comes down to",
        "the bit that matters? {x}",
    ]
    F["casual"]["recommendation"] += [
        "just {x} — that's the move",
        "easiest path: {x}",
        "do {x} and you're set",
    ]
    F["confident"]["importance"] += [
        "make no mistake: {x} is the thing",
        "{x}. That is non-negotiable",
        "the deciding factor is {x}, plainly",
    ]
    F["confident"]["recommendation"] += [
        "{x}. Do it",
        "the answer is simple — {x}",
        "no debate: {x}",
    ]
    F["empathetic"]["importance"] += [
        "what feels most important is {x}",
        "{x}, and that is completely valid",
        "gently, the heart of it is {x}",
    ]
    F["empathetic"]["cause"] += [
        "it makes sense that {x}, because {y}",
        "{x} — and given {y}, that is understandable",
        "since {y}, it is natural that {x}",
    ]
    F["friendly"]["importance"] += [
        "here's the thing that matters: {x}",
        "{x} — that's the bit to remember",
        "good to keep in mind: {x}",
    ]
    F["friendly"]["recommendation"] += [
        "I'd just {x}",
        "easy win: {x}",
        "give this a go — {x}",
    ]
    F["persuasive"]["importance"] += [
        "here is what you cannot ignore: {x}",
        "{x}. That changes everything",
        "the single thing that matters is {x}",
    ]
    F["persuasive"]["recommendation"] += [
        "act now: {x}",
        "the smart move is clear — {x}",
        "{x}, before the window closes",
    ]
    F["professional"]["importance"] += [
        "the key consideration is {x}",
        "{x} is the priority that drives outcomes",
        "strategically, {x} is what matters",
    ]
    F["professional"]["recommendation"] += [
        "the recommended path is to {x}",
        "next step: {x}",
        "we should {x} to move this forward",
    ]
    F["storytelling"]["importance"] += [
        "and this was the part that mattered: {x}",
        "{x} — that was the turn",
        "everything hinged on {x}",
    ]
    F["storytelling"]["sequence"] += [
        "first came {x}; then, slowly, {y}",
        "{x}. And then {y}",
        "it began with {x} and led to {y}",
    ]
    F["witty"]["importance"] += [
        "plot twist: {x} is the whole point",
        "{x} — kind of a big deal, as it turns out",
        "spoiler: it all comes down to {x}",
    ]
    F["witty"]["recommendation"] += [
        "bold suggestion: {x}",
        "{x}. Revolutionary, I know",
        "do {x}; thank me later",
    ]
    return F


TONE_FRAMES: Dict[str, Dict[str, List[str]]] = _frames()

# --------------------------------------------------------------------------- #
# Per-tone PIVOTS: paragraph / discourse hinges used when reflowing or
# restructuring across sentence boundaries.
# --------------------------------------------------------------------------- #
TONE_PIVOTS: Dict[str, List[str]] = {
    "academic": [
        "More precisely,", "By the same token,", "It follows that",
        "A further point:", "Considered together,", "On this reading,",
        "Crucially,", "In this connection,",
    ],
    "casual": [
        "Anyway,", "So yeah,", "Long story short,", "Here's the thing —",
        "On top of that,", "Which, honestly,", "Point is,", "Either way,",
    ],
    "confident": [
        "Bottom line:", "Make no mistake —", "Here's the truth:",
        "Let's be clear:", "No question:", "The fact is,",
        "Plainly put,", "Full stop —",
    ],
    "empathetic": [
        "And that's okay.", "Gently, though —", "If it helps,",
        "Take a breath here:", "Just as importantly,", "Please know,",
        "What's more,", "Either way, you're not alone —",
    ],
    "friendly": [
        "By the way,", "Quick heads-up —", "Good news:",
        "Just so you know,", "On top of that,", "Honestly,",
        "Here's a tip:", "And hey,",
    ],
    "persuasive": [
        "Here's why this matters:", "Think about it:", "The reality is,",
        "Consider this:", "Now ask yourself —", "Bottom line —",
        "And that's the point:", "Make no mistake —",
    ],
    "professional": [
        "In practice,", "From a delivery standpoint,", "Strategically,",
        "To be clear,", "Importantly,", "Net-net,",
        "Operationally,", "On balance,",
    ],
    "storytelling": [
        "And then,", "Slowly,", "Here's where it turns:",
        "What happened next was simple:", "Picture this —",
        "Somewhere in there,", "Before long,", "And just like that,",
    ],
    "witty": [
        "Plot twist:", "Spoiler alert —", "Against all odds,",
        "Funnily enough,", "In a stunning turn,", "Naturally,",
        "As one does,", "Predictably,",
    ],
}


def pattern_inventory(tone: str) -> Dict[str, int]:
    """Return the (effective) reconstruction-pattern counts for ``tone``.

    ``structural_transforms`` is the count of distinct engine transforms;
    ``reframe_templates`` counts tone frame variants; ``effective_patterns``
    estimates the combinatorial reach (each structural transform composes with
    the tone's fills, pivots and the shared nominalisation bank).
    """
    frames = TONE_FRAMES.get(tone, {})
    reframes = sum(len(v) for v in frames.values())
    pivots = len(TONE_PIVOTS.get(tone, []))
    from . import paraphrase as _engine  # local import avoids a cycle

    structural = len(_engine.TRANSFORMS)
    nominal = len(NOMINALIZATIONS)
    # Effective reach: every structural transform can pair with any reframe
    # template or pivot, on top of the shared light-verb bank.
    effective = structural * (reframes + pivots) + nominal + reframes
    return {
        "structural_transforms": structural,
        "reframe_templates": reframes,
        "pivots": pivots,
        "nominalizations": nominal,
        "effective_patterns": effective,
    }
