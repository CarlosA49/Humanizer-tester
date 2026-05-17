"""Per-project glossary: synonym overrides, acronym glosses, protected terms.

A glossary is a small JSON document a writer keeps alongside their paper::

    {
      "synonyms": { "system": ["framework", "architecture"],
                     "item":   ["object", "article"] },
      "acronyms": { "UWB": "ultra-wideband (UWB)",
                    "NLOS": "non-line-of-sight (NLOS)" },
      "protect":  ["YOLOv8", "ArUco", "Hailo-8L", "Raspberry Pi 5"]
    }

* ``synonyms`` -- project-preferred academic substitutions (merged on top of
  the built-in academic bank; project options are preferred).
* ``acronyms`` -- extra first-use glosses (merged with the defaults).
* ``protect``  -- exact terms (case-insensitive, may be multi-word) that must
  never be substituted or expanded -- product / model / library names.

All parsing is tolerant: unknown keys are ignored and malformed entries are
dropped rather than raising, so a slightly-off glossary still works.
"""

from __future__ import annotations

import json
from typing import Dict, List


def normalize_glossary(obj) -> Dict[str, object]:
    """Coerce a raw glossary object into ``{synonyms, acronyms, protect}``.

    ``synonyms``: ``{lower-case head -> [str, ...]}``
    ``acronyms``: ``{token -> gloss str}``
    ``protect``:  ``frozenset`` of lower-cased exact terms
    """
    syn: Dict[str, List[str]] = {}
    acro: Dict[str, str] = {}
    protect = set()

    if isinstance(obj, dict):
        raw_syn = obj.get("synonyms")
        if isinstance(raw_syn, dict):
            for k, v in raw_syn.items():
                key = str(k).strip().lower()
                if not key:
                    continue
                if isinstance(v, str):
                    v = [v]
                if isinstance(v, (list, tuple)):
                    opts = [str(x).strip() for x in v if str(x).strip()]
                    if opts:
                        syn[key] = opts

        raw_acro = obj.get("acronyms")
        if isinstance(raw_acro, dict):
            for k, v in raw_acro.items():
                kk, vv = str(k).strip(), str(v).strip()
                if kk and vv:
                    acro[kk] = vv

        raw_protect = obj.get("protect")
        if isinstance(raw_protect, (list, tuple)):
            for t in raw_protect:
                tt = str(t).strip().lower()
                if tt:
                    protect.add(tt)

    return {"synonyms": syn, "acronyms": acro, "protect": frozenset(protect)}


def load_glossary(path: str) -> Dict[str, object]:
    """Read and normalize a glossary JSON file.

    Raises ``ValueError`` with a clear message on unreadable / invalid JSON.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise ValueError(f"Glossary file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Glossary is not valid JSON ({path}): {exc}") from exc
    return normalize_glossary(data)
