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

from ._backend import emit
from ._frontend import compile
from ._ir import (
    CompiledGraph,
    GenError,
    NodeSpec,
    ParamEntry,
    load_library,
    load_macros,
)
from ._schema import CcEntry, CcMap, Macro, ParamsDoc, Patch, SysexLayout
from ._tables import emit_tables_c, emit_tables_h

__all__ = [
    "generate",
    "generate_params",
    "generate_tables",
    "generate_sysex_layout",
    "generate_synth_header",
    "generate_dsp_header",
    "generate_cc_map",
    "cc_map_reverse",
    "generate_cc_header",
    "param_ids",
    "param_meta",
    "GenError",
    "NodeSpec",
    "load_library",
    "load_macros",
]

_DEFAULT_LIBRARY = Path(__file__).resolve().parent.parent / "modules" / "nodes"
_DEFAULT_MACROS = Path(__file__).resolve().parent.parent / "modules" / "macros"


def _graph(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None,
    macros: Mapping[str, Macro] | None,
) -> CompiledGraph:
    if nodes is None:
        nodes = load_library(_DEFAULT_LIBRARY)
    if macros is None:
        macros = load_macros(_DEFAULT_MACROS)
    return compile(patch, nodes, macros)


def generate(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> str:
    """Compile `patch` into generated `<synth>_dsp.c` source."""
    return emit(_graph(patch, nodes, macros))


def generate_params(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> ParamsDoc:
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
                "display": p.display,
            }
            for p in graph.params
        ]
    }


