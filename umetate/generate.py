# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The patch generator (docs/roadmap.md §12.4).

A pure function: patch.json + the node library -> `<synth>_dsp.c`. Deterministic.
Expands macros (dots -> underscores for C ids), type-checks the graph, cycle-checks
with `delay1`/`delayN` as breakers, allocates SoA state, and emits one fused
monomorphic `render` (the §12.1 seam).
"""
from __future__ import annotations
from dataclasses import dataclass, field

from .nodes import NodeSpec, NODES

KIND_EVENT, KIND_CONTROL, KIND_AUDIO = "event", "control", "audio"
RESERVED = ("note", "gate", "velocity")   # voice-zone allocator inputs (bindings)


class GenError(Exception):
    pass


def _cid(name: str) -> str:
    """A patch id (dots) -> a C identifier (underscores)."""
    return name.replace(".", "_").replace("-", "_")


@dataclass
class NodeInstance:
    id: str                         # the patch id (dots), e.g. "carrier.ph"
    type: str
    zone: str                       # "voice" | "global"
    params: dict = field(default_factory=dict)
    spec: NodeSpec = None

    @property
    def c(self) -> str:
        return _cid(self.id)        # the C identifier, e.g. "carrier_ph"

    def state(self, name: str) -> str:
        return f"{self.c}_{name}"

    def state_ref(self, name: str, v: str) -> str:
        """Zone-aware state access: SoA `name[v]` for voice, scalar `name` for global."""
        return f"{self.c}_{name}[{v}]" if self.zone == "voice" else f"{self.c}_{name}"

    def param_expr(self, name: str) -> str:
        return f"{self.c}_{name}"

    # resolved by the generator: input port -> C expression (upstream output local)
    in_expr: dict = field(default_factory=dict, repr=False)

    def input(self, port: str, default: str = "0") -> str:
        return self.in_expr.get(port, default)


def _expand(patch, nodes, zone, inst_dict, instances, wires, bindings, macros):
    """Recursively expand a node/macro instance into leaf instances + wires + bindings.

    `bindings` maps (macro_id, port) -> (kind, node_id, field): kind "state" for a
    note-derived state target, "port" for a graph-edge rename.
    """
    typ = inst_dict["type"]
    if typ not in macros:
        spec = nodes.get(typ)
        if spec is None:
            raise GenError(f"unknown node type {typ!r} (instance {inst_dict['id']!r})")
        instances.append(NodeInstance(id=inst_dict["id"], type=typ, zone=zone,
                                      params=dict(inst_dict.get("params", {})), spec=spec))
        return
    m = macros[typ]
    prefix = inst_dict["id"]
    inner_params = dict(inst_dict.get("params", {}))
    for w in m.get("wires", []):
        frm, to = w["from"], w["to"]
        f_inner = _is_inner(frm, m)
        t_inner = _is_inner(to, m)
        if not f_inner and t_inner:
            bindings[(prefix, frm)] = _resolve_inner(to, m, prefix)     # macro in -> inner
        elif f_inner and not t_inner:
            bindings[(prefix, to)] = ("port",) + _resolve_inner(frm, m, prefix)[1:]  # inner -> macro out
        else:
            wires.append((_split(_prefix_port(frm, prefix)), _split(_prefix_port(to, prefix))))   # inner wire
    for n in m.get("nodes", []):
        _expand(patch, nodes, zone, {**n, "id": f"{prefix}.{n['id']}"}, instances, wires, bindings, macros)
    for mp, tgt in m.get("params", {}).items():
        kind, nid, field = _resolve_inner(tgt, m, prefix)
        inst = next(i for i in instances if i.id == nid)
        val = inner_params.get(mp)
        if kind == "state":
            inst.params["_note_field"] = field                          # note-derived, set at note-on
            inst.params["_note_ratio"] = val if val is not None else 1
        else:
            inst.params[field] = val


def _is_inner(port: str, m: dict) -> bool:
    first = port.split(".")[0]
    return any(n["id"] == first for n in m.get("nodes", []))


def _prefix_port(port: str, prefix: str) -> str:
    return f"{prefix}.{port}"


def _resolve_inner(port: str, m: dict, prefix: str) -> tuple:
    """Resolve a macro-inner port reference to (kind, node_id, field)."""
    node_id, field = port.split(".", 1)
    nid = f"{prefix}.{node_id}"
    node = next(n for n in m.get("nodes", []) if n["id"] == node_id)
    spec = NODES.get(node["type"])
    if spec and field in spec.state:
        return ("state", nid, field)
    if spec and field in spec.params:
        return ("param", nid, field)
    return ("port", nid, field)


def _resolve_port(port: tuple, bindings: dict) -> tuple:
    """Resolve a (node_id, port_name) through the macro bindings -> (kind, id, field)."""
    key = port
    while key in bindings:
        kind, nid, field = bindings[key]
        if kind == "state":
            return ("state", nid, field)
        key = (nid, field)
    return ("port", key[0], key[1])


def generate(patch: dict, nodes: dict[str, NodeSpec] = None) -> str:
    nodes = nodes or NODES
    name = _cid(patch["name"])        # sanitize for C identifiers (dots/hyphens -> _)
    voices = int(patch.get("voices", 1))
    macros = patch.get("macros", {})

    instances: list[NodeInstance] = []
    wires: list[tuple] = []
    bindings: dict = {}
    zones: dict = {}

    for zone in ("voice", "global"):
        z = patch.get(zone, {})
        zones[zone] = z
        for n in z.get("nodes", []):
            _expand(patch, nodes, zone, n, instances, wires, bindings, macros)
        for w in z.get("wires", []):
            wires.append((_split(w["from"]), _split(w["to"])))

    # ---- type-check + input resolution (resolved through the macro bindings) ----
    by_id = {i.id: i for i in instances}
    for e in wires:
        src = _resolve_port(e[0], bindings)
        dst = _resolve_port(e[1], bindings)
        if src[0] == "state" or dst[0] == "state":
            continue                       # note-derived state: handled by the allocator
        src_id, src_port = src[1], src[2]
        dst_id, dst_port = dst[1], dst[2]
        if src_id == "voice":
            by_id[dst_id].in_expr[dst_port] = "bus"      # the voice-zone mix
            continue
        if dst_id == "out":
            continue                                     # the final output (last global node)
        if src_id in RESERVED or dst_id in RESERVED:
            continue                       # allocator binding
        src_inst = by_id.get(src_id)
        dst_inst = by_id.get(dst_id)
        if src_inst is None or dst_inst is None:
            raise GenError(f"wire to/from unknown node: {src_id}.{src_port} -> {dst_id}.{dst_port}")
        if src_port not in src_inst.spec.outs:
            raise GenError(f"{src_id} has no output port {src_port!r}")
        if dst_port not in dst_inst.spec.ins:
            raise GenError(f"{dst_id} has no input port {dst_port!r}")
        sk, dk = src_inst.spec.outs[src_port], dst_inst.spec.ins[dst_port]
        if sk == KIND_AUDIO and dk == KIND_EVENT:
            raise GenError(f"type error: audio->event {src_id}.{src_port} -> {dst_id}.{dst_port}")
        if sk != dk and not ({sk, dk} <= {KIND_AUDIO, KIND_CONTROL}):
            raise GenError(f"type error: {sk}->{dk} {src_id}.{src_port} -> {dst_id}.{dst_port}")
        dst_inst.in_expr[dst_port] = f"{src_inst.c}_{src_port}_x"   # the upstream output local

    order = _topo(instances, wires)

    # resolve the voice_out (a named voice-zone signal) through the bindings
    voice_out = zones["voice"].get("voice_out")
    if voice_out:
        k, nid, field = _resolve_port(_split(voice_out), bindings)
        voice_out_expr = f"{_cid(nid)}_{field}_x"
    else:
        voice_out_expr = None

    return _emit(name, voices, instances, order, zones, voice_out_expr)


def _split(port: str) -> tuple:
    if "." in port:
        a, b = port.rsplit(".", 1)
        return a, b
    return port, ""


def _topo(instances, wires):
    ids = [i.id for i in instances]
    deps = {i.id: set() for i in instances}
    for (s, _), (d, _) in wires:
        if s in ids and d in ids and s != d:
            src = next(i for i in instances if i.id == s)
            if src.type not in ("delay1", "delayN"):
                deps[d].add(s)
    order, ready = [], [i.id for i in instances if not deps[i.id]]
    remaining = set(ids)
    while ready:
        n = ready.pop()
        if n in remaining:
            order.append(n)
            remaining.discard(n)
        for m in sorted(remaining):
            deps[m].discard(n)
            if not deps[m] and m not in ready and m not in order:
                ready.append(m)
    if remaining:
        raise GenError(f"cycle not broken by delay1/delayN: {sorted(remaining)}")
    return order


def _emit(name, voices, instances, order, zones, voice_out_expr=None):
    c = []
    c.append(f"/* GENERATED by umetate — do not edit. name={name} voices={voices} */")
    c.append('#include "fm1_math.h"')
    c.append("")
    c.append("#ifndef UMETATE_CPU1")
    c.append("#define UMETATE_CPU1")
    c.append("#endif")
    c.append("#ifndef UMETATE_POOL")
    c.append("#define UMETATE_POOL")
    c.append("#endif")
    c.append("")
    c.append(f"#define NVOICE {voices}")
    c.append("")

    c += _note_to_inc()

    # ---- state (SoA for voice, scalar for global) ----
    for i in instances:
        for sname, kind in i.spec.state.items():
            if kind == "pool":
                c.append(f"#define {i.state(sname)}_len 8192")
                c.append(f"#define {i.c}_delay_mask 8191")
                c.append(f"static int16_t {i.state(sname)}[{i.state(sname)}_len] UMETATE_POOL;")
            elif i.zone == "voice":
                c.append(f"static uint32_t {i.state(sname)}[NVOICE] UMETATE_CPU1;")
            else:
                c.append(f"static uint32_t {i.state(sname)} UMETATE_CPU1;")
    c.append("static uint8_t voice_gate[NVOICE] UMETATE_CPU1;")
    c.append("static uint8_t voice_note[NVOICE] UMETATE_CPU1;")
    c.append("static uint32_t voice_age[NVOICE] UMETATE_CPU1;")
    c.append("static uint32_t ages;")
    for i in instances:
        for pname, pkind in i.spec.params.items():
            val = i.params.get(pname)
            c.append(f"static int32_t {i.param_expr(pname)} = {_default(pkind, val)};")
    c.append("")

    # ---- fused render ----
    c.append(f"void {name}_dsp_render(int32_t *out, uint32_t frames) {{")
    c.append("    for (uint32_t f = 0; f < frames; f++) {")
    c.append("        int32_t bus = 0;")
    c.append("        for (uint32_t v = 0; v < NVOICE; v++) {")
    c.append("            if (!voice_gate[v]) continue;")
    # collect read/write statements; delay1/delayN writes are ordered last (cycle-breakers)
    reads, writes, voice_last = [], [], None
    for iid in order:
        i = next(x for x in instances if x.id == iid)
        if i.zone != "voice":
            continue
        outs, read, write = i.spec.emit(i, "v")
        reads.extend(read)
        writes.extend(write)
        for pname, expr in outs.items():
            if pname in ("audio", "out"):
                voice_last = expr
    for s in reads:
        c.append("            " + s)
    # the voice-zone mix into the bus
    if voice_out_expr:
        c.append(f"            bus = fm1_sat_add32(bus, {voice_out_expr});")
    elif voice_last:
        c.append(f"            bus = fm1_sat_add32(bus, {voice_last});")
    for s in writes:
        c.append("            " + s)
    c.append("        }")
    # global-zone nodes (chained via `bus`; inputs resolved through the wires)
    for iid in order:
        i = next(x for x in instances if x.id == iid)
        if i.zone != "global":
            continue
        outs, read, write = i.spec.emit(i, "0")
        for s in read:
            c.append("        " + s)
        out_port = "out" if "out" in outs else "audio"
        if out_port in outs:
            c.append(f"        bus = {outs[out_port]};")
        for s in write:
            c.append("        " + s)
    c.append("        out[f * 2] = bus; out[f * 2 + 1] = bus;")
    c.append("    }")
    c.append("}")
    c.append("")

    c += _seam(name, instances)
    return "\n".join(c) + "\n"


def _note_to_inc():
    return [
        "static const uint32_t note_inc_c9[12] = {",
        "    815363807u, 863847862u, 915214929u, 969636441u, 1027294024u, 1088380105u,",
        "    1153098554u, 1221665363u, 1294309365u, 1371273005u, 1452813141u, 1539201906u};",
        "static inline uint32_t note_to_inc(uint32_t note) {",
        "    return note_inc_c9[note % 12u] >> (10u - note / 12u);",
        "}",
        "",
    ]


def _seam(name, instances):
    c = []
    c.append(f"void {name}_dsp_reset(void) {{")
    c.append("    for (uint32_t v = 0; v < NVOICE; v++) voice_gate[v] = 0;")
    c.append("    ages = 0;")
    c.append("}")
    c.append("")
    c.append(f"void {name}_dsp_note_on(uint32_t note, uint32_t velocity) {{")
    c.append("    uint32_t pick = 0, best = 0xFFFFFFFFu, v;")
    c.append("    if (note > 127u || !velocity) return;")
    c.append("    for (v = 0; v < NVOICE; v++) {")
    c.append("        uint32_t score = (voice_note[v] == note && voice_gate[v]) ? 0u")
    c.append("                       : voice_gate[v] ? 0x80000000u + voice_age[v] : voice_age[v] + 1u;")
    c.append("        if (score < best) { best = score; pick = v; }")
    c.append("    }")
    c.append("    voice_note[pick] = (uint8_t)note;")
    c.append("    voice_age[pick] = ++ages;")
    c.append("    voice_gate[pick] = 1;")
    for i in instances:
        if i.type == "phasor" and i.zone == "voice":
            ratio = i.params.get("_note_ratio", 1)
            c.append(f"    {i.state('inc')}[pick] = note_to_inc(note) * {ratio}u;")
    c.append("}")
    c.append("")
    c.append(f"void {name}_dsp_note_off(uint32_t note) {{")
    c.append("    for (uint32_t v = 0; v < NVOICE; v++) if (voice_note[v] == note) voice_gate[v] = 0;")
    c.append("}")
    c.append("")
    c.append(f"void {name}_dsp_all_notes_off(void) {{")
    c.append("    for (uint32_t v = 0; v < NVOICE; v++) voice_gate[v] = 0;")
    c.append("}")
    c.append("")
    c.append(f"void {name}_dsp_set_bend_q16(uint32_t bend) {{ (void)bend; }}")
    c.append("")
    c.append(f"uint32_t {name}_dsp_lit(uint32_t base) {{")
    c.append("    uint32_t lit = 0;")
    c.append("    for (uint32_t v = 0; v < NVOICE; v++)")
    c.append("        if (voice_gate[v] && voice_note[v] >= base && voice_note[v] < base + 27u)")
    c.append("            lit |= 1u << (voice_note[v] - base);")
    c.append("    return lit;")
    c.append("}")
    c.append("")
    c.append(f"int {name}_dsp_quiet(void) {{")
    c.append("    for (uint32_t v = 0; v < NVOICE; v++) if (voice_gate[v]) return 0;")
    c.append("    return 1;")
    c.append("}")
    c.append("")
    return c


def _default(kind: str, val) -> int:
    if val is not None:
        return int(val)
    return {"q15": 32768, "q16": 65536, "q12": 4096, "q32": 0, "phase": 0}.get(kind, 0)


def _resolve_out(name: str, instances) -> str:
    for i in instances:
        if f"{i.id}.{name.split('.')[-1]}" == name:
            return f"{i.c}_{name.split('.')[-1]}_x"
    raise GenError(f"voice_out {name!r} is not a voice-zone output")


compile_patch = generate
