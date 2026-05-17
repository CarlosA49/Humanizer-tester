"""AI Humanizer — rewrite machine-sounding text into a chosen human tone.

Signals it tunes for: perplexity, burstiness and lexical diversity.
"""

from .core import Humanizer, HumanizeResult
from .metrics import TextMetrics, analyze
from .pipeline import DEFAULT_PIPELINE, Pipeline
from .tones import Tone, get_tone, list_tones

__version__ = "1.0.0"

__all__ = [
    "Humanizer",
    "HumanizeResult",
    "TextMetrics",
    "analyze",
    "Pipeline",
    "DEFAULT_PIPELINE",
    "Tone",
    "get_tone",
    "list_tones",
    "__version__",
]
