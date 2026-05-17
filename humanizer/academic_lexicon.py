"""Curated academic-register synonym bank.

In academic style the humanizer substitutes *only* through this bank instead
of the broad (casual-leaning) tone dictionary, so every swap is a genuine
scholarly-register alternative and stays grammatically substitutable (entries
are inflection-matched: ``show`` / ``shows`` / ``showed`` / ``shown`` are
separate keys).  Words absent from the bank are left untouched -- which is
exactly what a careful human editor of a paper does.

Pure data plus a tiny lookup; no imports from the rest of the package so it is
safe to import anywhere.
"""

from __future__ import annotations

from typing import Dict, List

# --------------------------------------------------------------------------- #
# Verbs (inflection-matched groups).
# --------------------------------------------------------------------------- #
_VERBS: Dict[str, List[str]] = {
    "use": ["employ", "apply", "utilize", "adopt"],
    "uses": ["employs", "applies", "utilizes", "adopts"],
    "used": ["employed", "applied", "utilized", "adopted"],
    "using": ["employing", "applying", "utilizing", "adopting"],
    "show": ["demonstrate", "indicate", "reveal", "report"],
    "shows": ["demonstrates", "indicates", "reveals", "reports"],
    "showed": ["demonstrated", "indicated", "revealed", "reported"],
    "shown": ["demonstrated", "indicated", "reported"],
    "improve": ["enhance", "refine", "strengthen"],
    "improves": ["enhances", "refines", "strengthens"],
    "improved": ["enhanced", "refined", "strengthened"],
    "improving": ["enhancing", "refining", "strengthening"],
    "support": ["corroborate", "reinforce", "substantiate", "underpin"],
    "supports": ["corroborates", "reinforces", "substantiates", "underpins"],
    "supported": ["corroborated", "reinforced", "substantiated"],
    "address": ["tackle", "mitigate", "handle"],
    "addresses": ["tackles", "mitigates", "handles"],
    "addressed": ["tackled", "mitigated", "handled"],
    "propose": ["put forward", "introduce", "present"],
    "proposes": ["puts forward", "introduces", "presents"],
    "proposed": ["put forward", "introduced", "presented"],
    "investigate": ["examine", "explore", "study"],
    "investigated": ["examined", "explored", "studied"],
    "investigates": ["examines", "explores", "studies"],
    "develop": ["devise", "build", "construct"],
    "developed": ["devised", "built", "constructed"],
    "develops": ["devises", "builds", "constructs"],
    "implement": ["deploy", "realize", "apply"],
    "implemented": ["deployed", "realized", "applied"],
    "implements": ["deploys", "realizes", "applies"],
    "evaluate": ["assess", "appraise", "gauge"],
    "evaluated": ["assessed", "appraised", "gauged"],
    "evaluates": ["assesses", "appraises", "gauges"],
    "analyze": ["examine", "assess", "characterize"],
    "analyzed": ["examined", "assessed", "characterized"],
    "analyzes": ["examines", "assesses", "characterizes"],
    "achieve": ["attain", "obtain", "reach"],
    "achieved": ["attained", "obtained", "reached"],
    "achieves": ["attains", "obtains", "reaches"],
    "enable": ["allow", "permit", "facilitate"],
    "enables": ["allows", "permits", "facilitates"],
    "enabled": ["allowed", "permitted", "facilitated"],
    "provide": ["offer", "yield", "afford", "deliver"],
    "provides": ["offers", "yields", "affords", "delivers"],
    "provided": ["offered", "yielded", "afforded"],
    "require": ["necessitate", "demand", "call for"],
    "requires": ["necessitates", "demands", "calls for"],
    "required": ["necessitated", "demanded"],
    "affect": ["influence", "impact", "alter"],
    "affects": ["influences", "impacts", "alters"],
    "affected": ["influenced", "impacted", "altered"],
    "identify": ["detect", "recognize", "distinguish"],
    "identified": ["detected", "recognized", "distinguished"],
    "identifies": ["detects", "recognizes", "distinguishes"],
    "obtain": ["acquire", "derive", "secure"],
    "obtained": ["acquired", "derived", "secured"],
    "observe": ["note", "record", "report"],
    "observed": ["noted", "recorded", "reported"],
    "examine": ["investigate", "assess", "inspect"],
    "examined": ["investigated", "assessed", "inspected"],
    "establish": ["determine", "ascertain", "confirm"],
    "established": ["determined", "ascertained", "confirmed"],
    "present": ["report", "describe", "outline"],
    "presented": ["reported", "described", "outlined"],
    "describe": ["characterize", "outline", "detail"],
    "described": ["characterized", "outlined", "detailed"],
    "focus": ["concentrate", "center"],
    "focuses": ["concentrates", "centers"],
    "focused": ["concentrated", "centered"],
    "indicate": ["suggest", "imply", "signal"],
    "indicates": ["suggests", "implies", "signals"],
    "indicated": ["suggested", "implied", "signaled"],
    "suggest": ["indicate", "imply", "point to"],
    "suggests": ["indicates", "implies", "points to"],
    "suggested": ["indicated", "implied"],
    "integrate": ["combine", "incorporate", "couple"],
    "integrated": ["combined", "incorporated", "coupled"],
    "monitor": ["track", "observe", "survey"],
    "monitored": ["tracked", "observed", "surveyed"],
    "monitoring": ["tracking", "observation", "surveillance"],
    "detect": ["identify", "recognize", "sense"],
    "detected": ["identified", "recognized", "sensed"],
    "verify": ["confirm", "validate", "corroborate"],
    "verified": ["confirmed", "validated", "corroborated"],
    "ensure": ["guarantee", "secure", "safeguard"],
    "consider": ["examine", "regard", "treat"],
    "considered": ["examined", "regarded", "treated"],
    "determine": ["establish", "ascertain", "identify"],
    "determined": ["established", "ascertained", "identified"],
    "perform": ["carry out", "conduct", "execute"],
    "performed": ["carried out", "conducted", "executed"],
    "conduct": ["carry out", "perform", "undertake"],
    "conducted": ["carried out", "performed", "undertaken"],
    "limit": ["constrain", "restrict", "bound"],
    "limits": ["constrains", "restricts", "bounds"],
    "limited": ["constrained", "restricted", "bounded"],
    "evolve": ["develop", "advance", "progress"],
    "highlight": ["underscore", "emphasize", "foreground"],
    "highlights": ["underscores", "emphasizes"],
    "highlighted": ["underscored", "emphasized"],
}

