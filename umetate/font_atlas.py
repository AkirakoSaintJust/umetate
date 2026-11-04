# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Build the design mockup's bitmap font atlas from `firmware/gen/felucca_font.h`.

The firmware font is a 4-bit-per-pixel bitmap: `height`, `pad`, `first`, `last`,
`adv`, `bw`, `off`, and `data`. The mockup needs the same bytes to draw the real
glyphs instead of a system font. The atlas is a small JSON file with the two
faces and base64 data. `check` fails when the committed atlas is stale.

Run: `python3 -m umetate.font_atlas write` or `check`.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "firmware" / "gen" / "felucca_font.h"
ATLAS = ROOT / "design" / "firmware-font.json"


def _numbers(text: str, name: str) -> list[int]:
    match = re.search(
        rf"\b{re.escape(name)}\[[^\]]*\]\s*=\s*\{{(.*?)\}}", text, re.DOTALL
    )
    if match is None:
        raise ValueError(f"{name} not found in the font header")
    values = re.findall(r"0x[0-9A-Fa-f]+|\d+", match.group(1))
    return [int(value, 0) for value in values]


def _face(text: str, prefix: str) -> dict[str, object]:
    struct = re.search(
        rf"felucca_font_t\s+{re.escape(prefix)}\s*=\s*"
        r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)",
        text,
    )
    if struct is None:
        raise ValueError(f"{prefix} struct not found")
    height, pad, first, last = (int(struct.group(i)) for i in range(1, 5))
    data = _numbers(text, f"{prefix}_DATA")
    return {
        "height": height,
        "pad": pad,
        "first": first,
        "last": last,
        "adv": _numbers(text, f"{prefix}_ADV"),
        "bw": _numbers(text, f"{prefix}_BW"),
        "off": _numbers(text, f"{prefix}_OFF"),
        "data": base64.b64encode(bytes(data)).decode("ascii"),
    }


def build() -> dict[str, object]:
    text = HEADER.read_text(encoding="utf-8")
    return {
        "source": "firmware/gen/felucca_font.h",
        "faces": {"S": _face(text, "FONT_S"), "L": _face(text, "FONT_L")},
    }


def render() -> str:
    return json.dumps(build(), indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate font-atlas", description=__doc__)
    parser.add_argument("action", choices=("write", "check"))
    args = parser.parse_args(argv)
    expected = render()
    if args.action == "write":
        ATLAS.write_text(expected, encoding="utf-8")
        print(f"font-atlas: wrote {ATLAS}")
        return 0
    actual = ATLAS.read_text(encoding="utf-8") if ATLAS.is_file() else ""
    if actual != expected:
        print(
            f"font-atlas: {ATLAS} is stale: run `python3 -m umetate.font_atlas write`",
            file=sys.stderr,
        )
        return 1
    print(f"font-atlas: {ATLAS} matches {HEADER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