def param_ids(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> dict[str, int]:
    """The name -> set_param id map (friendly names *and* flattened targets).

    With parts, the per-part params carry a `.pN` suffix; part 0's params are also
    registered unsuffixed (the operator-relative names the panel uses — `op1.eg.r1`
    — address part 0, the CC/preset surface)."""
    graph = _graph(patch, nodes, macros)
    ids: dict[str, int] = {}
    for p in graph.params:
        ids[p.name] = p.id
        ids[p.target] = p.id
        if p.part == 0:
            ids[p.name.removesuffix(".p0")] = p.id
            ids[p.target.removesuffix(".p0")] = p.id
    return ids


def param_meta(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> dict[int, tuple[str, int, int, str]]:
    """The set_param id -> `(display, min, max, curve)` map (the panel's per-param
    display scale). `display` is the value's on-screen form (see `_schema`)."""
    graph = _graph(patch, nodes, macros)
    return {p.id: (p.display, p.min, p.max, p.curve) for p in graph.params}


def generate_tables(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> tuple[str, str]:
    """The generated `tables.h` + `tables.c` (const XIP arrays) for `tables:`."""
    graph = _graph(patch, nodes, macros)
    return emit_tables_h(graph.tables), emit_tables_c(graph.tables)


def generate_sysex_layout(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> SysexLayout:
    """The generated `sysex-layout.json` (roadmap §6.11.4): the per-firmware SysEx
    payload geometry — the `<model>` byte (the patch's `model`) + record/bank sizes
    from the patch's param + part counts."""
    from ._records import SLOTS, multi_patch_size, part_patch_size, settings_size

    graph = _graph(patch, nodes, macros)
    n_params = graph.n_voice_params
    n_parts = graph.n_parts
    return {
        "model": patch.get("model", 0),
        "n_params": n_params,
        "n_parts": n_parts,
        "part_patch_size": part_patch_size(n_params),
        "multi_patch_size": multi_patch_size(n_parts),
        "settings_size": settings_size(),
        "part_patch_bank_size": SLOTS * part_patch_size(n_params),
        "multi_patch_bank_size": SLOTS * multi_patch_size(n_parts),
    }


def generate_synth_header(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> str:
    """The generated `synth_layout.h`: the runtime constants the framework needs to
    address the engine — the model byte, the param counts, and the routing-param
    base (the id of part 0's channel; `routing_base + r*n_parts + p`, r = channel/
    low/high/level/delay)."""
    graph = _graph(patch, nodes, macros)
    n = graph.n_voice_params
    p = graph.n_parts
    g = graph.n_global_params
    return (
        "/* GENERATED by umetate — do not edit. The runtime layout (§6.11.4). */\n"
        "#pragma once\n"
        "#include <stdint.h>\n"
        f"#define SYNTH_MODEL {patch.get('model', 0)}u\n"
        f"#define SYNTH_N_PARAMS {n}u\n"
        f"#define SYNTH_N_PARTS {p}u\n"
        f"#define SYNTH_N_GLOBAL {g}u\n"
        "#define SYNTH_ROUTING_BASE "
        "(SYNTH_N_PARTS * SYNTH_N_PARAMS + SYNTH_N_GLOBAL)\n"
    )


def generate_dsp_header(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
) -> str:
    """The generated `<synth>_dsp.h`: the engine seam's prototypes (the frozen
    contract the app glue calls; roadmap §12.1)."""
    graph = _graph(patch, nodes, macros)
    name = graph.name
    lines = [
        f"/* GENERATED by umetate — do not edit. The {name} engine seam (§12.1). */",
        "#pragma once",
        "#include <stdint.h>",
        f"void {name}_dsp_reset(void);",
        f"void {name}_dsp_note_on(uint32_t note, uint32_t velocity);",
        (
            f"void {name}_dsp_note_on_ch(uint32_t note, uint32_t velocity, "
            "uint32_t channel);"
        ),
        f"void {name}_dsp_note_off(uint32_t note);",
        f"void {name}_dsp_all_notes_off(void);",
        f"void {name}_dsp_set_bend_q16(uint32_t bend);",
        f"uint32_t {name}_dsp_lit(uint32_t base);",
        f"int {name}_dsp_quiet(void);",
        f"int {name}_dsp_set_param(uint32_t id, int32_t value);",
        f"int32_t {name}_dsp_get_param(uint32_t id);",
        f"uint32_t {name}_dsp_param_count(void);",
        f"void {name}_dsp_render(int32_t *out, uint32_t frames);",
        f"void {name}_render_block(uint32_t arg);",
    ]
    if graph.taps:
        lines.append(f"#define {name}_N_TAP_CH {len(graph.taps) * graph.n_parts}u")
        lines.append(f"const int32_t *{name}_dsp_tap(uint32_t ch);")
    init = patch.get("init") or {}
    if init:
        # the INIT PATCH/PART defaults, emitted as a `static const` {id, value}
        # table (per-part params expand to every part of the same backing variable).
        ids = param_ids(patch, nodes, macros)
        by_id = {p.id: p for p in graph.params}
        entries: list[tuple[int, int]] = []
        for pname, value in init.items():
            base_id = ids.get(pname)
            if base_id is None:
                raise GenError(f"init: {pname!r} does not name a patch param")
            base = by_id.get(base_id)
            if base is not None and base.part is not None:
                for p in graph.params:
                    if p.cname == base.cname and p.part is not None:
                        entries.append((p.id, value))
            else:
                entries.append((base_id, value))
        lines.append(
            f"typedef struct {{ uint16_t id; int32_t value; }} {name}_init_entry;"
        )
        lines.append(f"static const {name}_init_entry {name}_init[] = {{")
        lines.extend(f"    {{ {eid}u, {value} }}," for eid, value in entries)
        lines.append("};")
        lines.append(
            f"#define {name}_INIT_N (sizeof {name}_init / sizeof {name}_init[0])"
        )
    lines.append("")
    return "\n".join(lines)


# the CCs a param map must not claim: sustain (64) and the channel-mode block
# (120..127: all-sound-off, reset, local, all-notes-off, omni/poly/mono).
_CC_RESERVED = frozenset({64}) | frozenset(range(120, 128))


def generate_cc_map(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
    base: int = 16,
) -> CcMap:
    """The fixed `cc -> param` map (roadmap §6.11.4): one CC per param, ascending
    from `base`, skipping the reserved CCs. The patch's `cc:` list names the
    CC-exposed params (friendly name or flattened target; with parts, the `.pN`
    names); absent, every param is mapped. A GenError when the params don't fit."""
    graph = _graph(patch, nodes, macros)
    want = patch.get("cc")
    params: list[ParamEntry]
    if want is not None:
        by_name = {p.name: p for p in graph.params}
        by_target = {p.target: p for p in graph.params}
        chosen: list[ParamEntry] = []
        for name in want:
            p = by_name.get(name) or by_target.get(name)
            if p is None:
                raise GenError(
                    f"cc: {name!r} does not name a patch param "
                    f"(use a friendly name or a flattened target)"
                )
            if p not in chosen:
                chosen.append(p)
        params = chosen
    else:
        params = list(graph.params)
    entries: list[CcEntry] = []
    cc = base
    for p in params:
        while cc in _CC_RESERVED:
            cc += 1
        if cc > 127:
            raise GenError(
                f"cc map: {len(params)} params do not fit in CC {base}..127 "
                f"(skipping the reserved {sorted(_CC_RESERVED)})"
            )
        entries.append({"cc": cc, "param": p.id, "name": p.name})
        cc += 1
    return {"base": base, "entries": entries}


def cc_map_reverse(cc_map: CcMap) -> dict[int, int]:
    """The reversed `param id -> cc` lookup of a cc-map."""
    return {entry["param"]: entry["cc"] for entry in cc_map["entries"]}


def generate_cc_header(
    patch: Patch,
    nodes: Mapping[str, NodeSpec] | None = None,
    macros: Mapping[str, Macro] | None = None,
    base: int = 16,
) -> str:
    """The generated `cc_map.h`: the fixed `cc -> param` table (indexed by CC, `CC_NONE`
    where unassigned), the reversed `param -> cc` table (`CC_NONE` for params outside
    the patch's `cc:` list), and the per-param [min, max] ranges (the MIDI handler
    scales a 7-bit CC value to the param's full range)."""
    graph = _graph(patch, nodes, macros)
    cm = generate_cc_map(patch, nodes, macros, base)
    by_cc = {entry["cc"]: entry["param"] for entry in cm["entries"]}
    by_param = {entry["param"]: entry["cc"] for entry in cm["entries"]}
    n = len(graph.params)

    def fmt_row(values: list[str]) -> str:
        return "    " + ", ".join(values) + ","

    lines = [
        "/* GENERATED by umetate — do not edit. The fixed cc -> param map",
        "   (roadmap §6.11.4): one CC per exposed param, ascending from CC_BASE,",
        "   skipping the reserved CCs. */",
        "#pragma once",
        "#include <stdint.h>",
        f"#define CC_BASE {cm['base']}u",
        f"#define CC_PARAMS {len(cm['entries'])}u",
        "#define CC_NONE 0xFFFFu",
        "static const uint16_t cc_to_param[128] = {",
    ]
    for i in range(0, 128, 8):
        lines.append(fmt_row([f"{by_cc.get(c, 0xFFFF)}u" for c in range(i, i + 8)]))
    lines.extend(
        [
            "};",
            "",
            f"static const uint8_t param_to_cc[{n or 1}] = {{",
        ]
    )
    for i in range(0, n, 12):
        lines.append(
            fmt_row([f"{by_param.get(p, 0xFF)}u" for p in range(i, min(i + 12, n))])
        )
    lines.extend(
        [
            "};",
            "",
            f"static const int32_t param_min[{n or 1}] = {{",
        ]
    )
    for i in range(0, n, 8):
        lines.append(
            fmt_row([str(graph.params[p].min) for p in range(i, min(i + 8, n))])
        )
    lines.extend(
        [
            "};",
            "",
            f"static const int32_t param_max[{n or 1}] = {{",
        ]
    )
    for i in range(0, n, 8):
        lines.append(
            fmt_row([str(graph.params[p].max) for p in range(i, min(i + 8, n))])
        )
    lines.extend(["};", ""])
    return "\n".join(lines)
