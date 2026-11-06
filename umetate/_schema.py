# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The typed mirror of the JSON manifests (docs/roadmap.md §6.8, §12.4).

Every `*.schema.json` shape has a `TypedDict` here, the mypy mirror of the JSON
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
    ins: NotRequired[dict[str, str]]  # input port -> C expression override (zone-aware)


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
    """A patch `params:` entry: bind a friendly name to a flattened target.

    `display` is the value's on-screen form (the panel's per-param scale): `"raw"`
    (the integer), `"ratio"` (a Q16 frequency multiplier, `1.00` = base pitch),
    `"pct"` (0..100% of [min,max]), `"pct_inv"` (100..0%), `"onoff"` (off/on),
    `"off_pct"` (≤0 → "off", else %), `"hz"` (a Q32 rate as Hz), or `"semi"` (a
    bipolar Q15 as ±semitones), or `"wave"` (a 0..11 waveform index as its name).
    Absent = `"raw"`.
    """

    target: str
    min: NotRequired[int]
    max: NotRequired[int]
    default: NotRequired[int]
    curve: NotRequired[str]
    unit: NotRequired[str]
    rate: NotRequired[str]
    modulatable: NotRequired[bool]
    display: NotRequired[str]


class TableSpec(TypedDict):
    """A patch `tables:` entry."""

    kind: str
    shape: NotRequired[str]
    size: NotRequired[int]
    harmonics: NotRequired[list[int]]
    points: NotRequired[list[list[int]]]


class Parts(TypedDict):
    """A patch `parts:` section: N timbres, routing in parallel arrays (indexed by
    part). Chosen (over a list of per-part objects) so a future firmware can add an
    `engine: [...]` array and point different parts at different patch engines."""

    count: int
    channel: NotRequired[list[int]]  # MIDI channel per part, -1 = omni
    low: NotRequired[list[int]]  # keyzone low per part
    high: NotRequired[list[int]]  # keyzone high per part
    level: NotRequired[list[int]]  # q15 gain per part
    delay: NotRequired[list[int]]  # note-onset offset (ms) per part


# `global` is a Python keyword, so this one uses the functional form.
Patch = TypedDict(
    "Patch",
    {
        "name": str,
        "voices": int,
        "cpu0_voices": NotRequired[int],  # CPU0 split count (default voices//2)
        "sample_rate": NotRequired[int],
        "tables": NotRequired[dict[str, TableSpec]],
        "params": NotRequired[dict[str, ParamBinding]],
        "macros": NotRequired[dict[str, Macro]],
        "voice": NotRequired[Zone],
        "global": NotRequired[Zone],
        "parts": NotRequired[Parts],
        "model": NotRequired[int],  # the firmware's SysEx <model> byte (0-127)
        "cc": NotRequired[list[str]],  # the CC-exposed params (names); absent = all
        # scope taps: "<instance>.<port>" audio-rate voice-zone outputs, exposed
        # per-part as per-op scope/spectro channels (§6.11.4, L11).
        "taps": NotRequired[list[str]],
        # INIT PATCH/PART defaults: friendly name -> value (per-part params apply to
        # every part), emitted as the synth's init table (§6.11.4).
        "init": NotRequired[dict[str, int]],
    },
)


# ----------------------------------------------------------------- node ----


class PortDict(TypedDict):
    """A node.json port in object form: `{rate, format?, default?}`."""

    rate: str
    format: NotRequired[str]
    default: NotRequired[str]


class ParamSpec(TypedDict):
    """A node.json param in object form: `{kind, default?, modulatable?}`.

    `default` overrides the kind's default. `modulatable` (D23) gives the param a
    paired control input `<param>_mod` + a depth param `<param>_depth`; the effective
    value is base + mod·depth at block rate."""

    kind: str
    default: NotRequired[str]
    modulatable: NotRequired[bool]


