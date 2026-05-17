"""Tone definitions and their (large) dictionaries.

Each tone owns:

* ``synonyms``       -- a big word -> alternatives map (shared base + tone words)
* ``starters``       -- sentence-opening discourse markers for this tone
* ``interjections``  -- short asides injected mid-text for human texture
* ``connectors``     -- words used to merge short sentences
* ``fragments``      -- punchy stand-alone lines added to raise burstiness
* ``ai_tells``       -- typical "AI giveaway" phrases -> tone rewrites
* ``contraction_mode`` -- 'contract', 'expand' or 'keep'

The base synonym bank is intentionally broad; every tone inherits it and then
adds / overrides entries with its own flavoured vocabulary, so the effective
per-tone dictionary is several hundred words deep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# --------------------------------------------------------------------------- #
# Shared base vocabulary (inherited by every tone).
# --------------------------------------------------------------------------- #
BASE_SYNONYMS: Dict[str, List[str]] = {
    "good": ["solid", "strong", "decent", "fine", "worthwhile", "valuable", "sound"],
    "great": ["excellent", "outstanding", "remarkable", "superb", "first-rate", "stellar"],
    "bad": ["poor", "weak", "flawed", "subpar", "lacking", "deficient", "rough"],
    "big": ["large", "sizable", "substantial", "considerable", "hefty", "major"],
    "small": ["modest", "minor", "slight", "compact", "limited", "tiny"],
    "important": ["key", "crucial", "vital", "essential", "central", "pivotal", "significant"],
    "very": ["highly", "remarkably", "notably", "particularly", "especially", "decidedly"],
    "really": ["genuinely", "truly", "honestly", "seriously", "actually"],
    "many": ["numerous", "plenty of", "a host of", "countless", "a good number of"],
    "a lot": ["a great deal", "plenty", "loads", "no shortage", "a fair amount"],
    "use": ["employ", "apply", "leverage", "rely on", "draw on", "make use of"],
    "make": ["create", "build", "produce", "form", "shape", "put together"],
    "show": ["reveal", "demonstrate", "illustrate", "highlight", "point to", "indicate"],
    "help": ["assist", "support", "aid", "enable", "back", "bolster"],
    "get": ["obtain", "gain", "secure", "land", "pick up", "acquire"],
    "think": ["believe", "reckon", "figure", "suspect", "hold", "feel"],
    "say": ["note", "point out", "remark", "mention", "observe", "state"],
    "said": ["noted", "pointed out", "remarked", "mentioned", "observed", "stated"],
    "look": ["seem", "appear", "come across", "feel"],
    "start": ["begin", "kick off", "launch", "open", "set off", "initiate"],
    "end": ["finish", "wrap up", "close out", "conclude", "round off"],
    "change": ["shift", "alter", "adjust", "modify", "reshape", "transform"],
    "improve": ["sharpen", "strengthen", "refine", "upgrade", "boost", "enhance"],
    "problem": ["issue", "snag", "hurdle", "challenge", "obstacle", "sticking point"],
    "idea": ["notion", "concept", "thought", "angle", "take", "approach"],
    "way": ["method", "approach", "route", "path", "means", "tactic"],
    "thing": ["aspect", "element", "factor", "piece", "detail", "point"],
    "people": ["folks", "individuals", "readers", "users", "audiences"],
    "fast": ["quick", "rapid", "swift", "speedy", "brisk"],
    "slow": ["sluggish", "gradual", "unhurried", "plodding"],
    "hard": ["tough", "tricky", "demanding", "challenging", "thorny"],
    "easy": ["simple", "straightforward", "effortless", "painless", "manageable"],
    "interesting": ["intriguing", "compelling", "engaging", "noteworthy", "fascinating"],
    "show that": ["suggest that", "indicate that", "point to the fact that"],
    "in order to": ["to", "so as to", "with the aim of"],
    "a number of": ["several", "various", "a range of", "a handful of"],
    "however": ["that said", "even so", "still", "then again", "yet"],
    "therefore": ["so", "as a result", "which means", "for that reason"],
    "additionally": ["on top of that", "beyond that", "what's more", "and"],
    "utilize": ["use", "apply", "draw on", "lean on"],
    "very important": ["critical", "make-or-break", "non-negotiable"],
}

# --------------------------------------------------------------------------- #
# Tone-specific overrides / extra vocabulary.
# --------------------------------------------------------------------------- #
TONE_SYNONYMS: Dict[str, Dict[str, List[str]]] = {
    "casual": {
        "good": ["pretty good", "nice", "not bad", "solid"],
        "great": ["awesome", "amazing", "fantastic", "killer", "spot on"],
        "bad": ["rough", "not great", "kinda off", "messy"],
        "very": ["super", "really", "seriously", "way"],
        "difficult": ["a pain", "tricky", "a headache"],
        "understand": ["get", "wrap your head around", "figure out"],
        "begin": ["kick things off", "jump in", "dive in"],
        "many": ["tons of", "loads of", "a bunch of"],
        "okay": ["alright", "fine", "cool"],
        "good idea": ["smart move", "solid call"],
    },
    "professional": {
        "good": ["effective", "robust", "reliable", "well-suited"],
        "great": ["exceptional", "high-impact", "best-in-class"],
        "use": ["leverage", "deploy", "operationalize", "apply"],
        "help": ["support", "facilitate", "enable", "drive"],
        "problem": ["challenge", "risk", "constraint", "bottleneck"],
        "make": ["develop", "deliver", "execute", "implement"],
        "important": ["strategic", "high-priority", "mission-critical"],
        "show": ["demonstrate", "evidence", "substantiate"],
        "improve": ["optimize", "streamline", "elevate"],
    },
    "academic": {
        "show": ["demonstrate", "establish", "evidence", "substantiate"],
        "say": ["argue", "contend", "posit", "assert", "maintain"],
        "think": ["hypothesize", "postulate", "contend", "hold"],
        "idea": ["hypothesis", "premise", "construct", "proposition"],
        "important": ["significant", "salient", "consequential", "germane"],
        "use": ["employ", "utilize", "operationalize"],
        "big": ["substantial", "considerable", "marked", "pronounced"],
        "problem": ["limitation", "confound", "open question"],
        "because": ["insofar as", "given that", "owing to the fact that"],
        "so": ["consequently", "accordingly", "thus"],
        "also": ["furthermore", "moreover", "in addition"],
    },
    "friendly": {
        "good": ["lovely", "wonderful", "great", "really nice"],
        "great": ["fantastic", "brilliant", "wonderful", "amazing"],
        "help": ["lend a hand", "support you", "be there for"],
        "problem": ["little hiccup", "bump in the road", "snag"],
        "important": ["worth knowing", "good to keep in mind"],
        "think": ["feel", "have a hunch", "reckon"],
        "people": ["folks", "everyone", "you all"],
        "easy": ["a breeze", "no trouble at all", "simple"],
    },
    "persuasive": {
        "good": ["unbeatable", "game-changing", "compelling", "powerful"],
        "great": ["extraordinary", "undeniable", "transformative"],
        "important": ["critical", "urgent", "decisive", "make-or-break"],
        "show": ["prove", "make the case", "leave no doubt"],
        "help": ["unlock", "supercharge", "accelerate"],
        "use": ["harness", "capitalize on", "tap into"],
        "should": ["must", "owe it to yourself to", "can't afford not to"],
        "many": ["a growing number of", "more and more"],
        "now": ["right now", "today, not tomorrow"],
    },
    "confident": {
        "think": ["know", "am certain", "have no doubt"],
        "maybe": ["clearly", "without question", "plainly"],
        "could": ["will", "can", "does"],
        "good": ["strong", "decisive", "proven"],
        "important": ["essential", "non-negotiable", "the deciding factor"],
        "problem": ["obstacle we solve", "challenge we handle"],
        "i think": ["i'm confident", "make no mistake,"],
    },
    "empathetic": {
        "problem": ["struggle", "difficult moment", "hard time"],
        "hard": ["overwhelming", "draining", "a lot to carry"],
        "important": ["meaningful", "deeply valid", "worth honouring"],
        "help": ["be here for", "walk alongside", "support gently"],
        "think": ["sense", "imagine", "understand"],
        "good": ["healing", "kind", "reassuring"],
        "feel": ["are allowed to feel", "may be feeling"],
    },
    "storytelling": {
        "said": ["whispered", "admitted", "confessed", "let slip", "muttered"],
        "look": ["glance", "stare", "catch sight", "peer"],
        "walk": ["wander", "drift", "stride", "slip"],
        "big": ["towering", "vast", "looming", "endless"],
        "small": ["tiny", "fragile", "barely-there"],
        "fast": ["in a heartbeat", "before anyone could blink"],
        "suddenly": ["all at once", "out of nowhere", "in an instant"],
        "good": ["golden", "bright", "warm"],
        "bad": ["bitter", "cold", "haunting"],
    },
    "witty": {
        "good": ["not too shabby", "borderline genius", "weirdly excellent"],
        "bad": ["a glorious mess", "spectacularly off", "a plot twist no one wanted"],
        "very": ["impressively", "absurdly", "almost suspiciously"],
        "important": ["the whole ballgame", "kind of a big deal"],
        "problem": ["plot twist", "minor catastrophe", "the universe being dramatic"],
        "interesting": ["chef's-kiss interesting", "oddly fascinating"],
        "think": ["have a sneaking suspicion", "would bet money that"],
    },
}

# Sentence starters / discourse markers per tone.
TONE_STARTERS: Dict[str, List[str]] = {
    "casual": ["Honestly,", "Look,", "So here's the thing —", "Okay, so", "Truth is,", "Not gonna lie,", "Here's the deal:"],
    "professional": ["Notably,", "In practice,", "From a delivery standpoint,", "Strategically,", "To be clear,", "Importantly,"],
    "academic": ["Notably,", "It is worth noting that", "Crucially,", "On closer examination,", "By contrast,", "In this regard,"],
    "friendly": ["Honestly,", "Just so you know,", "Here's a little tip:", "Quick heads-up —", "By the way,", "Good news:"],
    "persuasive": ["Here's why this matters:", "Make no mistake —", "Think about it:", "The reality is,", "Consider this:", "Bottom line —"],
    "confident": ["Make no mistake,", "Here's the truth:", "Let's be clear:", "Without question,", "The fact is,"],
    "empathetic": ["First, take a breath.", "It's completely understandable that", "Gently —", "If it helps,", "Please know that"],
    "storytelling": ["And then,", "What happened next was simple:", "Here's where it turns:", "Picture this —", "Slowly,"],
    "witty": ["Plot twist:", "Spoiler alert —", "Against all odds,", "Funnily enough,", "In a stunning turn of events,"],
}

TONE_INTERJECTIONS: Dict[str, List[str]] = {
    "casual": ["honestly", "I mean", "you know", "kind of", "for real", "no joke"],
    "professional": ["in effect", "broadly speaking", "to be precise", "on balance"],
    "academic": ["arguably", "in essence", "more precisely", "to a degree"],
    "friendly": ["honestly", "I promise", "trust me", "no worries"],
    "persuasive": ["frankly", "make no mistake", "let's be honest", "and that's the point"],
    "confident": ["plainly", "without a doubt", "full stop", "period"],
    "empathetic": ["gently", "and that's okay", "truly", "if that resonates"],
    "storytelling": ["somehow", "of course", "as it turned out", "for a moment"],
    "witty": ["allegedly", "shockingly", "naturally", "as one does"],
}

TONE_CONNECTORS: Dict[str, List[str]] = {
    "casual": ["and", "but", "so", "plus"],
    "professional": ["and", "while", "whereas", "in turn"],
    "academic": ["and", "whereas", "while", "in that"],
    "friendly": ["and", "but", "so", "plus"],
    "persuasive": ["and", "but", "which is exactly why"],
    "confident": ["and", "because", "which is why"],
    "empathetic": ["and", "while", "even as"],
    "storytelling": ["and", "until", "but then", "as"],
    "witty": ["and", "but", "which, naturally,"],
}

TONE_FRAGMENTS: Dict[str, List[str]] = {
    "casual": ["Simple as that.", "No big deal.", "That's the gist.", "Worth it."],
    "professional": ["The impact is measurable.", "That distinction matters.", "Execution is everything."],
    "academic": ["The implication is non-trivial.", "This warrants careful reading.", "The distinction is consequential."],
    "friendly": ["You've got this.", "Pretty neat, right?", "Nothing to stress about."],
    "persuasive": ["The choice is obvious.", "Waiting costs you.", "This is the moment."],
    "confident": ["No hedging here.", "That's the bottom line.", "End of story."],
    "empathetic": ["You're not alone in this.", "That's more than okay.", "Take the time you need."],
    "storytelling": ["Everything changed.", "Nothing was the same after.", "And the room went quiet."],
    "witty": ["Bold move.", "Nobody saw that coming.", "Science, probably."],
}

# Common "AI giveaway" phrases -> tone-appropriate rewrites ([] == delete).
_GLOBAL_AI_TELLS: Dict[str, List[str]] = {
    "it is important to note that": ["worth noting:", "keep in mind that", ""],
    "it is worth noting that": ["notably,", "keep in mind that", ""],
    "it should be noted that": ["note that", ""],
    "in conclusion": ["all in all", "to wrap up", "in the end"],
    "in summary": ["to sum up", "long story short", "the short version:"],
    "overall,": ["on the whole,", "all told,", "broadly,"],
    "in today's world": ["these days", "right now", "lately"],
    "in the modern era": ["nowadays", "today"],
    "delve into": ["dig into", "get into", "look at"],
    "delving into": ["digging into", "getting into"],
    "navigate the complexities of": ["work through", "handle", "deal with"],
    "a testament to": ["a sign of", "proof of"],
    "plays a crucial role": ["matters a lot", "is central"],
    "plays a vital role": ["really matters", "is key"],
    "when it comes to": ["with", "for", "on"],
    "the realm of": ["the world of", ""],
    "tapestry of": ["mix of", "blend of"],
    "in the realm of": ["in", "within"],
    "first and foremost": ["first", "above all"],
    "last but not least": ["finally", "and lastly"],
    "needless to say": ["clearly", "obviously", ""],
    "at the end of the day": ["ultimately", "in the end"],
    "it goes without saying that": ["clearly,", "obviously,", ""],
}

CONTRACTION_MODE: Dict[str, str] = {
    "casual": "contract",
    "friendly": "contract",
    "witty": "contract",
    "storytelling": "contract",
    "persuasive": "contract",
    "confident": "keep",
    "professional": "keep",
    "empathetic": "keep",
    "academic": "expand",
}

TONE_DESCRIPTIONS: Dict[str, str] = {
    "casual": "Relaxed, conversational, contractions and asides.",
    "professional": "Polished, outcome-focused business voice.",
    "academic": "Formal, hedged, citation-style argumentation.",
    "friendly": "Warm, encouraging, approachable.",
    "persuasive": "High-conviction, action-driving marketing voice.",
    "confident": "Direct, assertive, no hedging.",
    "empathetic": "Gentle, validating, supportive.",
    "storytelling": "Narrative, sensory, scene-driven.",
    "witty": "Playful, dry, lightly comedic.",
}


@dataclass
class Tone:
    name: str
    description: str
    synonyms: Dict[str, List[str]] = field(default_factory=dict)
    starters: List[str] = field(default_factory=list)
    interjections: List[str] = field(default_factory=list)
    connectors: List[str] = field(default_factory=list)
    fragments: List[str] = field(default_factory=list)
    ai_tells: Dict[str, List[str]] = field(default_factory=dict)
    contraction_mode: str = "keep"

    @property
    def vocabulary_size(self) -> int:
        return sum(len(v) for v in self.synonyms.values())


def _build_tone(name: str) -> Tone:
    syn: Dict[str, List[str]] = {k: list(v) for k, v in BASE_SYNONYMS.items()}
    for word, alts in TONE_SYNONYMS.get(name, {}).items():
        # Merge tone words in front (preferred) without losing base options.
        merged = list(dict.fromkeys(alts + syn.get(word, [])))
        syn[word] = merged
    return Tone(
        name=name,
        description=TONE_DESCRIPTIONS[name],
        synonyms=syn,
        starters=list(TONE_STARTERS[name]),
        interjections=list(TONE_INTERJECTIONS[name]),
        connectors=list(TONE_CONNECTORS[name]),
        fragments=list(TONE_FRAGMENTS[name]),
        ai_tells=dict(_GLOBAL_AI_TELLS),
        contraction_mode=CONTRACTION_MODE[name],
    )


TONES: Dict[str, Tone] = {name: _build_tone(name) for name in TONE_DESCRIPTIONS}


def get_tone(name: str) -> Tone:
    key = (name or "").strip().lower()
    if key not in TONES:
        raise KeyError(
            f"Unknown tone {name!r}. Available: {', '.join(sorted(TONES))}"
        )
    return TONES[key]


def list_tones() -> List[str]:
    return sorted(TONES)
