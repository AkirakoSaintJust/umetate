# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate opm` - convert an OPM text patch bank to a Type P.fm1 bank.

The converter is a starting point, not a clone. It keeps the operator graph,
ratios, level curve, feedback depth, and the measured envelope timing, and it
writes a normal 128-slot bank JSON plus an optional `.syx` stream. The tolerance
and the known limits are in `docs/opm-to-type-p-fm1.md`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

from ._opm import OpmError, OpmVoice, convert_bank, parse_opm
from ._presets import as_bank, export_bank
from ._schema import as_patch
from .generate import generate_sysex_layout

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SYNTH = _ROOT / "examples" / "type-p-fm1"


class _Param(TypedDict):
    name: str
    default: int


def _part_defaults(synth_dir: Path) -> tuple[list[str], list[int]]:
    """The 139 part-relative parameters and their init values.

    `firmware/gen/params.json` is the manifest; the project's `patch.json`
    `init` block overrides the handful of values the instrument ships with.
    """
    manifest = synth_dir.parent.parent / "firmware" / "gen" / "params.json"
    if not manifest.is_file():
        manifest = _ROOT / "firmware" / "gen" / "params.json"
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        params = cast(list[_Param], raw["params"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OpmError(f"cannot read {manifest}: {exc}") from exc
    part = [p for p in params if p["name"].endswith(".p0")]
    if not part:
        raise OpmError(f"{manifest}: no part-relative parameters")
    names = [p["name"] for p in part]
    values = [p["default"] for p in part]
    patch_path = synth_dir / "patch.json"
    if patch_path.is_file():
        try:
            raw_init = json.loads(patch_path.read_text(encoding="utf-8")).get(
                "init", {}
            )
            init = cast(dict[str, int], raw_init) if isinstance(raw_init, dict) else {}
        except (OSError, json.JSONDecodeError):
            init = {}
        for i, name in enumerate(names):
            key = name[:-3]
            if key in init:
                values[i] = init[key]
            elif key == "attack" and "op1.eg.r1" in init:
                values[i] = init["op1.eg.r1"]
            elif key == "release" and "op1.eg.r4" in init:
                values[i] = init["op1.eg.r4"]
    return names, values


def _voice_is_silent(voice: OpmVoice) -> bool:
    for i, op in enumerate(voice.ops):
        if voice.slot_mask & (0x08 << i) and op.tl < 120:
            return False
    return True


def _select(
    voices: Sequence[OpmVoice],
    *,
    slots: Sequence[int],
    first: int | None,
    skip_silent: bool,
) -> list[OpmVoice]:
    chosen = list(voices)
    if slots:
        wanted = set(slots)
        chosen = [v for v in chosen if v.slot in wanted]
    if skip_silent:
        chosen = [v for v in chosen if not _voice_is_silent(v)]
    if first is not None:
        chosen = chosen[:first]
    return chosen


def _convert(args: argparse.Namespace) -> int:
    source = Path(args.input)
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"opm: cannot read {source}: {exc}", file=sys.stderr)
        return 1
    try:
        voices = parse_opm(text)
    except OpmError as exc:
        print(f"opm: {source}: {exc}", file=sys.stderr)
        return 1
    if not voices:
        print(f"opm: {source}: no voices", file=sys.stderr)
        return 1

    synth_dir = Path(args.synth) if args.synth else _DEFAULT_SYNTH
    try:
        names, defaults = _part_defaults(synth_dir)
        patch = as_patch(
            json.loads((synth_dir / "patch.json").read_text(encoding="utf-8"))
        )
        layout = generate_sysex_layout(patch)
    except (OpmError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"opm: {exc}", file=sys.stderr)
        return 1

    chosen = _select(
        voices,
        slots=args.slot or (),
        first=args.first,
        skip_silent=not args.keep_silent,
    )
    if not chosen:
        print("opm: no voices left after the selection", file=sys.stderr)
        return 1
    if len(chosen) > args.limit:
        print(
            f"opm: {len(chosen)} voices, keeping the first {args.limit} for the bank",
            file=sys.stderr,
        )
    try:
        bank, report = convert_bank(
            chosen,
            names=names,
            defaults=defaults,
            start=args.start,
            limit=args.limit,
            record_count=int(layout["n_params"]),
            pack=args.pack,
        )
    except OpmError as exc:
        print(f"opm: {exc}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else source.with_suffix(".bank.json")
    try:
        out.write_text(json.dumps(bank, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"opm: cannot write {out}: {exc}", file=sys.stderr)
        return 1

    syx = Path(args.syx) if args.syx else None
    if syx is not None:
        try:
            model = layout["model"] if args.model is None else args.model
            stream = export_bank(layout, as_bank(bank), model)
            syx.write_bytes(stream)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"opm: cannot write {syx}: {exc}", file=sys.stderr)
            return 1

    converted = sum(1 for _slot, _name, _warnings in report)
    print(f"opm: {len(chosen)} voices -> {converted} slots in {out}")
    if syx is not None:
        print(f"opm: SysEx bank -> {syx}")
    if args.report:
        for slot, name, warnings in report:
            print(f"  {slot:3d}  {name}")
            for warning in warnings:
                print(f"       - {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="umetate opm",
        description="convert an OPM text patch bank to a Type P.fm1 bank",
    )
    sub = parser.add_subparsers(dest="command")
    conv = sub.add_parser("convert", help="write a bank JSON and an optional .syx")
    conv.add_argument("input", help="the .opm text patch bank")
    conv.add_argument("--out", help="the bank JSON (default: <input>.bank.json)")
    conv.add_argument("--syx", help="also write a .syx bank stream here")
    conv.add_argument(
        "--synth",
        help=f"the Type P.fm1 project dir (default: {_DEFAULT_SYNTH})",
    )
    conv.add_argument(
        "--start", type=int, default=0, help="first bank slot (default 0)"
    )
    conv.add_argument(
        "--limit", type=int, default=128, help="most voices to convert (default 128)"
    )
    conv.add_argument(
        "--slot",
        type=int,
        action="append",
        help="only the OPM slot `@:n` with this number; repeatable",
    )
    conv.add_argument(
        "--first", type=int, help="only the first N voices after the other filters"
    )
    conv.add_argument(
        "--keep-silent",
        action="store_true",
        help="keep voices with no keyed, audible operator",
    )
    conv.add_argument(
        "--pack",
        action="store_true",
        help="ignore the OPM slot numbers and fill from --start upwards",
    )
    conv.add_argument(
        "--model", type=int, help="override the SysEx model byte (default: patch.json)"
    )
    conv.add_argument(
        "--report", action="store_true", help="print each slot and its warnings"
    )
    args = parser.parse_args(argv)
    if args.command != "convert":
        parser.print_help()
        return 0
    return _convert(args)


if __name__ == "__main__":
    sys.exit(main())
