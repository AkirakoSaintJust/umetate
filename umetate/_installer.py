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
from typing import cast

from ._schema import Installer

_FM1_INSTALL = (
    Path(__file__).resolve().parents[1] / "firmware" / "tools" / "fm1_install.py"
)


def load_installer_module() -> ModuleType:
    """Import the raw fm1tk-lineage installer module (test/internal use).

    The module itself is strangler-fig (not rewritten); this is the one place its
    file is imported.
    """
    spec = importlib.util.spec_from_file_location("_fm1_install", _FM1_INSTALL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_FM1_INSTALL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_installer() -> Installer:
    """The typed boundary: the public `Installer` surface `flash`/`inspect` touch."""
    return cast(Installer, load_installer_module())
