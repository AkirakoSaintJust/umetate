# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The generator's typed intermediate representation (docs/roadmap.md §12.4).

Everything the front-end produces and the back-end consumes, plus the node-library
loader. Pure data + pure functions; no side effects.
"""

from __future__ import annotations

import json
import re
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
TABLE = "table"  # a compile-time param naming a `tables:` entry (a string, not int)

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
    consumed: set[str] = field(
        default_factory=set, repr=False
    )  # output ports wired down-stream
    table: str | None = None  # the selected table name (a "table"-kind param)

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
class ParamEntry:
    """One flattened DSP param: set_param id, C backing name, and its binding.

    `name` is the manifest key when the patch's `params:` section binds this param,
    else its flattened `target` path (`<instance>.<param>`). Both resolve to `id`.
    """

    id: int
    name: str  # user-facing name (manifest key, else the target path)
    target: str  # "<instance>.<param>" (the flattened path)
    cname: str  # the C backing variable (e.g. "lp_cutoff")
    min: int
    max: int
    default: int  # the DSP initial value (from the node param)
    curve: str  # "linear" | "log"
    unit: str  # display unit ("" = none)
    rate: str  # "sample" | "block"
    modulatable: bool


@dataclass
class Table:
    """A `tables:` entry: a name + kind + its `const` XIP values (Q15 int16)."""

    name: str
    kind: str  # "wavetable" | "segments" | "spectrum" | "phase_map"
    size: int
    values: list[int]


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
    params: list[ParamEntry] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    control_block: int = CONTROL_BLOCK_DEFAULT


def to_c_identifier(name: str) -> str:
    """A patch/synth id (dots, hyphens) -> a C identifier (underscores).

    The result must be a valid C identifier; anything else is a `GenError` (never a
    silently-corrupt `.c`), so a crafted name cannot inject code into the output.
    """
    result = name.replace(".", "_").replace("-", "_")
    if not _IDENTIFIER_RE.fullmatch(result):
        raise GenError(f"{name!r} is not a valid C identifier")
    return result


_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def param_default(kind: str, value: str | None) -> int:
    """The DSP initial value for a param of `kind`, or an explicit integer override."""
    if value is not None:
        return int(value)
    return {
        "q12": 4096,
        "q15": 32768,
        "q16": 65536,
        "q32": 0,
        "phase": 0,
        "int16": 0,
        "int32": 0,
        "uint32": 0,
    }.get(kind, 0)


def param_bounds(kind: str) -> tuple[int, int]:
    """The [min, max] display range for a param's fixed-point kind."""
    return {
        "q12": (-4096, 4095),
        "q15": (-32768, 32767),
        "q16": (-65536, 65535),
        "q32": (0, 0x7FFFFFFF),
        "phase": (0, 0xFFFFFFFF),
        "int16": (-32768, 32767),
        "int32": (-0x80000000, 0x7FFFFFFF),
        "uint32": (0, 0xFFFFFFFF),
    }.get(kind, (0, 0x7FFFFFFF))


def load_library(root: str | Path) -> dict[str, NodeSpec]:
    """Load every `modules/nodes/<name>/node.json` + `node.c` into a NodeSpec map."""
    nodes: dict[str, NodeSpec] = {}
    for manifest_path in sorted(Path(root).glob("*/node.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        body_path = manifest_path.with_name("node.c")
        body = body_path.read_text(encoding="utf-8") if body_path.exists() else ""
        spec = node_spec_from_manifest(manifest, body)
        nodes[spec.name] = spec
    return nodes


def load_macros(root: str | Path) -> dict[str, dict[str, Any]]:
    """Load every `modules/macros/<name>/macro.json` into a name -> macro map.

    The macro's name is its directory name; the manifest is the same shape as a
    patch's inline `macros:` entry (`ins`/`outs`/`params`/`nodes`/`wires`), plus a
    `summary` for `umetate lib`.
    """
    macros: dict[str, dict[str, Any]] = {}
    for manifest_path in sorted(Path(root).glob("*/macro.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        macros[manifest_path.parent.name] = manifest
    return macros


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