# --------------------------------------------------------------------------- #
# Nouns.
# --------------------------------------------------------------------------- #
_NOUNS: Dict[str, List[str]] = {
    "study": ["investigation", "analysis", "work"],
    "studies": ["investigations", "analyses", "works"],
    "research": ["investigation", "scholarship", "inquiry"],
    "finding": ["result", "observation", "outcome"],
    "findings": ["results", "observations", "outcomes"],
    "result": ["outcome", "finding"],
    "results": ["outcomes", "findings"],
    "approach": ["method", "technique", "strategy"],
    "approaches": ["methods", "techniques", "strategies"],
    "method": ["approach", "technique", "procedure"],
    "methods": ["approaches", "techniques", "procedures"],
    "technique": ["method", "approach", "procedure"],
    "techniques": ["methods", "approaches", "procedures"],
    "system": ["framework", "architecture", "platform"],
    "systems": ["frameworks", "architectures", "platforms"],
    "framework": ["architecture", "scheme", "model"],
    "performance": ["effectiveness", "accuracy"],
    "accuracy": ["precision", "correctness"],
    "limitation": ["constraint", "shortcoming", "drawback"],
    "limitations": ["constraints", "shortcomings", "drawbacks"],
    "challenge": ["difficulty", "obstacle"],
    "challenges": ["difficulties", "obstacles"],
    "concern": ["issue", "consideration"],
    "concerns": ["issues", "considerations"],
    "issue": ["problem", "concern", "difficulty"],
    "issues": ["problems", "concerns", "difficulties"],
    "problem": ["issue", "difficulty", "limitation"],
    "advantage": ["benefit", "strength"],
    "advantages": ["benefits", "strengths"],
    "benefit": ["advantage", "gain"],
    "ability": ["capability", "capacity"],
    "capability": ["ability", "capacity"],
    "environment": ["setting", "context"],
    "scenario": ["setting", "case", "context"],
    "scenarios": ["settings", "cases", "contexts"],
    "context": ["setting", "domain"],
}

# --------------------------------------------------------------------------- #
# Adjectives / adverbs.
# --------------------------------------------------------------------------- #
_ADJ: Dict[str, List[str]] = {
    "important": ["significant", "notable", "considerable"],
    "significant": ["substantial", "notable", "considerable"],
    "key": ["central", "principal", "primary"],
    "crucial": ["essential", "critical", "vital"],
    "essential": ["fundamental", "critical", "necessary"],
    "effective": ["robust", "reliable", "successful"],
    "efficient": ["economical", "streamlined"],
    "accurate": ["precise", "reliable", "exact"],
    "reliable": ["dependable", "consistent", "robust"],
    "robust": ["resilient", "stable", "reliable"],
    "complex": ["intricate", "complicated", "elaborate"],
    "difficult": ["challenging", "demanding", "non-trivial"],
    "simple": ["straightforward", "elementary"],
    "novel": ["new", "original"],
    "recent": ["current", "contemporary"],
    "various": ["several", "diverse", "differing"],
    "numerous": ["many", "multiple", "several"],
    "large": ["substantial", "considerable", "extensive"],
    "small": ["limited", "modest", "minor"],
    "fast": ["rapid", "swift", "efficient"],
    "slow": ["gradual", "protracted"],
    "limited": ["constrained", "restricted", "narrow"],
    "widely": ["extensively", "broadly", "commonly"],
    "often": ["frequently", "commonly", "typically"],
    "clearly": ["evidently", "demonstrably"],
}

# --------------------------------------------------------------------------- #
# Multi-word academic phrasings.
# --------------------------------------------------------------------------- #
_PHRASES: Dict[str, List[str]] = {
    "a lot of": ["a substantial amount of", "considerable", "extensive"],
    "lots of": ["numerous", "considerable"],
    "make use of": ["employ", "utilize", "draw on"],
    "based on": ["grounded in", "derived from", "informed by"],
    "show that": ["demonstrate that", "indicate that", "reveal that"],
    "showed that": ["demonstrated that", "indicated that", "revealed that"],
    "found that": ["determined that", "observed that", "reported that"],
    "a number of": ["several", "various", "multiple"],
    "play a role": ["contribute", "be a factor"],
    "deal with": ["address", "handle", "treat"],
    "look at": ["examine", "consider", "investigate"],
    "point out": ["note", "observe", "indicate"],
    "carried out": ["conducted", "performed", "undertaken"],
    "real-time": ["real-time", "online", "live"],
}

ACADEMIC_LEXICON: Dict[str, List[str]] = {}
for _grp in (_VERBS, _NOUNS, _ADJ, _PHRASES):
    ACADEMIC_LEXICON.update(_grp)


def academic_options(word: str) -> List[str]:
    """Return curated academic-register alternatives for ``word`` (lower-cased),
    or an empty list when the word should be left untouched."""
    return list(ACADEMIC_LEXICON.get((word or "").strip().lower(), []))
