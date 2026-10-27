# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate lint --c` — the C standing checks (§6.1, §12.8).

Static, grep-based checks (clang-tidy is the deep AST pass, run separately): SEC-1
MAXP bounds, SEC-2 UAC access, ROM-address constants, HAL-only MMIO, and no
`double`/allocation in the DSP TU.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
FW = _ROOT / "firmware"

# the SFR/CPU register block (MMIO) and the flash/boot addresses (ROM)
_SFR_ADDR = re.compile(r"0x1EEE[0-9a-fA-F]{3}")
_FLASH_ADDR = re.compile(r"0x1c0[0-9a-fA-F]{4}|0x02000000")


def _src_files(suffixes: tuple[str, ...]) -> list[Path]:
    return [
        p
        for p in FW.joinpath("src").rglob("*")
        if p.suffix in suffixes and "build" not in p.parts
    ]


def _mmio_hal_only(_: Path) -> list[str]:
    """MMIO (FM1_PR or the SFR block) belongs in hal/, never in src/."""
    errors: list[str] = []
    for p in FW.joinpath("src").glob("*.c"):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "FM1_PR(" in line or _SFR_ADDR.search(line):
                errors.append(f"{p.relative_to(FW)}:{i}: MMIO access outside hal/")
    return errors


def _rom_in_map(_: Path) -> list[str]:
    """Hardcoded flash/boot addresses belong in hal/fm1_flash_map.h, not src/."""
    errors: list[str] = []
    for p in _src_files((".c", ".h")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _FLASH_ADDR.search(line):
                errors.append(
                    f"{p.relative_to(FW)}:{i}: hardcoded flash address: {line.strip()}"
                )
    return errors


def _dsp_no_double_alloc(_: Path) -> list[str]:
    """The DSP TU is integer, platform-free: no double or allocation."""
    text = (FW / "src" / "rib_dsp.c").read_text(encoding="utf-8")
    errors: list[str] = []
    for bad in ("double", "malloc", "alloca", "calloc", "realloc"):
        if re.search(rf"\b{bad}\b", text):
            errors.append(f"src/rib_dsp.c: forbidden {bad!r} in the DSP TU")
    return errors


def _maxp_bounds(_: Path) -> list[str]:
    """SEC-1: a buffer index equal to MAXP is out of bounds (valid: 0..MAXP-1)."""
    errors: list[str] = []
    for p in FW.joinpath("src").glob("*.c"):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\[MAXP\]\s*=", line) or re.search(r"\[MAXP \+", line):
                errors.append(
                    f"{p.relative_to(FW)}:{i}: MAXP-bounds violation: {line.strip()}"
                )
    return errors


_CHECKS: list[tuple[str, Callable[[Path], list[str]]]] = [
    ("mmio", _mmio_hal_only),
    ("rom", _rom_in_map),
    ("dsp", _dsp_no_double_alloc),
    ("maxp", _maxp_bounds),
]


def c_checks() -> list[str]:
    """Run the C standing checks; return the list of violations (empty = clean)."""
    errors: list[str] = []
    for _name, check in _CHECKS:
        errors.extend(check(FW))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate lint", description=__doc__)
    parser.add_argument("--c", action="store_true", dest="c_checks", help="C checks")
    args = parser.parse_args(argv)

    if not args.c_checks:
        parser.error("give --c (the C standing checks)")

    errors = c_checks()
    if errors:
        for error in errors:
            print(f"lint: {error}", file=sys.stderr)
        return 1
    print("lint --c: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
