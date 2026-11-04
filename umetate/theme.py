# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate theme` — a WCAG 2.1 contrast checker + dark-palette generator.

The applicable WCAG subset for a fixed 240x240 RGB565 screen (no text resize, no
pointer/audio): 1.4.3 contrast (text >= 4.5:1 normal, 3:1 large/graphics),
1.4.11 non-text contrast (>= 3:1), 2.4.7/2.4.13 focus visibility (>= 3:1), and
1.4.1 not-colour-alone (a design rule, not a numeric check). The tool checks the
numeric ones: `text` >= 4.5:1 and every other foreground role >= 3:1 against
`background`.

`check` verifies a palette (a `{name, colors}` object) and prints a report; it
exits non-zero on any failed pair. `generate` builds a dark palette from an accent
hue, brightening the accent/status hues until they meet 3:1 against black, and
prints the palette as JSON + a report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NotRequired, TypedDict

# role -> the minimum contrast against `background` (WCAG 2.1 AA).
_ROLE_MIN = {
    "text": 4.5,
    "muted": 3.0,
    "accent": 3.0,
    "success": 3.0,
    "warning": 3.0,
    "error": 3.0,
}

_FOREGROUND = tuple(_ROLE_MIN)  # the roles checked against background


class Theme(TypedDict):
    """A palette: `{name, colors: {role: "#RRGGBB"}, palettes?: {name: [...]}}`."""

    name: str
    colors: dict[str, str]
    palettes: NotRequired[dict[str, list[str]]]


RGB = tuple[int, int, int]


def hex_to_rgb(h: str) -> RGB:
    """`#RRGGBB` -> (r, g, b) 0..255."""
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"bad colour {h!r}: want #RRGGBB")
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError as exc:
        raise ValueError(f"bad colour {h!r}: want #RRGGBB") from exc


def rgb_to_hex(c: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*c)


def rgb_to_rgb565(c: RGB) -> int:
    """RGB888 -> RGB565 (the screen's 5/6/5-bit format)."""
    r, g, b = c
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def emit_c(theme: Theme) -> str:
    """A C header of the colour roles and palettes as RGB565 `#define`s."""
    colors = theme["colors"]
    lines = [
        "/* GENERATED - do not edit. Source: firmware/theme.json "
        "(umetate theme write firmware/theme.json firmware/gen/theme.h). */",
        "#pragma once",
    ]
    for role, value in colors.items():
        rgb565 = rgb_to_rgb565(hex_to_rgb(value))
        macro = "THEME_" + role.upper()
        lines.append(f"#define {macro} 0x{rgb565:04X}u")
    palettes = theme.get("palettes", {})
    if palettes:
        lines.append("")
        lines.append(f"#define THEME_PALETTE_COUNT {len(palettes)}")
        lines.append("static const uint16_t THEME_PALETTES[THEME_PALETTE_COUNT][5] = {")
        for name, steps in palettes.items():
            if len(steps) != 5:
                raise ValueError(f"palette {name!r} needs 5 colours")
            values = ", ".join(
                f"0x{rgb_to_rgb565(hex_to_rgb(step)):04X}u" for step in steps
            )
            lines.append(f"    {{ {values} }}, /* {name} */")
        lines.append("};")
    return "\n".join(lines) + "\n"


