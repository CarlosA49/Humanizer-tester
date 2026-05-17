"""Generate the app icons (no third-party deps).

A flat, modern mark for the AI Humanizer: pill-shaped "burstiness" wave
bars (tall/short/tall — the signal the tool tunes) on the app's dark
charcoal background, in the brand blue with one white accent bar.

Rendered per target size (geometry is proportional, so every file is
crisp at its own resolution — no resampling). Re-run after editing:

    python web/make_icons.py
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ICONS = Path(__file__).resolve().parent.parent / "docs" / "icons"

BG = (14, 17, 23)        # #0E1117  app background
BLUE = (59, 130, 246)    # #3B82F6  accent
WHITE = (230, 237, 243)  # #E6EDF3  highlight

# Five bars: relative height (fraction of motif height) and colour.
BARS = [
    (0.42, BLUE),
    (0.72, BLUE),
    (0.54, WHITE),
    (0.92, BLUE),
    (0.48, BLUE),
]


def _png(path: Path, size: int, pixels: bytearray) -> None:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    raw = bytearray()
    stride = size * 3
    for y in range(size):
        raw.append(0)  # filter type 0
        raw.extend(pixels[y * stride:(y + 1) * stride])
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def render(size: int) -> bytearray:
    buf = bytearray(BG * (size * size))

    def put(x: int, y: int, c) -> None:
        if 0 <= x < size and 0 <= y < size:
            i = (y * size + x) * 3
            buf[i:i + 3] = bytes(c)

    n = len(BARS)
    bar_w = size * 0.108
    gap = size * 0.052
    total = n * bar_w + (n - 1) * gap
    x0 = (size - total) / 2.0
    baseline = size * 0.770          # bars sit on this line
    max_h = size * 0.560             # tallest possible bar
    r = bar_w / 2.0                  # pill cap radius

    for bi, (hf, color) in enumerate(BARS):
        h = max(max_h * hf, bar_w)   # never shorter than a circle
        left = x0 + bi * (bar_w + gap)
        right = left + bar_w
        top = baseline - h
        cx = (left + right) / 2.0
        cyt = top + r                # top cap centre
        cyb = baseline - r           # bottom cap centre
        xa, xb = int(left), int(right) + 1
        ya, yb = int(top), int(baseline) + 1
        for y in range(ya, yb):
            for x in range(xa, xb):
                px, py = x + 0.5, y + 0.5
                if left <= px <= right and cyt <= py <= cyb:
                    inside = True
                elif (px - cx) ** 2 + (py - cyt) ** 2 <= r * r and py < cyt:
                    inside = True
                elif (px - cx) ** 2 + (py - cyb) ** 2 <= r * r and py > cyb:
                    inside = True
                else:
                    inside = False
                if inside:
                    put(x, y, color)
    return buf


TARGETS = {
    "apple-touch-icon.png": 180,
    "icon-192.png": 192,
    "icon-512.png": 512,
    "icon-maskable-512.png": 512,
    "icon-1024.png": 1024,
}


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    for name, size in TARGETS.items():
        _png(ICONS / name, size, render(size))
        print(f"wrote {name} ({size}x{size})")


if __name__ == "__main__":
    main()
