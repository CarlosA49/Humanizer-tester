"""Command-line interface.

Examples
--------
    python -m humanizer --list-tones
    python -m humanizer --tone casual "It is important to note that ..."
    python -m humanizer --tone academic --strength 0.7 --file in.txt
    echo "some text" | python -m humanizer --tone friendly --metrics
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .core import Humanizer
from .tones import get_tone, list_tones


def _read_input(args: argparse.Namespace) -> str:
    if args.text:
        return " ".join(args.text)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            return fh.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="humanizer",
        description="Rewrite machine-sounding text into a chosen human tone "
        "(tunes perplexity, burstiness and lexical diversity).",
    )
    p.add_argument("text", nargs="*", help="Text to humanize (or use --file / stdin).")
    p.add_argument("-t", "--tone", default="casual", help="Tone to apply.")
    p.add_argument(
        "-s", "--strength", type=float, default=0.5,
        help="0.0–1.0: how aggressively rules fire (default 0.5).",
    )
    p.add_argument("--seed", type=int, default=None, help="Seed for reproducible output.")
    p.add_argument("-f", "--file", help="Read input text from a file.")
    p.add_argument("--metrics", action="store_true", help="Print before/after metrics.")
    p.add_argument("--changes", action="store_true", help="Print the change log.")
    p.add_argument("--list-tones", action="store_true", help="List available tones and exit.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_tones:
        for name in list_tones():
            tone = get_tone(name)
            print(f"{name:<14} {tone.description}  (~{tone.vocabulary_size} synonyms)")
        return 0

    text = _read_input(args)
    if not text.strip():
        print("No input text. Provide text, --file, or pipe via stdin.", file=sys.stderr)
        return 2

    try:
        h = Humanizer(tone=args.tone, strength=args.strength, seed=args.seed)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    result = h.humanize(text)
    print(result.text)

    if args.metrics:
        print("\n--- metrics ---", file=sys.stderr)
        print(result.summary(), file=sys.stderr)
    if args.changes:
        print("\n--- changes ---", file=sys.stderr)
        for c in result.changes:
            print(f"  - {c}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
