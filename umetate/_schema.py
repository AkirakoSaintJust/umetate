# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The typed mirror of the JSON manifests (docs/roadmap.md §6.8, §12.4).

Every `*.schema.json` shape has a `TypedDict` here — the mypy mirror of the JSON
Schema. The JSON boundary (a `json.loads` result) is narrowed to these via the
`as_*` loaders below: a single `isinstance` check on the required keys, then one
`cast`. The deeper per-field validation (unknown `kind`, unknown `source`, …) stays
in the consuming modules, which now operate on typed data.

No `Any` here, by design: this module is what lets `disallow_any_explicit` stay on.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, NotRequired, Protocol, TextIO, TypedDict, cast

# ---- the two note-derived binding kinds (a macro param target) ----
NoteKind = Literal["inc", "cutoff"]


# ---------------------------------------------------------------- patch ----

# `from` is a Python keyword, so this one uses the functional form.
Wire = TypedDict("Wire", {"from": str, "to": str})


class ParamTarget(TypedDict):
    """A macro param target: `{target, note_derived?, note_cutoff?}`."""

    target: str
    note_derived: NotRequired[bool]
    note_cutoff: NotRequired[bool]


class Instance(TypedDict):
    """A node/macro instance in a zone."""

    id: str
    type: str
    params: NotRequired[dict[str, int | str]]  # int = value, str = table selector


class Zone(TypedDict):
    """A `voice`/`global` zone."""

    nodes: list[Instance]
    wires: NotRequired[list[Wire]]
    voice_out: NotRequired[str]


class Macro(TypedDict):
    """A reusable subgraph (a patch's inline `macros:` entry, or a shipped macro)."""

    ins: dict[str, str]
    outs: dict[str, str]
    params: NotRequired[dict[str, str | ParamTarget]]  # macro param -> target
    nodes: list[Instance]
    wires: list[Wire]
    summary: NotRequired[str]


class ParamBinding(TypedDict):
    """A patch `params:` entry: bind a friendly name to a flattened target."""

    target: str
    min: NotRequired[int]
    max: NotRequired[int]
    default: NotRequired[int]
    curve: NotRequired[str]
    unit: NotRequired[str]
    rate: NotRequired[str]
    modulatable: NotRequired[bool]


class TableSpec(TypedDict):
    """A patch `tables:` entry."""

    kind: str
    shape: NotRequired[str]
    size: NotRequired[int]
    harmonics: NotRequired[list[int]]
    points: NotRequired[list[list[int]]]


# `global` is a Python keyword, so this one uses the functional form.
Patch = TypedDict(
    "Patch",
    {
        "name": str,
        "voices": int,
        "sample_rate": NotRequired[int],
        "tables": NotRequired[dict[str, TableSpec]],
        "params": NotRequired[dict[str, ParamBinding]],
        "macros": NotRequired[dict[str, Macro]],
        "voice": NotRequired[Zone],
        "global": NotRequired[Zone],
    },
)


# ----------------------------------------------------------------- node ----


class PortDict(TypedDict):
    """A node.json port in object form: `{rate, format?, default?}`."""

    rate: str
    format: NotRequired[str]
    default: NotRequired[str]


class NodeManifest(TypedDict):
    """A shipped node's node.json."""

    name: str
    summary: NotRequired[str]
    ins: NotRequired[dict[str, str | PortDict]]
    outs: dict[str, str | PortDict]
    params: NotRequired[dict[str, str]]
    state: NotRequired[dict[str, str]]
    note_derived: NotRequired[dict[str, str]]
    note_cutoff: NotRequired[dict[str, str]]
    note_reciprocal: NotRequired[dict[str, str]]


# ---------------------------------------------------------------- panel ----


class Widget(TypedDict):
    type: str
    row: NotRequired[int]
    col: NotRequired[int]
    span: NotRequired[int]
    param: NotRequired[str]
    text: NotRequired[str]
    unit: NotRequired[str]
    fmt: NotRequired[str]
    items: NotRequired[list[str]]


class Page(TypedDict):
    id: str
    title: NotRequired[str]
    widgets: NotRequired[list[Widget]]


class Context(TypedDict):
    pages: list[Page]
    bindings: NotRequired[list[PanelBinding]]
    on_enter: NotRequired[list[str]]
    on_exit: NotRequired[list[str]]


