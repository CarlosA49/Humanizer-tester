"""Assemble the static GitHub Pages site into ./_site.

Copies the static UI from ``docs/`` and the live ``humanizer/`` package
source (so the deployed app always uses the real code, never a fork of it),
then writes a manifest the browser uses to load the package into Pyodide.

Run locally:  python web/build_site.py && (cd _site && python -m http.server)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)

    # Static UI assets.
    shutil.copytree(ROOT / "docs", SITE, dirs_exist_ok=True)

    # Live package source.
    pkg_src = ROOT / "humanizer"
    pkg_dst = SITE / "humanizer"
    pkg_dst.mkdir(parents=True, exist_ok=True)
    py_files = sorted(p.name for p in pkg_src.glob("*.py"))
    for name in py_files:
        shutil.copyfile(pkg_src / name, pkg_dst / name)

    (pkg_dst / "__files__.json").write_text(
        json.dumps(py_files, indent=2), encoding="utf-8"
    )
    (SITE / ".nojekyll").touch()

    print(f"Built {SITE} with {len(py_files)} package files: {py_files}")


if __name__ == "__main__":
    main()
