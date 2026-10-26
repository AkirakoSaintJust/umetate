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

    def param_expr(self, name: str) -> str:
        return f"{self.c}_{name}"

    # resolved by the generator: input port -> C expression (upstream output local)
    in_expr: dict = field(default_factory=dict, repr=False)

    def input(self, port: str, default: str = "0") -> str:
        return self.in_expr.get(port, default)


def _expand(patch: dict, nodes: dict, zone: str, macro_inst: dict,
            instances: list, wires: list, macros: dict) -> str:
    """Expand one node/macro instance. Returns the node id (or None for a wire-only)."""
    typ = macro_inst["type"]
    if typ in macros:
        # ---- macro instance: expand its inner nodes with the prefix ----
        m = macros[typ]
        prefix = macro_inst["id"]
        inner_params = dict(macro_inst.get("params", {}))
        # map the macro's own ports/params to its inner nodes:
        #   wires of the form `from: <macro-port> to: <inner>` and
        #   `from: <inner> to: <macro-port>` are port/state renames.
        port_map = {}      # macro port name -> (inner node, inner port)  [port->port]
        state_map = {}     # macro port name -> (inner node, inner state) [port->state, note-derived]
        out_map = {}       # macro out name -> (inner node, inner port)
        for w in m.get("wires", []):
            frm, to = w["from"], w["to"]
            if not _is_inner(frm, m) and _is_inner(to, m):
                # macro input -> inner port/state
                tgt = _resolve_inner(to, m, prefix)
                if tgt[0] == "state":
                    state_map[frm] = tgt[1:]
                else:
                    port_map[frm] = tgt[1:]
            elif _is_inner(frm, m) and not _is_inner(to, m):
                out_map[to] = _resolve_inner(frm, m, prefix)[1:]
            else:
                # inner wire
                wires.append((_join(_prefix_port(frm, prefix)), _join(_prefix_port(to, prefix))))
        # emit the inner nodes
        for n in m.get("nodes", []):
            _expand(patch, nodes, zone, {**n, "id": f"{prefix}.{n['id']}"},
                    instances, wires, macros)
        # params: map macro params (ratio -> ph.ratio) to inner state/params
        for mp, tgt in m.get("params", {}).items():
            kind, node_id, field = _resolve_inner(tgt, m, prefix)
            val = inner_params.get(mp)
            if kind == "state":
                # a note-derived state target: handled at allocator time
                inst = next(i for i in instances if i.id == node_id)
                inst.params[f"_notederived_{field}"] = val if val is not None else 1
            else:
                inst = next(i for i in instances if i.id == node_id)
                inst.params[field] = val
        # record the port maps on the first inner node (or a dict keyed by macro id)
        return prefix
    else:
        spec = nodes.get(typ)
        if spec is None:
            raise GenError(f"unknown node type {typ!r} (instance {macro_inst['id']!r})")
        inst = NodeInstance(id=macro_inst["id"], type=typ, zone=zone,
                            params=dict(macro_inst.get("params", {})), spec=spec)
        instances.append(inst)
        return macro_inst["id"]


def _is_inner(port: str, m: dict) -> bool:
    # a macro wire source/target that names one of the macro's inner node ids
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


def _join(src: tuple, dst: tuple) -> tuple:
    return (src, dst)


def generate(patch: dict, nodes: dict[str, NodeSpec] = None) -> str:
    nodes = nodes or NODES
    name = patch["name"]
    voices = int(patch.get("voices", 1))
    macros = patch.get("macros", {})

    instances: list[NodeInstance] = []
    wires: list[tuple] = []          # ((src_id, src_port), (dst_id, dst_port))
    zones: dict = {}

    for zone in ("voice", "global"):
        z = patch.get(zone, {})
        zones[zone] = z
        for n in z.get("nodes", []):
            _expand(patch, nodes, zone, n, instances, wires, macros)
        for w in z.get("wires", []):
            wires.append((_split(w["from"]), _split(w["to"])))

    # ---- type-check + input resolution ----
    by_id = {i.id: i for i in instances}
    for e in wires:
        src_id, src_port = e[0]
        dst_id, dst_port = e[1]
        if src_id in RESERVED or dst_id in RESERVED:
            continue                       # allocator bindings
        src = by_id.get(src_id)
        dst = by_id.get(dst_id)
        if src is None or dst is None:
            raise GenError(f"wire to/from unknown node: {src_id}.{src_port} -> {dst_id}.{dst_port}")
        if src_port not in src.spec.outs:
            raise GenError(f"{src_id} has no output port {src_port!r}")
        if dst_port not in dst.spec.ins:
            raise GenError(f"{dst_id} has no input port {dst_port!r}")
        sk, dk = src.spec.outs[src_port], dst.spec.ins[dst_port]
        if sk == KIND_AUDIO and dk == KIND_EVENT:
            raise GenError(f"type error: audio->event {src_id}.{src_port} -> {dst_id}.{dst_port}")
        if sk != dk and not ({sk, dk} <= {KIND_AUDIO, KIND_CONTROL}):
            raise GenError(f"type error: {sk}->{dk} {src_id}.{src_port} -> {dst_id}.{dst_port}")
        dst.in_expr[dst_port] = f"{src.c}_{src_port}_x"   # the upstream output local

    order = _topo(instances, wires)

    return _emit(name, voices, instances, order, zones)


def _split(port: str) -> tuple:
    if "." in port:
        a, b = port.split(".", 1)
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


def _emit(name, voices, instances, order, zones):
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
        for sname, _kind in i.spec.state.items():
            if i.zone == "voice":
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
    voice_out = zones["voice"].get("voice_out")
    voice_last = None
    for iid in order:
        i = next(x for x in instances if x.id == iid)
        if i.zone != "voice":
            continue
        outs, stmts = i.spec.emit(i, "v")
        for s in stmts:
            c.append("            " + s)
        for pname, expr in outs.items():
            if pname == "audio":
                voice_last = expr
    # the voice-zone mix into the bus
    if voice_out:
        src = _resolve_out(voice_out, instances)
        c.append(f"            bus = fm1_sat_add32(bus, {src});")
    elif voice_last:
        c.append(f"            bus = fm1_sat_add32(bus, {voice_last});")
    c.append("        }")
    # global-zone nodes
    for iid in order:
        i = next(x for x in instances if x.id == iid)
        if i.zone != "global":
            continue
        for port in i.spec.ins:
            i.in_expr[port] = "bus"
        outs, stmts = i.spec.emit(i, "0")
        for s in stmts:
            c.append("        " + s)
        if "audio" in outs:
            bus_expr = outs["audio"]
            c.append(f"        bus = {bus_expr};")
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
            ratio = i.params.get("_notederived_inc", i.params.get("ratio", 1))
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
