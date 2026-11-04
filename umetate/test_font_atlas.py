# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host test: the mockup font atlas matches firmware/gen/felucca_font.h."""

from __future__ import annotations

from .font_atlas import ATLAS, render


def main() -> int:
    expected = render()
    actual = ATLAS.read_text(encoding="utf-8") if ATLAS.is_file() else ""
    if actual != expected:
        print(f"FAIL: {ATLAS} is stale: run `python3 -m umetate.font_atlas write`")
        return 1
    print(f"ok: {ATLAS} matches the firmware font")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
