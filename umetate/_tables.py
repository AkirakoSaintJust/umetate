# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The table generator (docs/roadmap.md §12.4): patch `tables:` -> `const` XIP arrays.

Built-in shapes + a small inline spec. Every table becomes a `const int16_t
table_<name>[]` + a `#define table_<name>_len` in `tables.c`/`.h`; a node body may
reference it with the `${table.<name>}` placeholder.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from ._ir import GenError, Table, to_c_identifier
from ._schema import TableSpec

_TABLE_KINDS = ("wavetable", "segments", "spectrum", "phase_map", "routing")
_WAVE_SHAPES = ("sine", "triangle", "square", "saw")

# The 8 distinct 4-op FM algorithms (ymfm `s_algorithm_ops` 0..7 — the standard
# TX81Z/DX100/DX21 4-op set). Each is (mod, carrier): mod[i][j] = 1 if operator j
# phase-modulates operator i; carrier[i] = 1 if operator i is summed to the output.
# Operators op0..op3 are ymfm's O1..O4.
_ROUTING: list[tuple[list[list[int]], list[int]]] = [
    # 0: O1 -> O2 -> O3 -> O4 -> out (O4)
    ([[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], [0, 0, 0, 1]),
    # 1: (O1 + O2) -> O3 -> O4 -> out (O4)
    ([[0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 0, 0], [0, 0, 1, 0]], [0, 0, 0, 1]),
    # 2: (O1 + (O2 -> O3)) -> O4 -> out (O4)
    ([[0, 0, 0, 0], [0, 0, 0, 0], [0, 1, 0, 0], [1, 0, 1, 0]], [0, 0, 0, 1]),
    # 3: ((O1 -> O2) + O3) -> O4 -> out (O4)
    ([[0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0], [0, 1, 1, 0]], [0, 0, 0, 1]),
    # 4: (O1 -> O2) + (O3 -> O4) -> out (O2 + O4)
    ([[0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0]], [0, 1, 0, 1]),
    # 5: (O1 -> O2) + (O1 -> O3) + (O1 -> O4) -> out (O2 + O3 + O4)
    ([[0, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]], [0, 1, 1, 1]),
    # 6: (O1 -> O2) + O3 + O4 -> out (O2 + O3 + O4)
    ([[0, 0, 0, 0], [1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], [0, 1, 1, 1]),
    # 7: O1 + O2 + O3 + O4 -> out (all four carriers)
    ([[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], [1, 1, 1, 1]),
]


def table_cname(name: str) -> str:
    """The C identifier for a table (also the `${table.<name>}` replacement)."""
    return f"table_{to_c_identifier(name)}"


def build_tables(raw: Mapping[str, TableSpec]) -> list[Table]:
    """Parse + generate every `tables:` entry into a `Table` (deterministic)."""
    return [_build_table(name, spec) for name, spec in raw.items()]


def _build_table(name: str, spec: TableSpec) -> Table:
    kind = spec["kind"]
    if kind not in _TABLE_KINDS:
        raise GenError(f"tables.{name}: unknown kind {kind!r}")
    if kind == "wavetable":
        values = _wave(spec.get("shape", "sine"), spec.get("size", 256))
    elif kind == "phase_map":
        values = _phase_map(spec)
    elif kind == "spectrum":
        values = _spectrum(spec)
    elif kind == "routing":
        values = _routing()
    else:
        values = _segments(spec)
    if not values:
        raise GenError(f"tables.{name}: empty table")
    if any(not -32768 <= v <= 32767 for v in values):
        raise GenError(f"tables.{name}: a value is outside int16 range")
    return Table(name=name, kind=kind, size=len(values), values=values)


def _wave(shape: str, size: int) -> list[int]:
    if shape not in _WAVE_SHAPES:
        raise GenError(f"tables: unknown wavetable shape {shape!r}")
    if size < 1 or size > 65536:
        raise GenError(f"tables: bad wavetable size {size}")

    def f(ph: float) -> float:
        if shape == "sine":
            return math.sin(2 * math.pi * ph)
        if shape == "triangle":
            return 1 - 4 * abs(ph - 0.5)
        if shape == "square":
            return 1.0 if ph < 0.5 else -1.0
        return 2 * ph - 1  # saw

    return [round(f(i / size) * 32767) for i in range(size)]


def _phase_map(spec: TableSpec) -> list[int]:
    size = spec.get("size", 256)
    if size < 1 or size > 65536:
        raise GenError(f"tables: bad phase_map size {size}")
    return [round(32767 * i / max(size - 1, 1)) for i in range(size)]


def _spectrum(spec: TableSpec) -> list[int]:
    """A wavetable from harmonic amplitudes via additive synthesis — the inverse
    FFT: `table[i] = sum_k a_k * sin(2*pi*k*i/size) / N`, normalized to Q15."""
    harmonics = spec.get("harmonics") or []
    if not harmonics:
        raise GenError("tables: spectrum needs inline `harmonics`")
    size = spec.get("size", 256)
    if size < 1 or size > 65536:
        raise GenError("tables: bad spectrum size")
    n = len(harmonics)
    values: list[int] = []
    for i in range(size):
        ph = 2.0 * math.pi * i / size
        total = sum(a * math.sin(k * ph) for k, a in enumerate(harmonics, start=1))
        values.append(round(total / n))
    return values


def _segments(spec: TableSpec) -> list[int]:
    """A breakpoint envelope as flattened `[t_ms, level, ...]` pairs (ADSR default)."""
    points = spec.get("points")
    if points is None:
        points = [[0, 0], [100, 32767], [400, 22000], [800, 0]]
    flat: list[int] = []
    for point in points:
        t, level = point
        flat.append(t)
        flat.append(level)
    return flat


def _routing() -> list[int]:
    """The 8-algorithm routing matrix: per algorithm, 4 modulation rows (dest 0..3)
    + 1 carrier-mask row, each a 4-weight 0/1 vector (Q15 0 or 32767). Layout:
    `routing[algorithm * 20 + dest * 4 + src]`."""
    flat: list[int] = []
    for mod, carrier in _ROUTING:
        for dest in range(4):
            flat.extend(32767 if w else 0 for w in mod[dest])
        flat.extend(32767 if w else 0 for w in carrier)
    return flat


def emit_tables_h(tables: list[Table]) -> str:
    """The `tables.h` extern declarations."""
    lines = [
        "/* GENERATED by umetate — do not edit. */",
        "#pragma once",
        "#include <stdint.h>",
        "",
    ]
    for t in tables:
        cname = table_cname(t.name)
        lines.append(f"#define {cname}_len {t.size}")
        lines.append(f"extern const int16_t {cname}[{t.size}];")
    return "\n".join(lines) + "\n"


def emit_tables_c(tables: list[Table]) -> str:
    """The `tables.c` `const` XIP array definitions."""
    lines = [
        "/* GENERATED by umetate — do not edit. */",
        '#include "tables.h"',
        "",
    ]
    for t in tables:
        cname = table_cname(t.name)
        body = ", ".join(str(v) for v in t.values)
        lines.append(f"const int16_t {cname}[{t.size}] = {{ {body} }};")
    return "\n".join(lines) + "\n"
