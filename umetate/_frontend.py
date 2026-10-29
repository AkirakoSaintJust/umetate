# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The generator's front-end (docs/roadmap.md §12.4): patch -> CompiledGraph.

Pure passes in order: parse, macro expansion, wire resolution, type-check,
cycle-check + topological sort. Everything is deterministic; errors raise GenError
with a reason, never a silent fallback.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from ._ir import (
    AUDIO,
    CONTROL,
    EVENT,
    OUT_SINK,
    RESERVED_INPUTS,
    TABLE,
    VOICE_SOURCE,
    CompiledGraph,
    Edge,
    GenError,
    NodeInstance,
    NodeSpec,
    ParamEntry,
    Port,
    PortSpec,
    param_bounds,
    param_default,
    to_c_identifier,
)
from ._schema import (
    Instance,
    Macro,
    NoteKind,
    ParamBinding,
    ParamTarget,
    Parts,
    Patch,
    Zone,
)
from ._tables import build_tables
from ._voice import mode_param_entries


def compile(
    patch: Patch,
    nodes: Mapping[str, NodeSpec],
    macros: Mapping[str, Macro] | None = None,
) -> CompiledGraph:
    """Compile a patch into a CompiledGraph (parse -> expand -> check -> topo).

    `macros` is the shipped macro library (`modules/macros`); the patch's own
    `macros:` section shadows it.
    """
    name = to_c_identifier(patch["name"])
    voices = patch["voices"]
    merged_macros = dict(macros or {})
    merged_macros.update(patch.get("macros") or {})

    instances: list[NodeInstance] = []
    raw_wires: list[tuple[str, str]] = []
    bindings: dict[tuple[str, str], tuple[str, str]] = {}

    voice_zone: Zone = patch.get("voice") or {"nodes": []}
    global_zone: Zone = patch.get("global") or {"nodes": []}

    for zone, zone_dict in (("voice", voice_zone), ("global", global_zone)):
        for inst_dict in zone_dict["nodes"]:
            id_ = inst_dict["id"]
            if id_ in RESERVED_INPUTS:
                raise GenError(
                    f"node id {id_!r} collides with the reserved allocator input "
                    f"{id_!r} (use a different id)"
                )
            _expand(
                inst_dict,
                zone,
                nodes,
                merged_macros,
                instances,
                raw_wires,
                bindings,
            )
        for wire in zone_dict.get("wires", []):
            raw_wires.append((wire["from"], wire["to"]))

    edges = [
        Edge(_resolve_ref(frm, bindings), _resolve_ref(to, bindings))
        for frm, to in raw_wires
    ]
    by_id = {i.id: i for i in instances}

    voice_out_ref = voice_zone.get("voice_out")
    voice_out, global_out = _typecheck(edges, by_id, voice_out_ref, bindings)

    parts = patch.get("parts")
    n_parts = parts["count"] if parts else 1
    if n_parts < 1:
        raise GenError("parts: 'count' must be >= 1")

    n_voice_params = sum(
        sum(1 for k in i.spec.params.values() if k != TABLE)
        for i in instances
        if i.zone == "voice"
    )
    n_global_params = sum(
        sum(1 for k in i.spec.params.values() if k != TABLE)
        for i in instances
        if i.zone == "global"
    )

    params = _build_params(instances, patch.get("params") or {}, n_parts, parts)
    params.extend(mode_param_entries(len(params)))

    return CompiledGraph(
        name=name,
        voices=voices,
        instances=instances,
        voice_order=_topo([i for i in instances if i.zone == "voice"], edges),
        global_order=_topo([i for i in instances if i.zone == "global"], edges),
        voice_out=voice_out,
        global_out=global_out,
        params=params,
        tables=build_tables(patch.get("tables") or {}),
        n_parts=n_parts,
        n_voice_params=n_voice_params,
        n_global_params=n_global_params,
    )


# per-part routing params (cname, field, min, max, fallback default)
_ROUTING_PARAMS: tuple[tuple[str, str, int, int, int], ...] = (
    ("part_channel", "channel", -1, 15, 0),
    ("part_low", "low", 0, 127, 0),
    ("part_high", "high", 0, 127, 127),
    ("part_level", "level", 0, 32768, 32768),
    ("part_delay", "delay", 0, 1000, 0),
)


