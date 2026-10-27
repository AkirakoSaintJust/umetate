# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The patch generator's public entry (docs/roadmap.md §12.4).

A pure function: a patch + the node library -> `<synth>_dsp.c`. Deterministic
(same inputs -> byte-identical output). The passes live in `_ir`/`_frontend`/
`_backend`; this module only wires them together.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._backend import _flat_params, emit
from ._frontend import compile
from ._ir import GenError, NodeSpec, load_library

__all__ = ["generate", "generate_params", "GenError", "NodeSpec", "load_library"]

_DEFAULT_LIBRARY = Path(__file__).resolve().parent.parent / "modules"


def generate(
    patch: Mapping[str, Any], nodes: Mapping[str, NodeSpec] | None = None
) -> str:
    """Compile `patch` into generated `<synth>_dsp.c` source."""
    if nodes is None:
        nodes = load_library(_DEFAULT_LIBRARY)
    return emit(compile(patch, nodes))


def generate_params(
    patch: Mapping[str, Any], nodes: Mapping[str, NodeSpec] | None = None
) -> dict[str, Any]:
    """The flattened param table (`params.json`): id -> display name + default."""
    if nodes is None:
        nodes = load_library(_DEFAULT_LIBRARY)
    graph = compile(patch, nodes)
    return {
        "params": [
            {"id": i, "name": name, "default": default}
            for i, (_, name, default) in enumerate(_flat_params(graph))
        ]
    }
