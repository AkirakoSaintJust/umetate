# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""UI token checks: one source, generated headers, no hard-coded values.

The design language lives in `design/tokens.json`. The firmware palette lives in
`firmware/theme.json`. Both are projected into C headers. This module checks
that the projections are current and that the UI source does not quietly
reintroduce a raw colour, font family, or theme value.

Run: `python3 -m umetate.tokens`
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

from .theme import Theme, emit_c, read_theme

ROOT = Path(__file__).resolve().parents[1]

_CAMEL = re.compile(r"(?<!^)(?=[A-Z])")
_CSS_TOKEN = re.compile(r"--p1-([a-z0-9-]+):\s*([^;]+);")
_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
_COLOUR_LITERAL = re.compile(
    r"Colour\s*\(\s*0x[0-9a-fA-F]+|Colour::from(?:String|RGB|RGBA)\s*\("
)
_FONT_LITERAL = re.compile(r'"(Zen Dots|DotGothic16|Arial Black)"')
_RGB_CALL = re.compile(r"\bRGB\s*\(")
_THEME_USE = re.compile(r"\bTHEME_[A-Z0-9_]+\b")
_C_DEFINE = re.compile(r"^\s*#define\s+(C_[A-Z0-9_]+)\s+(.+)$", re.MULTILINE)

_CONTROL_MAP: tuple[tuple[str, str | None, str], ...] = (
    ("defaultKnob", "cell", "p1-knob-cell"),
    ("defaultKnob", "dial", "p1-knob-dial"),
    ("operatorEnvelopeKnob", "cell", "p1-op-env-knob-cell"),
    ("operatorEnvelopeKnob", "dial", "p1-op-env-knob-dial"),
    ("operatorOscillatorKnob", "cell", "p1-op-osc-knob-cell"),
    ("operatorOscillatorKnob", "dial", "p1-op-osc-knob-dial"),
    ("operatorLfoKnob", "cell", "p1-op-osc-knob-cell"),
    ("operatorLfoKnob", "dial", "p1-op-osc-knob-dial"),
    ("partKnob", "cell", "p1-part-knob-cell"),
    ("partKnob", "dial", "p1-part-knob-dial"),
    ("pitchEnvelopeKnob", "cell", "p1-penv-knob-cell"),
    ("pitchEnvelopeKnob", "dial", "p1-penv-knob-dial"),
    ("keyVelocityKnob", "cell", "p1-kv-knob-cell"),
    ("keyVelocityKnob", "dial", "p1-kv-knob-dial"),
    ("muteTile", "width", "p1-mute-tile-width"),
    ("muteTile", "height", "p1-mute-tile-height"),
    ("legendSquare", None, "p1-legend-square"),
    ("levelTrackHeight", None, "p1-level-track-height"),
    ("toggleTrack", "width", "p1-toggle-width"),
    ("toggleTrack", "height", "p1-toggle-height"),
    ("scrollerMaxHeight", "patch", "p1-scroller-max-patch"),
    ("scrollerMaxHeight", "part", "p1-scroller-max-part"),
)

_SIZE_CSS = {"slotRow": "p1-text-slot"}
_SPACE_CSS = {
    "operatorColumnPadding": "p1-opcol-padding",
    "operatorColumnGap": "p1-opcol-gap",
    "operatorCardPadding": "p1-opcard-padding",
}
_BORDER_CSS = {"width": "p1-border-width"}


def _kebab(name: str) -> str:
    return _CAMEL.sub("-", name).lower()


def _norm(value: str) -> str:
    return " ".join(value.split()).lower()