class NodeManifest(TypedDict):
    """A shipped node's node.json."""

    name: str
    summary: NotRequired[str]
    ins: NotRequired[dict[str, str | PortDict]]
    outs: dict[str, str | PortDict]
    params: NotRequired[dict[str, str | ParamSpec]]
    state: NotRequired[dict[str, str]]
    note_derived: NotRequired[dict[str, str]]
    note_cutoff: NotRequired[dict[str, str]]
    note_reciprocal: NotRequired[dict[str, str]]
    note_tune: NotRequired[dict[str, list[str]]]
    block_derived: NotRequired[dict[str, str]]


# ---------------------------------------------------------------- panel ----


class Widget(TypedDict):
    type: str
    row: NotRequired[int]
    col: NotRequired[int]
    span: NotRequired[int]
    param: NotRequired[str]
    params: NotRequired[list[str]]
    text: NotRequired[str]
    unit: NotRequired[str]
    fmt: NotRequired[str]
    items: NotRequired[list[str]]
    channel: NotRequired[
        int
    ]  # scope/spectro: the op index (0..3) -> "op N of the active part"
    active: NotRequired[bool]  # scope/spectro: the *active* operator of the active part
    mix_part: NotRequired[int]  # scope/spectro: the part index (0..1) -> "part N mix"
    part: NotRequired[bool]  # subheader: 1 = "PART N", 0 = "OP N"
    plural: NotRequired[bool]  # subheader: drop the N ("OP" / "PART")
    plain: NotRequired[bool]  # subheader: no prefix at all (a global page)
    partop: NotRequired[bool]  # subheader: "PART N OP <text>"
    name: NotRequired[int]  # name row: the name index (0 = part, 1 = patch)


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
    part: NotRequired[
        bool
    ]  # resolve `target` through the active part (UI_BIND_PART_PARAM)


# `global` is a Python keyword, so this one uses the functional form.
PanelManifest = TypedDict(
    "PanelManifest",
    {
        "name": str,
        "boot": NotRequired[Page],
        "home": NotRequired[str],
        "global": NotRequired[list[PanelBinding]],
        "mute": NotRequired[list[str]],
        "operators": NotRequired[list[str]],
        "alg": NotRequired[str],  # the algorithm param name (the header readout)
        "parts": NotRequired[int],  # the part count (the header + part_next)
        "legend": NotRequired[str],  # the footer gesture legend (drawn at the bottom)
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
    display: str


class ParamsDoc(TypedDict):
    params: list[ParamDoc]


class SysexLayout(TypedDict):
    """The generated `sysex-layout.json` (roadmap §6.11.4): the per-firmware SysEx
    payload geometry, the firmware's `<model>` byte (the patch's `model`), the
    part-patch record's param count, the part count, and the record/bank sizes."""

    model: int
    n_params: int
    n_parts: int
    part_patch_size: int
    multi_patch_size: int
    settings_size: int
    part_patch_bank_size: int
    multi_patch_bank_size: int


class CcEntry(TypedDict):
    """One fixed `cc -> param` assignment (roadmap §6.11.4)."""

    cc: int
    param: int
    name: str


class CcMap(TypedDict):
    """The generated cc-map: one CC per param, ascending from `base`, skipping the
    reserved CCs (sustain 64 and the channel-mode 120..127)."""

    base: int
    entries: list[CcEntry]


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
    voices = obj.get("voices")
    if not isinstance(voices, int):
        raise ValueError("patch: 'voices' must be an integer")
    cpu0 = obj.get("cpu0_voices")
    if cpu0 is not None and (not isinstance(cpu0, int) or not 0 <= cpu0 <= voices):
        raise ValueError("patch: 'cpu0_voices' must be an integer in 0..voices")
    model = obj.get("model")
    if model is not None and (not isinstance(model, int) or not 0 <= model <= 0x7F):
        raise ValueError("patch: 'model' must be a byte in 0..127")
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
