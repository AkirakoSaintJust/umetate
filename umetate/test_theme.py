# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host tests for `umetate theme` (docs/roadmap.md §6.10): the WCAG 2.1 contrast
math, the palette generator, the checker, and the shipped gfx.c palettes (a
regression lock so a palette edit can't silently drop below 1.4.3)."""

from __future__ import annotations

import json
from pathlib import Path

from .theme import (
    Theme,
    check,
    contrast,
    emit_c,
    generate,
    hex_to_rgb,
    luminance,
    read_theme,
    rgb_to_hex,
    rgb_to_rgb565,
)

ROOT = Path(__file__).resolve().parents[1]

_BLACK = (0, 0, 0)


def main() -> int:
    failures: int = 0

    # 1. the WCAG math (known reference values).
    if abs(contrast((0, 0, 0), (255, 255, 255)) - 21.0) > 0.01:
        print("FAIL: black/white contrast is not 21:1")
        failures += 1
    else:
        print("ok: black/white contrast is 21:1")
    if abs(luminance((255, 255, 255)) - 1.0) > 0.001:
        print("FAIL: white luminance is not 1.0")
        failures += 1
    else:
        print("ok: white luminance is 1.0")

    # 2. the generator produces a compliant dark palette (every role >= its floor).
    theme = generate(150.0)
    bad = [line for line in check(theme) if "FAIL" in line]
    if bad:
        print(f"FAIL: generated palette has failing pairs: {bad}")
        failures += 1
    else:
        print("ok: generate produces a WCAG-compliant dark palette")

    # 3. the checker flags a low-contrast palette.
    low: Theme = {"name": "low", "colors": {"background": "#000000", "text": "#333333"}}
    if not any("FAIL" in line for line in check(low)):
        print("FAIL: check did not flag a low-contrast text")
        failures += 1
    else:
        print("ok: check flags a low-contrast text")

    # 4. the shipped palettes: labels (step 2) and values (step 4) >= 4.5:1,
    #    secondary (step 3) >= 3:1 against black (the 1.4.3/1.4.11 floors).
    raw = json.loads((ROOT / "firmware" / "theme.json").read_text(encoding="utf-8"))
    colors = raw["colors"]
    palettes = {
        name: [hex_to_rgb(step) for step in steps]
        for name, steps in raw.get("palettes", {}).items()
    }
    for name, steps in palettes.items():
        label = contrast(steps[2], _BLACK)
        amb = contrast(steps[3], _BLACK)
        hi = contrast(steps[4], _BLACK)
        if label < 4.5 or hi < 4.5 or amb < 3.0:
            print(f"FAIL: {name} palette contrast ({label:.2f}/{amb:.2f}/{hi:.2f})")
            failures += 1
        else:
            print(f"ok: {name} palette meets contrast ({label:.2f}/{amb:.2f}/{hi:.2f})")

    # 4b. the popup roles: the container and text come from theme.json. The text
    #     must read (4.5:1) and both accents stay visible (3:1) in every palette.
    popup_bg = hex_to_rgb(colors["popup_background"])
    popup_text = hex_to_rgb(colors["popup_text"])
    text_contrast = contrast(popup_text, popup_bg)
    if text_contrast < 4.5:
        print(f"FAIL: popup text contrast {text_contrast:.2f}")
        failures += 1
    else:
        print(f"ok: popup text contrast {text_contrast:.2f}")
    for name, steps in palettes.items():
        sel = contrast(steps[3], popup_bg)
        hi = contrast(steps[4], popup_bg)
        if sel < 3.0 or hi < 3.0:
            print(f"FAIL: {name} popup roles too dim ({sel:.2f}/{hi:.2f})")
            failures += 1
        else:
            print(f"ok: {name} popup roles legible ({sel:.2f}/{hi:.2f})")

    # 5. the round-trip: hex <-> rgb.
    if rgb_to_hex(hex_to_rgb("#00ff80")) != "#00ff80":
        print("FAIL: hex/rgb round-trip")
        failures += 1

    # 6. the C header emit + the checked-in firmware/gen/theme.h is in sync.
    if rgb_to_rgb565((0, 255, 255)) != 0x07FF:
        print("FAIL: cyan RGB565 is not 0x07FF")
        failures += 1
    else:
        print("ok: cyan -> RGB565 0x07FF")
    theme = read_theme(str(ROOT / "firmware" / "theme.json"))
    emitted = emit_c(theme)
    checked = (ROOT / "firmware" / "gen" / "theme.h").read_text(encoding="utf-8")
    if emitted != checked:
        print(
            "FAIL: firmware/gen/theme.h is stale "
            "(run `umetate theme write firmware/theme.json firmware/gen/theme.h`)"
        )
        failures += 1
    else:
        print("ok: firmware/gen/theme.h is in sync with theme.json")

    print("theme tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
