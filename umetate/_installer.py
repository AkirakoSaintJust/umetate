# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Load the inherited `firmware/tools/fm1_install.py` as a module.

`inspect` (its parsing functions) and `flash` (its install seam) both need it; this
is the one loader (strangler-fig: the installer itself is not rewritten).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_FM1_INSTALL = (
    Path(__file__).resolve().parents[1] / "firmware" / "tools" / "fm1_install.py"
)


def load_installer() -> ModuleType:
    """Import the fm1tk-lineage installer as a module."""
    spec = importlib.util.spec_from_file_location("_fm1_install", _FM1_INSTALL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_FM1_INSTALL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
