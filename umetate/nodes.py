# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The shipped node library (docs/roadmap.md §12.5).

Each node is a NodeSpec: the manifest (ins/outs/params/state) plus a Python emitter
that produces the per-sample C body. The generator inlines these bodies into one
fused, monomorphic render.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class NodeSpec:
    name: str
    ins: dict[str, str] = field(default_factory=dict)     # port -> kind (event|control|audio)
    outs: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)  # param -> q-format
    state: dict[str, str] = field(default_factory=dict)   # state -> q-format
    # emit(inst, v) -> (dict[str,str] out-exprs, list[str] statements)
    emit: Callable = None


# ---------------------------------------------------------------- nodes ---
# `inst.c` is the C identifier, `inst.state(name)` the SoA array name, `v` the
# voice index, `inst.input(port, default)` the resolved input expression.


def _phasor(inst, v):
    phase = inst.state("phase")                 # SoA array name
    inc = inst.state("inc")
    out = f"{inst.c}_phase_x"                   # the output local (per-sample value)
    fm = inst.input("fm", "0")
    mod = inst.input("mod", "0")
    stmts = [f"uint32_t {out} = {phase}[{v}] + {inc}[{v}] + {fm} + {mod};",
             f"{phase}[{v}] = {out};"]
    return {"phase": out}, stmts


def _osc(inst, v):
    out = f"{inst.c}_audio_x"
    phase = inst.input("phase", "0")
    stmts = [f"int32_t {out} = fm1_sin({phase});"]
    return {"audio": out}, stmts


def _vca(inst, v):
    out = f"{inst.c}_audio_x"
    audio = inst.input("audio", "0")
    cv = inst.input("cv", "32768")              # unity gain default
    stmts = [f"int32_t {out} = fm1_q15_mul({audio}, {cv});"]
    return {"audio": out}, stmts


def _mix(inst, v):
    out = f"{inst.c}_audio_x"
    terms = [inst.input(port, "0") for port in inst.spec.ins]
    stmts = [f"int32_t {out} = " + " + ".join(terms) + ";"]
    return {"audio": out}, stmts


def _delay1(inst, v):
    out = f"{inst.c}_audio_x"
    prev = inst.state("prev")
    audio = inst.input("audio", "0")
    stmts = [f"int32_t {out} = {prev}[{v}];",
             f"{prev}[{v}] = {audio};"]
    return {"audio": out}, stmts


NODES: dict[str, NodeSpec] = {
    "phasor": NodeSpec("phasor",
                       ins={"mod": "control", "fm": "audio"},
                       outs={"phase": "audio"},
                       state={"inc": "q32", "phase": "phase"},
                       emit=_phasor),
    "osc": NodeSpec("osc",
                    ins={"phase": "audio"},
                    outs={"audio": "audio"},
                    params={"level": "q15"},
                    emit=_osc),
    "vca": NodeSpec("vca",
                    ins={"audio": "audio", "cv": "control"},
                    outs={"audio": "audio"},
                    params={"level": "q15"},
                    emit=_vca),
    "mix": NodeSpec("mix",
                    ins={"in0": "audio", "in1": "audio"},
                    outs={"audio": "audio"},
                    emit=_mix),
    "delay1": NodeSpec("delay1",
                       ins={"audio": "audio"},
                       outs={"audio": "audio"},
                       state={"prev": "q15"},
                       emit=_delay1),
}