def _linear(channel: int) -> float:
    """A single sRGB channel (0..255) -> linear light (0..1)."""
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(c: RGB) -> float:
    """Relative luminance (WCAG 2.1), 0..1."""
    r, g, b = c
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(a: RGB, b: RGB) -> float:
    """The WCAG contrast ratio of two colours (1..21, a vs b, order-insensitive)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def check(theme: Theme) -> list[str]:
    """The contrast report for `theme` (one line per checked pair)."""
    colors = theme["colors"]
    if "background" not in colors:
        return ["theme has no `background` colour"]
    bg = hex_to_rgb(colors["background"])
    report: list[str] = []
    for role in _FOREGROUND:
        if role not in colors:
            report.append(f"{role}: missing")
            continue
        ratio = contrast(hex_to_rgb(colors[role]), bg)
        lo = _ROLE_MIN[role]
        report.append(
            f"{role:<8} {ratio:5.2f}:1  "
            f"{'ok' if ratio >= lo else 'FAIL (need ' + str(lo) + ':1)'}"
        )
    return report


def _blend(c: RGB, toward: RGB, t: float) -> RGB:
    """Mix `c` toward `toward` by fraction `t` (0..1)."""
    return tuple(round(c[i] + (toward[i] - c[i]) * t) for i in range(3))  # type: ignore[return-value]


def _brighten(c: RGB, min_ratio: float) -> RGB:
    """Blend `c` toward white until its contrast vs black meets `min_ratio`."""
    black = (0, 0, 0)
    for t in (i / 32.0 for i in range(33)):
        cand = _blend(c, (255, 255, 255), t)
        if contrast(cand, black) >= min_ratio:
            return cand
    return (255, 255, 255)


def _hue_to_rgb(hue: float) -> RGB:
    """A full-saturation, full-value colour for `hue` (0..360) -> RGB."""
    hue %= 360.0
    i = int(hue // 60.0) % 6
    f = hue / 60.0 - int(hue // 60.0)
    q = 1.0 - f
    t = f
    c = [
        (255, round(255 * t), 0),
        (round(255 * q), 255, 0),
        (0, 255, round(255 * t)),
        (0, round(255 * q), 255),
        (round(255 * t), 0, 255),
        (255, 0, round(255 * q)),
    ][i]
    return c


def generate(hue: float) -> Theme:
    """A dark palette from an accent `hue`: black bg, white text, a muted grey, and
    the accent/status hues brightened to >= 3:1 against black."""
    colors = {
        "background": "#000000",
        "text": "#ffffff",
        "muted": "#9ca3af",  # a mid-grey, ~7:1 vs black
        "accent": rgb_to_hex(_brighten(_hue_to_rgb(hue), 3.0)),
        "success": rgb_to_hex(_brighten(_hue_to_rgb(130.0), 3.0)),
        "warning": rgb_to_hex(_brighten(_hue_to_rgb(40.0), 3.0)),
        "error": rgb_to_hex(_brighten(_hue_to_rgb(0.0), 3.0)),
    }
    return {"name": f"dark-hue{hue:g}", "colors": colors}


def _print_report(theme: Theme) -> None:
    print(f"{theme['name']}:")
    for line in check(theme):
        print(f"  {line}")


def read_theme(path: str) -> Theme:
    """Read a theme.json (`{name, colors, palettes?}`) from `path`."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    theme: Theme = {"name": raw.get("name", "palette"), "colors": raw["colors"]}
    if "palettes" in raw:
        theme["palettes"] = raw["palettes"]
    return theme


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate theme", description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check_p = sub.add_parser("check", help="verify a palette's WCAG contrast")
    check_p.add_argument("palette", help="a theme.json (`{name, colors}`)")
    gen_p = sub.add_parser("generate", help="build a dark palette from an accent hue")
    gen_p.add_argument("--hue", type=float, default=150.0, help="the accent hue 0..360")
    gen_p.add_argument(
        "--c", action="store_true", help="emit a C header (RGB565), not JSON"
    )
    emit_p = sub.add_parser("emit", help="emit a C header (RGB565) from a theme.json")
    emit_p.add_argument("palette", help="a theme.json (`{name, colors}`)")
    write_p = sub.add_parser("write", help="write the C header into the repo")
    write_p.add_argument("palette", help="a theme.json (`{name, colors}`)")
    write_p.add_argument(
        "output", help="the header to write, e.g. firmware/gen/theme.h"
    )
    args = parser.parse_args(argv)

    if args.action == "check":
        try:
            theme = read_theme(args.palette)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"theme: cannot read {args.palette!r}: {exc}", file=sys.stderr)
            return 1
        _print_report(theme)
        return 0 if all("FAIL" not in line for line in check(theme)) else 1

    if args.action == "emit":
        try:
            theme = read_theme(args.palette)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"theme: cannot read {args.palette!r}: {exc}", file=sys.stderr)
            return 1
        print(emit_c(theme), end="")
        return 0

    if args.action == "write":
        try:
            theme = read_theme(args.palette)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"theme: cannot read {args.palette!r}: {exc}", file=sys.stderr)
            return 1
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(emit_c(theme).encode("utf-8"))
        print(f"theme: wrote {output}")
        return 0

    theme = generate(args.hue)
    if args.c:
        print(emit_c(theme), end="")
    else:
        print(json.dumps(theme, indent=2))
        _print_report(theme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
