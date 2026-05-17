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
from .metrics import TextMetrics, analyze
from .pipeline import DEFAULT_PIPELINE, TONE_PIPELINES, Pipeline, pipeline_for_tone
from .tones import Tone, get_tone, list_tones

__version__ = "2.0.0"

__all__ = [
    "Humanizer",
    "HumanizeResult",
    "TextMetrics",
    "analyze",
    "Pipeline",
    "DEFAULT_PIPELINE",
    "TONE_PIPELINES",
    "pipeline_for_tone",
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
