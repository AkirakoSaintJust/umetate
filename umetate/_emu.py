# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The fm1-emu host toolchain: paths + helpers shared by `setup`, `emu`, `quick-check`.

`umetate setup` installs Rust (rustup) and builds fm1-emu here (git-ignored
`.tools/`); `umetate emu` launches it; `quick-check` probes it.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EMU_DIR = _ROOT / ".tools" / "fm1-emu"
_RELEASE = _EMU_DIR / "target" / "release"

_EXE = ".exe" if sys.platform == "win32" else ""

EMU_DIR = _EMU_DIR
EMU_BIN = _RELEASE / f"fm1-emu{_EXE}"
LIVE_BIN = _RELEASE / f"fm1-live{_EXE}"


def emulator_built() -> bool:
    """Are both the batch runner (`fm1-emu`) and the GUI (`fm1-live`) built?"""
    return EMU_BIN.is_file() and LIVE_BIN.is_file()


def find_cargo() -> Path | None:
    """`cargo` on PATH, else the rustup default (`~/.cargo/bin`)."""
    found = shutil.which("cargo")
    if found:
        return Path(found)
    candidate = Path.home() / ".cargo" / "bin" / f"cargo{_EXE}"
    return candidate if candidate.is_file() else None