def _norm_font(value: str) -> str:
    text = _norm(value)
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _expected_css(data: dict[str, object]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for key, value in _as_dict(data["colour"]).items():
        expected[f"p1-{_kebab(key)}"] = str(value).lower()
    for key, value in _as_dict(data["font"]).items():
        expected[f"p1-font-{_kebab(key)}"] = _norm_font(str(value))
    for key, value in _as_dict(data["size"]).items():
        name = _SIZE_CSS.get(key, f"p1-text-{_kebab(key)}")
        expected[name] = f"{value}px"
    for key, value in _as_dict(data["space"]).items():
        name = _SPACE_CSS.get(key, f"p1-{_kebab(key)}")
        expected[name] = f"{value}px"
    for key, value in _as_dict(data["border"]).items():
        css = _BORDER_CSS.get(key, f"p1-{_kebab(key)}")
        if isinstance(value, str):
            expected[css] = _norm(value)
        elif key == "radius":
            expected[css] = str(value)
        else:
            expected[css] = f"{value}px"
    control = _as_dict(data["control"])
    for group, field, css in _CONTROL_MAP:
        entry = control.get(group)
        raw_value: object
        if field is None:
            raw_value = entry
        elif isinstance(entry, dict):
            raw_value = cast(dict[str, object], entry).get(field)
        else:
            raw_value = None
        if isinstance(raw_value, int):
            expected[css] = f"{raw_value}px"
    return expected


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _check_css(errors: list[str]) -> None:
    data = json.loads((ROOT / "design" / "tokens.json").read_text(encoding="utf-8"))
    expected = _expected_css(data)
    css = (ROOT / "design" / "tokens.css").read_text(encoding="utf-8")
    actual: dict[str, str] = {}
    for match in _CSS_TOKEN.finditer(css):
        name = "p1-" + match.group(1)
        raw = match.group(2)
        actual[name] = _norm_font(raw) if name.startswith("p1-font-") else _norm(raw)
    for name, want in expected.items():
        if name not in actual:
            errors.append(f"design/tokens.css: missing --{name} ({want})")
        elif actual[name] != want:
            errors.append(
                f"design/tokens.css: --{name} is {actual[name]!r}, "
                f"tokens.json says {want!r}"
            )
    for name in actual:
        if name not in expected:
            errors.append(f"design/tokens.css: --{name} is not in tokens.json")


def _scan_source(path: Path, text: str, errors: list[str]) -> None:
    for match in _HEX.finditer(text):
        errors.append(f"{path}: hard-coded colour {match.group(0)}")
    if _COLOUR_LITERAL.search(text):
        errors.append(f"{path}: hard-coded juce::Colour literal")
    for match in _FONT_LITERAL.finditer(text):
        errors.append(f"{path}: hard-coded font family {match.group(1)!r}")


def _check_generator(errors: list[str]) -> None:
    """Every token in tokens.json must appear in the generated UiTokens.h."""
    data = json.loads((ROOT / "design" / "tokens.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "UiTokens.h"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "plugin" / "tools" / "gen_tokens.py"),
                str(ROOT / "design" / "tokens.json"),
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append("plugin/tools/gen_tokens.py failed: " + proc.stderr.strip())
            return
        header = output.read_text(encoding="utf-8")
    for key in _as_dict(data["colour"]):
        if f" {key} =" not in header:
            errors.append(f"UiTokens.h: missing colour token {key}")
    for key in _as_dict(data["font"]):
        token = "font" + key[0].upper() + key[1:]
        if f" {token} =" not in header:
            errors.append(f"UiTokens.h: missing font token {token}")
    for key in _as_dict(data["size"]):
        token = "text" + key[0].upper() + key[1:]
        if f" {token} =" not in header:
            errors.append(f"UiTokens.h: missing size token {token}")
    for key in _as_dict(data["space"]):
        if f" {key} =" not in header:
            errors.append(f"UiTokens.h: missing space token {key}")


def _check_plugin(errors: list[str]) -> None:
    patterns = (
        "plugin/juce/*.cpp",
        "plugin/juce/*.h",
        "plugin/ui/*.cpp",
        "plugin/ui/*.h",
    )
    for pattern in patterns:
        for path in sorted(ROOT.glob(pattern)):
            _scan_source(
                path.relative_to(ROOT), path.read_text(encoding="utf-8"), errors
            )


def _check_firmware(errors: list[str]) -> None:
    theme_path = ROOT / "firmware" / "theme.json"
    header_path = ROOT / "firmware" / "gen" / "theme.h"
    theme: Theme = read_theme(str(theme_path))
    expected = emit_c(theme)
    actual = header_path.read_text(encoding="utf-8")
    if actual != expected:
        errors.append(
            "firmware/gen/theme.h is stale: run "
            "`umetate theme write firmware/theme.json firmware/gen/theme.h`"
        )
        return

    defined = set(re.findall(r"#define\s+(THEME_[A-Z0-9_]+)", actual))
    defined.update({"THEME_PALETTES", "THEME_PALETTE_COUNT"})
    for folder in ("firmware/src", "firmware/gen", "firmware/hal"):
        for path in sorted((ROOT / folder).glob("*")):
            if path.suffix not in (".c", ".h") or path == header_path:
                continue
            text = path.read_text(encoding="utf-8")
            if _RGB_CALL.search(text):
                errors.append(f"{path.relative_to(ROOT)}: raw RGB() colour literal")
            for name in sorted(set(_THEME_USE.findall(text))):
                if name not in defined:
                    errors.append(f"{path.relative_to(ROOT)}: uses undefined {name}")

    gfx = (ROOT / "firmware" / "src" / "gfx.c").read_text(encoding="utf-8")
    for match in _C_DEFINE.finditer(gfx):
        name, value = match.group(1), match.group(2).strip()
        if "RGB(" in value or re.search(r"0x[0-9A-Fa-f]{4}", value):
            errors.append(
                f"firmware/src/gfx.c: {name} is a raw colour, not a theme token"
            )
        elif "THEME_" not in value and "pal[" not in value:
            errors.append(f"firmware/src/gfx.c: {name} does not come from theme.json")

    for name, steps in theme.get("palettes", {}).items():
        if len(steps) != 5:
            errors.append(f"firmware/theme.json: palette {name!r} needs 5 colours")
        for step in steps:
            try:
                _ = int(step.lstrip("#"), 16)
            except ValueError:
                errors.append(
                    f"firmware/theme.json: palette {name!r} has bad colour {step!r}"
                )


def check() -> list[str]:
    """Return the token/lint errors (empty means clean)."""
    errors: list[str] = []
    _check_css(errors)
    _check_generator(errors)
    _check_plugin(errors)
    _check_firmware(errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate tokens", description=__doc__)
    parser.parse_args(argv)
    errors = check()
    if errors:
        for error in errors:
            print(f"tokens: {error}", file=sys.stderr)
        return 1
    print("tokens: design tokens, generated headers and UI sources agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
