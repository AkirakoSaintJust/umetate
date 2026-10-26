# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The generator's typed intermediate representation (docs/roadmap.md §12.4).

Everything the front-end produces and the back-end consumes, plus the node-library
loader. Pure data + pure functions; no side effects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

# ---- signal kinds (ports) ----
EVENT = "event"
CONTROL = "control"
AUDIO = "audio"

# ---- fixed-point formats (params/state/ports) ----
Q12 = "q12"
Q15 = "q15"
Q16 = "q16"
Q32 = "q32"
PHASE = "phase"
POOL = "pool"
INT16 = "int16"
INT32 = "int32"
UINT32 = "uint32"

# ---- the voice zone's reserved allocator inputs (bindings, not graph edges) ----
RESERVED_INPUTS = ("note", "gate", "velocity")

# ---- the zone-boundary markers ----
VOICE_SOURCE = "voice"  # a wire source naming the mixed voice bus
OUT_SINK = "out"  # a wire target naming the final output sample

CONTROL_BLOCK_DEFAULT = 32


class GenError(Exception):
    """A generation error carrying the reason; never a silent fallback."""


class Port(NamedTuple):
    """A (node, port) reference in a wire."""

    node: str
    port: str


class Edge(NamedTuple):
    """A directed wire src -> dst."""

    src: Port
    dst: Port


class PortSpec(NamedTuple):
    """A port's rate + optional fixed-point format + unconnected default (C expr)."""

    kind: str
    fmt: str | None = None
    default: str | None = None


@dataclass
class NodeSpec:
    """A compiled node.json manifest + its node.c body template (§12.5)."""

    name: str
    ins: dict[str, PortSpec] = field(default_factory=dict)
    outs: dict[str, PortSpec] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)  # param -> q-format
    state: dict[str, str] = field(default_factory=dict)  # state -> type (or "pool")
    body: str = ""  # the per-sample template


@dataclass
class NodeInstance:
    """A concrete node in a zone, with resolved inputs and note-derived state."""

    id: str  # patch id (dots), e.g. "carrier.ph"
    type: str  # the node/macro type name
    zone: str  # "voice" | "global"
    spec: NodeSpec
    params: dict[str, str] = field(default_factory=dict)
    in_expr: dict[str, str] = field(default_factory=dict, repr=False)
    note_derived: dict[str, str] | None = None  # state -> macro ratio (note-on)

    @property
    def c(self) -> str:
        """The C identifier: patch id with dots/hyphens -> underscores."""
        return to_c_identifier(self.id)

    def state_ref(self, name: str, v: str) -> str:
        """Zone-aware state access: SoA `name[v]` for voice, scalar for global."""
        return f"{self.c}_{name}[{v}]" if self.zone == "voice" else f"{self.c}_{name}"

    def param_expr(self, name: str) -> str:
        """The C name of a param's backing variable."""
        return f"{self.c}_{name}"

    def input(self, port: str, default: str = "0") -> str:
        """The resolved input expression for `port`, or `default` when unconnected."""
        return self.in_expr.get(port, default)

    def port_default(self, port: str) -> str:
        """The default C expression for an unconnected input port."""
        spec = self.spec.ins[port]
        return spec.default if spec.default is not None else "0"

    def is_audio_rate(self) -> bool:
        """A node is audio-rate if any port is audio; else control-rate (§12.4)."""
        return any(p.kind == AUDIO for p in self.spec.ins.values()) or any(
            p.kind == AUDIO for p in self.spec.outs.values()
        )

    def is_breaker(self) -> bool:
        """A delay node: its body carries the @@read@@/@@write@@ split."""
        return "@@read@@" in self.spec.body

    def out_local(self, port: str) -> str:
        """The C name of an output: a per-sample local (audio) or a held array."""
        if self.is_audio_rate():
            return f"{self.c}_{port}_x"
        return f"{self.c}_{port}_x[v]" if self.zone == "voice" else f"{self.c}_{port}_x"


@dataclass
class CompiledGraph:
    """The front-end's output: everything the back-end needs to emit C."""

    name: str
    voices: int
    instances: list[NodeInstance]
    voice_order: list[str]  # topo order of voice-zone instance ids
    global_order: list[str]  # topo order of global-zone instance ids
    voice_out: Port | None  # the voice-zone signal summed into the bus
    global_out: Port | None  # the global node feeding `out` (else the bus)
    control_block: int = CONTROL_BLOCK_DEFAULT


def to_c_identifier(name: str) -> str:
    """A patch/synth id (dots, hyphens) -> a C identifier (underscores)."""
    return name.replace(".", "_").replace("-", "_")


def load_library(root: str | Path) -> dict[str, NodeSpec]:
    """Load every `modules/<name>/node.json` + `node.c` into a NodeSpec map."""
    nodes: dict[str, NodeSpec] = {}
    for manifest_path in sorted(Path(root).glob("*/node.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        body_path = manifest_path.with_name("node.c")
        body = body_path.read_text(encoding="utf-8") if body_path.exists() else ""
        spec = node_spec_from_manifest(manifest, body)
        nodes[spec.name] = spec
    return nodes


def node_spec_from_manifest(manifest: dict[str, Any], body: str) -> NodeSpec:
    """Build a NodeSpec from a node.json dict + its node.c body."""
    name = str(manifest["name"])
    ins = {str(p): _parse_port(v) for p, v in dict(manifest.get("ins", {})).items()}
    outs = {str(p): _parse_port(v) for p, v in dict(manifest.get("outs", {})).items()}
    params = {str(k): str(v) for k, v in dict(manifest.get("params", {})).items()}
    state = {str(k): str(v) for k, v in dict(manifest.get("state", {})).items()}
    return NodeSpec(
        name=name, ins=ins, outs=outs, params=params, state=state, body=body
    )


def _parse_port(value: object) -> PortSpec:
    """Parse a node.json port: a bare kind or a `{rate, format, default}` object."""
    if isinstance(value, str):
        return PortSpec(value)
    if isinstance(value, dict):
        rate = str(value["rate"])
        fmt = value.get("format")
        default = value.get("default")
        return PortSpec(
            rate,
            str(fmt) if fmt is not None else None,
            str(default) if default is not None else None,
        )
    raise GenError(f"bad port spec: {value!r}")