class PanelBinding(TypedDict):
    source: str
    target: NotRequired[str]
    action: NotRequired[str]
    arg: NotRequired[str]
    behavior: NotRequired[str]
    curve: NotRequired[str]
    slot: NotRequired[int]


# `global` is a Python keyword, so this one uses the functional form.
PanelManifest = TypedDict(
    "PanelManifest",
    {
        "name": str,
        "boot": NotRequired[Page],
        "home": NotRequired[str],
        "global": NotRequired[list[PanelBinding]],
        "mute": NotRequired[list[str]],
        "contexts": dict[str, Context],
    },
)


# ------------------------------------------------------------- env.lock ----


class Toolchain(TypedDict):
    linux: str
    windows: NotRequired[str]
    download: str
    linux_sha256: NotRequired[str]


class Sdk(TypedDict):
    source: str
    tag: str
    math: NotRequired[str]
    assets: dict[str, str]


class Emu(TypedDict):
    source: str
    commit: str
    packages: list[str]


class Lock(TypedDict):
    jieli_toolchain: Toolchain
    ac79_sdk: Sdk
    fm1_emu: Emu


# ------------------------------------------------------- evidence matrix ----


class EvidenceEntry(TypedDict):
    layer: str
    status: str
    detail: NotRequired[str]


class EvidenceMatrix(TypedDict):
    layers: list[EvidenceEntry]


# ------------------------------------------------------- generated params ----


class ParamDoc(TypedDict):
    """One entry of the generated `params.json` (params.schema.json)."""

    id: int
    name: str
    target: str
    min: int
    max: int
    default: int
    curve: str
    unit: str
    rate: str
    modulatable: bool


class ParamsDoc(TypedDict):
    params: list[ParamDoc]


# ------------------------------------------------- fm1tk strangler-fig ----


class Installer(Protocol):
    """The fm1_install.py surface the CLI touches (the one trusted boundary)."""

    LOADER_MARK: bytes

    def product_of(self, raw: bytes) -> str: ...
    def model_of(self, text: str) -> str: ...
    def deinterleave(self, raw: bytes) -> tuple[bytes, int]: ...
    def package_damage(self, image: bytes) -> str | None: ...

    def main(
        self,
        argv: list[str] | None,
        *,
        backend: object | None,
        out: TextIO,
        ask: Callable[[str], bool],
    ) -> int: ...

    ask_tty: Callable[[str], bool]


# ------------------------------------------------------- JSON boundary ----


def _obj(raw: object, what: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError(f"{what}: expected a JSON object, got {type(raw).__name__}")
    return cast(dict[str, object], raw)


def as_patch(raw: object) -> Patch:
    obj = _obj(raw, "patch")
    if not isinstance(obj.get("name"), str):
        raise ValueError("patch: 'name' must be a string")
    if not isinstance(obj.get("voices"), int):
        raise ValueError("patch: 'voices' must be an integer")
    return cast(Patch, obj)


def as_node_manifest(raw: object) -> NodeManifest:
    obj = _obj(raw, "node")
    if not isinstance(obj.get("name"), str):
        raise ValueError("node: 'name' must be a string")
    if not isinstance(obj.get("outs"), dict):
        raise ValueError("node: 'outs' must be an object")
    return cast(NodeManifest, obj)


def as_macro(raw: object) -> Macro:
    obj = _obj(raw, "macro")
    for key in ("ins", "outs", "nodes", "wires"):
        if not isinstance(obj.get(key), (dict, list)):
            raise ValueError(f"macro: '{key}' must be present")
    return cast(Macro, obj)


def as_panel(raw: object) -> PanelManifest:
    obj = _obj(raw, "panel")
    if not isinstance(obj.get("name"), str):
        raise ValueError("panel: 'name' must be a string")
    if not isinstance(obj.get("contexts"), dict):
        raise ValueError("panel: 'contexts' must be an object")
    return cast(PanelManifest, obj)


def as_lock(raw: object) -> Lock:
    obj = _obj(raw, "env.lock")
    for key in ("jieli_toolchain", "ac79_sdk", "fm1_emu"):
        if not isinstance(obj.get(key), dict):
            raise ValueError(f"env.lock: '{key}' must be an object")
    return cast(Lock, obj)


def as_evidence(raw: object) -> EvidenceMatrix:
    obj = _obj(raw, "evidence")
    if not isinstance(obj.get("layers"), list):
        raise ValueError("evidence: 'layers' must be a list")
    return cast(EvidenceMatrix, obj)
