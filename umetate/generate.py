# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The patch generator's public entry (docs/roadmap.md §12.4).

A pure function: a patch + the node library -> `<synth>_dsp.c` (+ `tables.c`/`.h`).
Deterministic (same inputs -> byte-identical output). The passes live in
`_ir`/`_frontend`/`_backend`/`_tables`; this module only wires them together.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._backend import emit
from ._frontend import compile
from ._ir import CompiledGraph, GenError, NodeSpec, load_library, load_macros
from ._tables import emit_tables_c, emit_tables_h

__all__ = [
    "generate",
    "generate_params",
    "generate_tables",
    "param_ids",
    "GenError",
    "NodeSpec",
    "load_library",
    "load_macros",
]

_DEFAULT_LIBRARY = Path(__file__).resolve().parent.parent / "modules" / "nodes"
_DEFAULT_MACROS = Path(__file__).resolve().parent.parent / "modules" / "macros"


def _graph(
    patch: Mapping[str, Any],
    nodes: Mapping[str, NodeSpec] | None,
    macros: Mapping[str, Any] | None,
) -> CompiledGraph:
    if nodes is None:
        nodes = load_library(_DEFAULT_LIBRARY)
    if macros is None:
        macros = load_macros(_DEFAULT_MACROS)
    return compile(patch, nodes, macros)


def generate(
    patch: Mapping[str, Any],
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Any] | None = None,
) -> str:
    """Compile `patch` into generated `<synth>_dsp.c` source."""
    return emit(_graph(patch, nodes, macros))


def generate_params(
    patch: Mapping[str, Any],
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The flattened param table (`params.json`): id -> name + display metadata."""
    graph = _graph(patch, nodes, macros)
    return {
        "params": [
            {
                "id": p.id,
                "name": p.name,
                "target": p.target,
                "min": p.min,
                "max": p.max,
                "default": p.default,
                "curve": p.curve,
                "unit": p.unit,
                "rate": p.rate,
                "modulatable": p.modulatable,
            }
            for p in graph.params
        ]
    }


def param_ids(
    patch: Mapping[str, Any],
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    """The name -> set_param id map (friendly names *and* flattened targets)."""
    graph = _graph(patch, nodes, macros)
    ids: dict[str, int] = {}
    for p in graph.params:
        ids[p.name] = p.id
        ids[p.target] = p.id
    return ids


def generate_tables(
    patch: Mapping[str, Any],
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """The generated `tables.h` + `tables.c` (const XIP arrays) for `tables:`."""
    graph = _graph(patch, nodes, macros)
    return emit_tables_h(graph.tables), emit_tables_c(graph.tables)
