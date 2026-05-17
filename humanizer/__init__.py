"""AI Humanizer — rewrite machine-sounding text into a chosen human tone.

Signals it tunes for: perplexity, burstiness and lexical diversity.
"""

from .advanced_metrics import (
    bigram_perplexity,
    detailed_report,
    humanity_score,
    mtld,
    sentence_burstiness_profile,
)
from .core import Humanizer, HumanizeResult
from .glossary import load_glossary, normalize_glossary
from .metrics import TextMetrics, analyze
from .paraphrase_patterns import pattern_inventory
from .pipeline import DEFAULT_PIPELINE, TONE_PIPELINES, Pipeline, pipeline_for_tone
from .suggest import suggest_synonyms
from .tones import Tone, get_tone, list_tones

__version__ = "2.2.0"

__all__ = [
    "Humanizer",
    "HumanizeResult",
    "TextMetrics",
    "analyze",
    "Pipeline",
    "DEFAULT_PIPELINE",
    "TONE_PIPELINES",
    "pipeline_for_tone",
    "pattern_inventory",
    "suggest_synonyms",
    "load_glossary",
    "normalize_glossary",
    "Tone",
    "get_tone",
    "list_tones",
    "bigram_perplexity",
    "mtld",
    "sentence_burstiness_profile",
    "humanity_score",
    "detailed_report",
    "__version__",
]
