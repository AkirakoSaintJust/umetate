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
    emit: Callable = None


# ---------------------------------------------------------------- nodes ---
# `inst.state_ref(name, v)` is zone-aware (SoA `name[v]` for voice, scalar for
# global); `inst.input(port, default)` is the resolved input expression.


def _phasor(inst, v):
    phase = inst.state_ref("phase", v)
    inc = inst.state_ref("inc", v)
    out = f"{inst.c}_phase_x"
    fm = inst.input("fm", "0")
    mod = inst.input("mod", "0")
    read = [f"uint32_t {out} = {phase} + {inc} + {fm} + {mod};",
            f"{phase} = {out};"]
    return {"phase": out}, read, []


def _osc(inst, v):
    out = f"{inst.c}_audio_x"
    phase = inst.input("phase", "0")
    read = [f"int32_t {out} = fm1_sin({phase});"]
    return {"audio": out}, read, []


def _vca(inst, v):
    out = f"{inst.c}_audio_x"
    audio = inst.input("audio", "0")
    cv = inst.input("cv", "32768")              # unity gain default
    read = [f"int32_t {out} = fm1_q15_mul({audio}, {cv});"]
    return {"audio": out}, read, []


def _mix(inst, v):
    out = f"{inst.c}_audio_x"
    terms = [inst.input(port, "0") for port in inst.spec.ins]
    read = [f"int32_t {out} = " + " + ".join(terms) + ";"]
    return {"audio": out}, read, []


def _delay1(inst, v):
    """1-sample delay: the register read is a source (ordered first), the write a
    sink (ordered last) — this breaks the FM feedback cycle at sample level."""
    out = f"{inst.c}_out_x"
    prev = inst.state_ref("prev", v)
    audio = inst.input("in", "0")
    read = [f"int32_t {out} = {prev};"]
    write = [f"{prev} = {audio};"]
    return {"out": out}, read, write


def _env(inst, v):
    """Linear attack/release envelope (q15). `gate` defaults to the allocator gate."""
    level = inst.state_ref("level", v)
    out = f"{inst.c}_cv_x"
    gate = inst.input("gate", f"voice_gate[{v}]")
    a = inst.param_expr("attack")
    r = inst.param_expr("release")
    read = [f"int32_t {out} = {level};",
            f"if ({gate}) {{ {level} += {a}; if ({level} > 32767) {level} = 32767; }}",
            f"else {{ {level} -= {r}; if ({level} < 0) {level} = 0; }}"]
    return {"cv": out}, read, []


def _one_pole(inst, v):
    """One-pole lowpass (q15)."""
    z = inst.state_ref("z1", v)
    out = f"{inst.c}_audio_x"
    audio = inst.input("audio", "0")
    f = inst.param_expr("cutoff")
    read = [f"int32_t {out} = {z} + fm1_q15_mul({f}, {audio} - {z});",
            f"{z} = {out};"]
    return {"audio": out}, read, []


def _delayN(inst, v):
    """Fixed-size ring-buffer delay with feedback (q15, pool buffer)."""
    buf = inst.state("buf")                     # the pool array (int16)
    idx = inst.state_ref("idx", v)
    out = f"{inst.c}_out_x"
    audio = inst.input("in", "0")
    fb = inst.param_expr("fb")
    mask = f"{inst.c}_delay_mask"
    read = [f"int32_t {out} = {buf}[{idx}];"]
    write = [f"{buf}[{idx}] = {audio} + fm1_q15_mul({out}, {fb});",
             f"{idx} = ({idx} + 1) & {mask};"]
    return {"out": out}, read, write


def _noise(inst, v):
    """White noise (xorshift LFSR)."""
    lfsr = inst.state_ref("lfsr", v)
    out = f"{inst.c}_audio_x"
    read = [f"{lfsr} ^= {lfsr} << 13; {lfsr} ^= {lfsr} >> 17; {lfsr} ^= {lfsr} << 5;",
            f"int32_t {out} = (int32_t)({lfsr} >> 8);"]
    return {"audio": out}, read, []


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
                       ins={"in": "audio"},
                       outs={"out": "audio"},
                       state={"prev": "q15"},
                       emit=_delay1),
    "env": NodeSpec("env",
                    ins={"gate": "event"},
                    outs={"cv": "control"},
                    params={"attack": "q16", "release": "q16"},
                    state={"level": "q15"},
                    emit=_env),
    "one_pole": NodeSpec("one_pole",
                         ins={"audio": "audio", "cut": "control"},
                         outs={"audio": "audio"},
                         params={"cutoff": "q15"},
                         state={"z1": "q15"},
                         emit=_one_pole),
    "delayN": NodeSpec("delayN",
                       ins={"in": "audio"},
                       outs={"out": "audio"},
                       params={"fb": "q15"},
                       state={"buf": "pool", "idx": "uint32"},
                       emit=_delayN),
    "noise": NodeSpec("noise",
                      ins={},
                      outs={"audio": "audio"},
                      state={"lfsr": "uint32"},
                      emit=_noise),
}