def _routing_values(parts: Parts | None, field: str) -> list[int] | None:
    """The per-part routing array for `field`, or None when unset."""
    if parts is None:
        return None
    return cast(list[int] | None, parts.get(field))


def _build_params(
    instances: list[NodeInstance],
    manifest: Mapping[str, ParamBinding],
    n_parts: int,
    parts: Parts | None,
) -> list[ParamEntry]:
    """Flatten node params (per-part for the voice zone) + the routing params."""
    voice: list[tuple[str, str, int, str]] = []
    global_: list[tuple[str, str, int, str]] = []
    for i in instances:
        for pname, kind in i.spec.params.items():
            if kind == TABLE:
                continue  # a compile-time table selector, not a runtime param
            entry = (
                i.param_expr(pname),
                f"{i.id}.{pname}",
                param_default(kind, i.params.get(pname)),
                kind,
            )
            (voice if i.zone == "voice" else global_).append(entry)

    by_target: dict[str, str] = {}
    meta: dict[str, ParamBinding] = {}
    for name, spec in manifest.items():
        target = spec["target"]
        if target in by_target:
            raise GenError(
                f"params: {by_target[target]!r} and {name!r} both target {target!r}"
            )
        by_target[target] = name
        meta[target] = spec

    flat_targets = {target for _, target, _, _ in voice + global_}
    for target, name in by_target.items():
        if target not in flat_targets:
            raise GenError(f"params: {name!r} targets unknown param {target!r}")

    def add(
        cname: str,
        target: str,
        default: int,
        kind: str,
        name: str,
        part: int | None,
        m: ParamBinding | None,
    ) -> ParamEntry:
        lo, hi = param_bounds(kind)
        return ParamEntry(
            id=len(entries),
            name=name,
            target=target,
            cname=cname,
            part=part,
            min=m.get("min", lo) if m else lo,
            max=m.get("max", hi) if m else hi,
            default=default,
            curve=m.get("curve", "linear") if m else "linear",
            unit=m.get("unit", "") if m else "",
            rate=m.get("rate", "block") if m else "block",
            modulatable=m.get("modulatable", False) if m else False,
        )

    entries: list[ParamEntry] = []
    if n_parts > 1:
        for p in range(n_parts):
            for cname, target, default, kind in voice:
                base = by_target.get(target, target)
                entries.append(
                    add(
                        cname,
                        f"{target}.p{p}",
                        default,
                        kind,
                        f"{base}.p{p}",
                        p,
                        meta.get(target),
                    )
                )
    else:
        for cname, target, default, kind in voice:
            base = by_target.get(target, target)
            entries.append(
                add(cname, target, default, kind, base, None, meta.get(target))
            )

    for cname, target, default, kind in global_:
        base = by_target.get(target, target)
        entries.append(add(cname, target, default, kind, base, None, meta.get(target)))

    if n_parts > 1:
        for cname, field, lo, hi, fallback in _ROUTING_PARAMS:
            arr = _routing_values(parts, field)
            for p in range(n_parts):
                default = arr[p] if arr is not None and p < len(arr) else fallback
                entries.append(
                    ParamEntry(
                        id=len(entries),
                        name=f"{field}.p{p}",
                        target=f"part.{field}.p{p}",
                        cname=cname,
                        part=p,
                        min=lo,
                        max=hi,
                        default=default,
                        curve="linear",
                        unit="",
                        rate="block",
                        modulatable=False,
                    )
                )
    return entries


# --------------------------------------------------------------- expansion ---


