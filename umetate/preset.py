# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate preset`: export or import the preset bank as SysEx
(roadmap §6.11.4).

This is the host-side round trip. A JSON bank holds 128 single parts and 64 multi
patches, and the `.syx` stream is a sequence of dump frames, because the device
transfer over MIDI is the firmware's job (F7). Here the `.syx` file is the exchange
format.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._presets import as_bank, export_bank, import_bank
from ._schema import Patch, as_patch
from .generate import generate_sysex_layout


def _model_byte(text: str) -> int:
    value = int(text, 0)
    if not 0 <= value <= 0xFF:
        raise argparse.ArgumentTypeError(f"model must be 0..255, got {value}")
    return value


def _load_patch(path: str) -> Patch:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"preset: cannot read patch {path!r}: {exc}") from exc
    return as_patch(raw)


def _export(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="umetate preset export", description="export a JSON bank to a .syx stream"
    )
    parser.add_argument("patch", help="patch.json (the record geometry)")
    parser.add_argument("--bank", required=True, help="the JSON bank to export")
    parser.add_argument(
        "--model",
        required=True,
        type=_model_byte,
        help="the firmware model byte (0-255)",
    )
    parser.add_argument("--out", required=True, help="the .syx file to write")
    args = parser.parse_args(argv)

    try:
        bank = as_bank(json.loads(Path(args.bank).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"preset: cannot read bank {args.bank!r}: {exc}", file=sys.stderr)
        return 1
    layout = generate_sysex_layout(_load_patch(args.patch))
    try:
        Path(args.out).write_bytes(export_bank(layout, bank, args.model))
    except OSError as exc:
        print(f"preset: cannot write {args.out!r}: {exc}", file=sys.stderr)
        return 1
    print(f"preset: exported 128 single parts + 64 multi patches to {args.out}")
    return 0


def _import(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="umetate preset import", description="import a .syx stream to a JSON bank"
    )
    parser.add_argument("patch", help="patch.json (the record geometry)")
    parser.add_argument(
        "--from", required=True, dest="src", help="the .syx file to read"
    )
    parser.add_argument(
        "--model",
        required=True,
        type=_model_byte,
        help="the firmware model byte (0-255)",
    )
    parser.add_argument("--out", required=True, help="the JSON bank to write")
    args = parser.parse_args(argv)

    try:
        stream = Path(args.src).read_bytes()
    except OSError as exc:
        print(f"preset: cannot read {args.src!r}: {exc}", file=sys.stderr)
        return 1
    layout = generate_sysex_layout(_load_patch(args.patch))
    bank = import_bank(stream, layout, args.model)
    if bank is None:
        print(
            f"preset: {args.src!r} is not a valid {args.model:#04x} bank "
            "(corrupt, truncated, or wrong model)",
            file=sys.stderr,
        )
        return 1
    try:
        Path(args.out).write_text(json.dumps(bank, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"preset: cannot write {args.out!r}: {exc}", file=sys.stderr)
        return 1
    print(f"preset: imported a bank to {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("usage: umetate preset {export|import} [ARGS]")
        return 0
    if args[0] == "export":
        return _export(args[1:])
    if args[0] == "import":
        return _import(args[1:])
    print(f"preset: unknown subcommand {args[0]!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
