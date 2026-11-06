# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate fmt`: run clang-format over the C files (`.clang-format`, §6.8)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import runner

_FW = Path(__file__).resolve().parents[1] / "firmware"


def _c_files() -> list[str]:
    files: list[str] = []
    for pattern in ("*.c", "*.h"):
        files.extend(str(p) for p in _FW.rglob(pattern) if "build" not in p.parts)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate fmt", description=__doc__)
    parser.add_argument("--check", action="store_true", help="report, don't reformat")
    args = parser.parse_args(argv)

    if shutil.which("clang-format"):
        cmd = (
            ["clang-format", "--dry-run", "--Werror"]
            if args.check
            else ["clang-format", "-i"]
        )
        return subprocess.run(cmd + _c_files(), cwd=_FW).returncode
    if runner.probe().docker:
        mode = ["--dry-run", "--Werror"] if args.check else ["-i"]
        return runner.run(["clang-format"] + mode + _c_files(), cwd="/work/firmware")
    print("fmt: blocked because clang-format was not found", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