def _expand(
    inst_dict: Instance,
    zone: str,
    nodes: Mapping[str, NodeSpec],
    macros: Mapping[str, Macro],
    instances: list[NodeInstance],
    raw_wires: list[tuple[str, str]],
    bindings: dict[tuple[str, str], tuple[str, str]],
) -> None:
    """Expand a node/macro instance into leaf instances, wires, and bindings."""
    type_ = inst_dict["type"]
    id_ = inst_dict["id"]
    if type_ not in macros:
        spec = nodes.get(type_)
        if spec is None:
            raise GenError(f"unknown node type {type_!r} (instance {id_!r})")
        params = _str_params(inst_dict.get("params"))
        table = None
        for pname, kind in spec.params.items():
            if kind == TABLE:
                table = params.pop(pname, None)
                if table is None:
                    raise GenError(
                        f"node {id_!r} (type {type_!r}) needs a table name "
                        f"(params: {{ {pname}: <name> }})"
                    )
        instances.append(
            NodeInstance(
                id=id_,
                type=type_,
                zone=zone,
                spec=spec,
                params=params,
                note_derived=dict(spec.note_derived),
                note_cutoff=dict(spec.note_cutoff),
                block_derived=dict(spec.block_derived),
                table=table,
            )
        )
        return

    macro = macros[type_]
    for inner in macro["nodes"]:
        child: Instance = {**inner, "id": f"{id_}.{inner['id']}"}
        _expand(
            child,
            zone,
            nodes,
            macros,
            instances,
            raw_wires,
            bindings,
        )

    for wire in macro["wires"]:
        frm, to = wire["from"], wire["to"]
        f_inner = _is_inner(frm, macro)
        t_inner = _is_inner(to, macro)
        if not f_inner and t_inner:
            bindings[(id_, frm)] = _inner_ref(to, id_)
        elif f_inner and not t_inner:
            bindings[(id_, to)] = _inner_ref(frm, id_)
        else:
            raw_wires.append((_prefix(frm, id_), _prefix(to, id_)))

    instance_params = _str_params(inst_dict.get("params"))
    for pname, target in macro.get("params", {}).items():
        target_str, note_kind = _parse_param_target(target)
        inner_id, field = target_str.split(".", 1)
        inst = _find(instances, f"{id_}.{inner_id}")
        if inst is None:
            raise GenError(f"macro param {pname!r} targets unknown node {inner_id!r}")
        value = instance_params.get(pname)
        if note_kind == "inc":
            # a note-derived ratio: map to the target node's ratio *param* (q16),
            # which note_on multiplies into the increment. The node declares it in
            # `note_derived` as `field -> param-name`.
            ratio_param = inst.spec.note_derived.get(field)
            if ratio_param is None:
                raise GenError(
                    f"macro param {pname!r} targets {inner_id}.{field}, which is "
                    f"not a note-derived ratio"
                )
            if value is not None:
                inst.params[ratio_param] = value
        elif note_kind == "cutoff":
            inst.note_cutoff[field] = value if value is not None else "1"
        elif value is not None:
            inst.params[field] = value


def _str_params(params: Mapping[str, int | str] | None) -> dict[str, str]:
    if not params:
        return {}
    return {k: str(v) for k, v in params.items()}


def _is_inner(port: str, macro: Macro) -> bool:
    first = port.split(".", 1)[0]
    return any(n["id"] == first for n in macro["nodes"])


def _inner_ref(port: str, prefix: str) -> tuple[str, str]:
    node_id, field = port.split(".", 1)
    return (f"{prefix}.{node_id}", field)


def _prefix(port: str, prefix: str) -> str:
    return f"{prefix}.{port}"


def _parse_param_target(target: str | ParamTarget) -> tuple[str, NoteKind | None]:
    """A macro param target: `'inner.field'`, `{target, note_derived}`, or
    `{target, note_cutoff}`. Returns (target, note-kind) where kind is
    `"inc"`, `"cutoff"`, or `None` (a plain param)."""
    if isinstance(target, str):
        return target, None
    if target.get("note_cutoff"):
        return target["target"], "cutoff"
    if target.get("note_derived"):
        return target["target"], "inc"
    return target["target"], None


def _find(instances: list[NodeInstance], id_: str) -> NodeInstance | None:
    for i in instances:
        if i.id == id_:
            return i
    return None


# --------------------------------------------------------------- resolution ---


def _resolve_ref(ref: str, bindings: Mapping[tuple[str, str], tuple[str, str]]) -> Port:
    """Resolve a wire reference through the macro port/state bindings."""
    node, port = _split(ref)
    while (node, port) in bindings:
        node, port = bindings[(node, port)]
    return Port(node, port)


def _split(ref: str) -> tuple[str, str]:
    if "." in ref:
        node, port = ref.rsplit(".", 1)
        return node, port
    return ref, ""


def _typecheck(
    edges: list[Edge],
    by_id: dict[str, NodeInstance],
    voice_out_ref: str | None,
    bindings: Mapping[tuple[str, str], tuple[str, str]],
) -> tuple[Port | None, Port | None]:
    """Type-check every edge, resolve inputs, and locate the zone boundaries."""
    global_out: Port | None = None
    for edge in edges:
        src, dst = edge.src, edge.dst
        if src.node == VOICE_SOURCE:
            dst_inst = by_id.get(dst.node)
            if dst_inst is not None:
                dst_inst.in_expr[dst.port] = "bus"
            continue
        if dst.node == OUT_SINK:
            global_out = src
            continue
        if src.node in RESERVED_INPUTS or dst.node in RESERVED_INPUTS:
            continue  # allocator binding, not a graph edge

        src_inst = by_id.get(src.node)
        dst_inst = by_id.get(dst.node)
        if src_inst is None or dst_inst is None:
            raise GenError(
                f"wire to/from unknown node: "
                f"{src.node}.{src.port} -> {dst.node}.{dst.port}"
            )
        src_port = src_inst.spec.outs.get(src.port)
        dst_port = dst_inst.spec.ins.get(dst.port)
        if src_port is None:
            raise GenError(f"{src.node} has no output port {src.port!r}")
        if dst_port is None:
            raise GenError(f"{dst.node} has no input port {dst.port!r}")
        _check_edge(src, dst, src_port, dst_port)
        dst_inst.in_expr[dst.port] = src_inst.out_local(src.port)
        src_inst.consumed.add(src.port)

    voice_out = _resolve_ref(voice_out_ref, bindings) if voice_out_ref else None
    for port in (voice_out, global_out):
        if port is not None and port.node in by_id:
            by_id[port.node].consumed.add(port.port)
    return voice_out, global_out


def _check_edge(src: Port, dst: Port, src_port: PortSpec, dst_port: PortSpec) -> None:
    """Enforce the port-kind + fixed-point-format rules (§12.4 pass 1)."""
    if src_port.kind == AUDIO and dst_port.kind == EVENT:
        raise GenError(
            f"type error: audio->event {src.node}.{src.port} -> {dst.node}.{dst.port}"
        )
    if src_port.kind != dst_port.kind and not (
        {src_port.kind, dst_port.kind} <= {AUDIO, CONTROL}
    ):
        raise GenError(
            f"type error: {src_port.kind}->{dst_port.kind} "
            f"{src.node}.{src.port} -> {dst.node}.{dst.port}"
        )
    if src_port.fmt and dst_port.fmt and src_port.fmt != dst_port.fmt:
        raise GenError(
            f"format mismatch: {src_port.fmt}->{dst_port.fmt} "
            f"{src.node}.{src.port} -> {dst.node}.{dst.port}"
        )


# --------------------------------------------------------------- topo sort ---


def _topo(zone_instances: list[NodeInstance], edges: list[Edge]) -> list[str]:
    """Topologically sort a zone; delay1/delayN are removed (read/write hoisted)."""
    ids = {i.id for i in zone_instances}
    breakers = {i.id for i in zone_instances if i.is_breaker()}
    deps: dict[str, set[str]] = {i.id: set() for i in zone_instances}
    for edge in edges:
        src, dst = edge.src.node, edge.dst.node
        if src not in ids or dst not in ids or src == dst:
            continue
        if src in breakers or dst in breakers:
            continue  # delay read (source) and write (sink) are hoisted
        deps[dst].add(src)

    order: list[str] = []
    ready = [i.id for i in zone_instances if not deps[i.id]]
    remaining = set(ids)
    while ready:
        node = ready.pop()
        if node in remaining:
            order.append(node)
            remaining.discard(node)
        for candidate in sorted(remaining):
            deps[candidate].discard(node)
            if (
                not deps[candidate]
                and candidate not in ready
                and candidate not in order
            ):
                ready.append(candidate)
    if remaining:
        raise GenError(f"cycle not broken by delay1/delayN: {sorted(remaining)}")
    return order
