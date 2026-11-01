# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host tests for the generator (docs/roadmap.md §12.4 verification).

- the pocket-drone two-op FM example (op macro + delay1 feedback + global chain)
  must *compile* for host;
- a delay-free env/vca patch must render non-silent then silent (the seam contract);
- an `audio->event` edge must be rejected with a type error.
Run: python3 -m umetate.test_generate
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ._ir import AUDIO, GenError
from ._panel import generate_panel
from ._schema import Patch, as_panel, as_patch
from .generate import (
    generate,
    generate_dsp_header,
    generate_params,
    generate_tables,
    load_library,
    param_ids,
)

LIBRARY_ROOT = Path(__file__).resolve().parents[1] / "modules" / "nodes"

POCKET_DRONE: Patch = {
    "name": "pocket-drone",
    "voices": 8,
    "macros": {
        "op": {
            "ins": {"fm": "audio"},
            "outs": {"audio": "audio"},
            "params": {"ratio": {"target": "ph.inc", "note_derived": True}},
            "nodes": [
                {"id": "ph", "type": "phasor"},
                {"id": "osc", "type": "osc"},
                {"id": "env", "type": "env"},
                {"id": "vca", "type": "vca"},
            ],
            "wires": [
                {"from": "fm", "to": "ph.fm"},
                {"from": "ph.phase", "to": "osc.phase"},
                {"from": "osc.audio", "to": "vca.audio"},
                {"from": "env.cv", "to": "vca.cv"},
                {"from": "vca.audio", "to": "audio"},
            ],
        }
    },
    "voice": {
        "nodes": [
            {"id": "carrier", "type": "op", "params": {"ratio": 65536}},
            {"id": "mod", "type": "op", "params": {"ratio": 131072}},
            {"id": "d1", "type": "delay1"},
        ],
        "wires": [
            {"from": "mod.audio", "to": "carrier.fm"},
            {"from": "mod.audio", "to": "d1.in"},
            {"from": "d1.out", "to": "mod.fm"},
        ],
        "voice_out": "carrier.audio",
    },
    "global": {
        "nodes": [{"id": "lp", "type": "one_pole"}],
        "wires": [
            {"from": "voice", "to": "lp.audio"},
            {"from": "lp.audio", "to": "out"},
        ],
    },
}

SINE_ENV: Patch = {
    "name": "sine_env",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# phase_shape / phase_dist between the phasor and the osc (identity at d=v=0.5).
PHASE_SHAPE: Patch = {
    "name": "phase_shape_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "sh", "type": "phase_shape"},
            {"id": "osc", "type": "osc"},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "sh.phase"},
            {"from": "sh.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}

PHASE_DIST: Patch = {
    "name": "phase_dist_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "pd", "type": "phase_dist"},
            {"id": "osc", "type": "osc"},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "pd.phase"},
            {"from": "pd.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}


# the naive oscillator macro (tuned_phasor -> phase_dist PWM -> naive_osc table).
NAIVE_VCO: Patch = {
    "name": "naive_vco_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "vco", "type": "naive_vco", "params": {"shape": 3}},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "vco.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}


# `osc` with a non-sine waveform (6 = double half sine) — exercises fm1_sin_wave.
WAVEFORM: Patch = {
    "name": "waveform_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc", "params": {"waveform": 6}},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# `route4` (routing-matrix row, alg 7 additive = all carriers) + `mix4` — exercises
# the runtime-algorithm primitive and the 4-input sum.
ROUTE4_TEST: Patch = {
    "name": "route4_test",
    "voices": 4,
    "tables": {"routing": {"kind": "routing"}},
    "voice": {
        "nodes": [
            {"id": "ph1", "type": "phasor"},
            {"id": "ph2", "type": "phasor"},
            {"id": "o1", "type": "osc"},
            {"id": "o2", "type": "osc"},
            {
                "id": "rt",
                "type": "route4",
                "params": {"which": "routing", "algorithm": 7, "dest": 4},
            },
            {"id": "mx", "type": "mix4"},
        ],
        "wires": [
            {"from": "ph1.phase", "to": "o1.phase"},
            {"from": "ph2.phase", "to": "o2.phase"},
            {"from": "o1.audio", "to": "rt.a"},
            {"from": "o2.audio", "to": "rt.b"},
            {"from": "rt.audio", "to": "mx.in0"},
            {"from": "o1.audio", "to": "mx.in1"},
        ],
        "voice_out": "mx.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the `lfo` node: a free-running control-rate sine, wired straight to the output so
# the non-silent contract proves it oscillates (not a constant).
LFO_TEST: Patch = {
    "name": "lfo_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {"id": "lf", "type": "lfo", "params": {"rate": 9739155, "depth": 32767}}
        ],
        "wires": [],
        "voice_out": "lf.cv",
    },
    "global": {"nodes": [], "wires": []},
}

# the `mute` node: an oscillator gated by a runtime `mute` param (0 = pass, 1 = 0).
MUTE_TEST: Patch = {
    "name": "mute_test",
    "voices": 1,
    "params": {"m": {"target": "g.mute", "min": 0, "max": 1, "curve": "linear"}},
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
            {"id": "g", "type": "mute"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "g.audio"},
        ],
        "voice_out": "g.audio",
    },
    "global": {"nodes": [], "wires": []},
}

SVF_WF: Patch = {
    "name": "svf_wf",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
            {"id": "flt", "type": "svf", "params": {"f": 10000, "q": 4000}},
            {"id": "fold", "type": "wavefolder", "params": {"amount": 8000}},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "flt.audio"},
            {"from": "flt.low", "to": "fold.audio"},
            {"from": "fold.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# uses the *shipped* fm_op macro (modules/macros), no inline macros: section.
FM_OP: Patch = {
    "name": "fm_op_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "carrier", "type": "fm_op", "params": {"ratio": 65536}},
            {"id": "mod", "type": "fm_op", "params": {"ratio": 131072}},
        ],
        "wires": [{"from": "mod.audio", "to": "carrier.fm"}],
        "voice_out": "carrier.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# The phase-modulation contract. A rectified sine has a large DC mean: under PM the
# carrier's *frequency* is unchanged (the DC is a constant phase offset); under the
# old accumulating-FM phasor it detuned the carrier by the mean. The flat envelope
# (l1=l2=l3, zero decay) keeps the test about the oscillator, not the EG.
_PM_ENV: dict[str, int] = {
    "r1": 99,
    "r2": 0,
    "r3": 0,
    "r4": 99,
    "l1": 99,
    "l2": 99,
    "l3": 99,
}
PM_DC_MOD: Patch = {
    "name": "pm_dc_mod",
    "voices": 2,
    "voice": {
        "nodes": [
            {
                "id": "carrier",
                "type": "fm_op",
                "params": {"ratio": 65536, "level": 99, "feedback": 0, **_PM_ENV},
            },
            {
                "id": "mod",
                "type": "fm_op",
                "params": {
                    "ratio": 32768,
                    "waveform": 8,  # rectified sine: nonzero mean
                    "level": 85,
                    "feedback": 0,
                    **_PM_ENV,
                },
            },
        ],
        "wires": [{"from": "mod.audio", "to": "carrier.fm"}],
        "voice_out": "carrier.audio",
    },
    "global": {"nodes": [], "wires": []},
}
PM_FEEDBACK: Patch = {
    "name": "pm_feedback",
    "voices": 2,
    "voice": {
        "nodes": [
            {
                "id": "carrier",
                "type": "fm_op",
                "params": {"ratio": 65536, "level": 99, "feedback": 8000, **_PM_ENV},
            }
        ],
        "wires": [],
        "voice_out": "carrier.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# A single operator with a non-instant release rate (r4 = 60), for the note-off
# release-tail contract: releasing a key must keep sounding then decay to silence.
RELEASE_PATCH: Patch = {
    "name": "release_test",
    "voices": 1,
    "voice": {
        "nodes": [{"id": "op", "type": "fm_op", "params": {"ratio": 65536, "r4": 60}}],
        "wires": [],
        "voice_out": "op.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# A single operator with a per-note pitch envelope wired into its pitch. With
# `on` = 1 and a +1-octave sustain (l1 = l2 = l3 = 32768), the carrier's
# frequency doubles; with `on` = 0 the pitch envelope contributes nothing.
_PENV: dict[str, int] = {
    "r1": 99,
    "r2": 0,
    "r3": 0,
    "r4": 99,
    "l1": 32768,
    "l2": 32768,
    "l3": 32768,
}


def _penv_patch(on: int) -> Patch:
    return {
        "name": "penv_test",
        "voices": 1,
        "voice": {
            "nodes": [
                {"id": "op", "type": "fm_op", "params": {"ratio": 65536}},
                {"id": "penv", "type": "pitch_env", "params": {**_PENV, "on": on}},
            ],
            "wires": [{"from": "penv.cv", "to": "op.pitch"}],
            "voice_out": "op.audio",
        },
        "global": {"nodes": [], "wires": []},
    }


LPG_TEST: Patch = {
    "name": "lpg_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
            {"id": "lg", "type": "lpg", "params": {"release": 65536}},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "lg.audio"},
        ],
        "voice_out": "lg.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the `dx_env` rate/level envelope (attack/decay1/decay2/sustain/release) driving a
# VCA — non-silent while gated, then release to silence.
DX_ENV: Patch = {
    "name": "dx_env_test",
    "voices": 4,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
            {
                "id": "eg",
                "type": "dx_env",
                "params": {
                    "r1": 80,
                    "r2": 60,
                    "r3": 50,
                    "r4": 80,
                    "l1": 99,
                    "l2": 93,
                    "l3": 87,
                },
            },
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "eg.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the `table` node reading a square wavetable + an IFFT spectrum, linked with
# tables.c (the `table` node is what makes `tables:` shapes actually audible).
TABLE_OSC: Patch = {
    "name": "table_osc",
    "voices": 4,
    "tables": {
        "sq": {"kind": "wavetable", "shape": "square"},
        "add": {"kind": "spectrum", "harmonics": [32767, 16000, 8000, 4000]},
    },
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "table", "params": {"which": "add"}},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the mip-mapped band-limited `osc` table: a phasor drives the square (waveform
# 10); the phasor's `mip` selects the level whose top harmonic sits below Nyquist,
# so a high note drops the odd harmonics that would otherwise fold back and alias.
OSC_TABLE_BL: Patch = {
    "name": "osc_table_bl",
    "voices": 1,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc", "params": {"waveform": 10}},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "ph.mip", "to": "osc.mip"},
        ],
        "voice_out": "osc.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the `saw` node uses the note-on reciprocal (inv_inc = 2^32/inc) via an inline
# macro that sets the note-derived `inc`.
SAW_TEST: Patch = {
    "name": "saw_test",
    "voices": 4,
    "macros": {
        "sawop": {
            "ins": {"fm": "audio"},
            "outs": {"audio": "audio"},
            "params": {"ratio": {"target": "osc.inc", "note_derived": True}},
            "nodes": [{"id": "osc", "type": "saw"}],
            "wires": [
                {"from": "fm", "to": "osc.fm"},
                {"from": "osc.audio", "to": "audio"},
            ],
        }
    },
    "voice": {
        "nodes": [{"id": "carrier", "type": "sawop", "params": {"ratio": 65536}}],
        "wires": [],
        "voice_out": "carrier.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the band-limited pulse (square at width 0.5) and triangle, for spectral
# anti-aliasing contracts (same note-derived `inc` shape as SAW_TEST).
PULSE_TEST: Patch = {
    "name": "pulse_test",
    "voices": 4,
    "macros": {
        "op": {
            "ins": {"fm": "audio"},
            "outs": {"audio": "audio"},
            "params": {"ratio": {"target": "osc.inc", "note_derived": True}},
            "nodes": [{"id": "osc", "type": "pulse"}],
            "wires": [
                {"from": "fm", "to": "osc.fm"},
                {"from": "osc.audio", "to": "audio"},
            ],
        }
    },
    "voice": {
        "nodes": [{"id": "carrier", "type": "op", "params": {"ratio": 65536}}],
        "wires": [],
        "voice_out": "carrier.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# D23 modulation: a modulatable param gets a wired `<param>_mod` control input + a
# `<param>_depth` param (effective value = base + mod·depth at block rate). `width`
# on the band-limited `pulse` is modulatable; an LFO wired to `osc.width_mod` sweeps
# the duty when `width_depth` is non-zero (and is inert when it is zero).
MOD_PULSE_TEST: Patch = {
    "name": "mod_pulse_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {"id": "osc", "type": "pulse"},
            {"id": "lfo", "type": "lfo", "params": {"rate": 4194304, "depth": 32767}},
        ],
        "wires": [{"from": "lfo.cv", "to": "osc.width_mod"}],
        "voice_out": "osc.audio",
    },
    "global": {"nodes": [], "wires": []},
}

TRIANGLE_TEST: Patch = {
    "name": "triangle_test",
    "voices": 4,
    "macros": {
        "op": {
            "ins": {"fm": "audio"},
            "outs": {"audio": "audio"},
            "params": {"ratio": {"target": "osc.inc", "note_derived": True}},
            "nodes": [{"id": "osc", "type": "triangle"}],
            "wires": [
                {"from": "fm", "to": "osc.fm"},
                {"from": "osc.audio", "to": "audio"},
            ],
        }
    },
    "voice": {
        "nodes": [{"id": "carrier", "type": "op", "params": {"ratio": 65536}}],
        "wires": [],
        "voice_out": "carrier.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# the `pitched_noise` macro uses the note-derived cutoff (f = 2*sin(pi*f_note/fs)).
PITCHED_NOISE: Patch = {
    "name": "pn_test",
    "voices": 4,
    "voice": {
        "nodes": [{"id": "pn", "type": "pitched_noise"}],
        "wires": [],
        "voice_out": "pn.audio",
    },
    "global": {"nodes": [], "wires": []},
}

TABLE_DEMO: Patch = {
    "name": "table_demo",
    "voices": 4,
    "tables": {
        "sine": {"kind": "wavetable", "size": 256, "shape": "sine"},
        "adsr": {"kind": "segments"},
        "spec": {"kind": "spectrum", "harmonics": [32767, 16000, 8000, 4000]},
    },
    "params": {
        "cutoff": {
            "target": "lp.cutoff",
            "min": 0,
            "max": 127,
            "default": 64,
            "unit": "Hz",
            "curve": "log",
        }
    },
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
            {"id": "env", "type": "env"},
            {"id": "vca", "type": "vca"},
        ],
        "wires": [
            {"from": "ph.phase", "to": "osc.phase"},
            {"from": "osc.audio", "to": "vca.audio"},
            {"from": "env.cv", "to": "vca.cv"},
        ],
        "voice_out": "vca.audio",
    },
    "global": {
        "nodes": [{"id": "lp", "type": "one_pole"}],
        "wires": [
            {"from": "voice", "to": "lp.audio"},
            {"from": "lp.audio", "to": "out"},
        ],
    },
}

SOUND_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
void __NAME___dsp_all_notes_off(void);
static int32_t out[1024];
int main(void) {
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, 100);
    __NAME___dsp_render(out, 512);
    int64_t e = 0; for (int i = 0; i < 1024; i++) e += (int64_t)out[i] * out[i];
    if (e < 1000000) { printf("FAIL: silent\\n"); return 1; }
    __NAME___dsp_all_notes_off();
    __NAME___dsp_render(out, 512);
    int64_t t = 0; for (int i = 0; i < 1024; i++) t += (int64_t)out[i] * out[i];
    if (t != 0) {
        printf("FAIL: not silent after off (tail=%lld)\\n", (long long)t);
        return 1;
    }
    printf("ok: __NAME__ renders non-silent then silent\\n");
    return 0;
}
"""

# A patch with a post-voice IIR stage (e.g. a global filter) rings down and settles
# into a sub-LSB limit cycle after note-off, so it never reaches *exactly* zero. This
# contract verifies the operators gate: non-silent while held, then the tail decays
# to below -60 dBFS after a full release window.
DECAY_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
void __NAME___dsp_all_notes_off(void);
static int32_t out[4096];
int main(void) {
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, 100);
    __NAME___dsp_render(out, 512);
    int64_t e = 0; for (int i = 0; i < 1024; i++) e += (int64_t)out[i] * out[i];
    if (e < 1000000) { printf("FAIL: silent\\n"); return 1; }
    __NAME___dsp_all_notes_off();
    __NAME___dsp_render(out, 2048);
    int64_t t = 0; for (int i = 3072; i < 4096; i++) t += (int64_t)out[i] * out[i];
    if (t > 1000000) {
        printf("FAIL: did not decay after off (tail=%lld)\\n", (long long)t);
        return 1;
    }
    printf("ok: __NAME__ renders non-silent then decays to near-silence\\n");
    return 0;
}
"""

# The runtime-algorithm contract: set `algorithm` to each of the 8 routings via
# set_param and confirm each renders non-silent (the `route` node's whole point).
ALGO_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
void __NAME___dsp_all_notes_off(void);
static int32_t out[512];
int main(void) {
    for (uint32_t alg = 0; alg < 8; alg++) {
        __NAME___dsp_reset();
        __NAME___dsp_set_param(__ALGO_ID__, (int32_t)alg);
        __NAME___dsp_note_on(69, 100);
        __NAME___dsp_render(out, 256);
        int64_t e = 0; for (int i = 0; i < 512; i++) e += (int64_t)out[i] * out[i];
        if (e < 1000000) { printf("FAIL: algorithm %u silent\\n", alg); return 1; }
        __NAME___dsp_all_notes_off();
    }
    printf("ok: __NAME__ renders non-silent across all 8 algorithms\\n");
    return 0;
}
"""

DUMP_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
static int32_t out[4096];
int main(void) {
    __NAME___dsp_note_on(69, 100);
    __NAME___dsp_render(out, 2048);
    for (int i = 0; i < 2048; i++) printf("%d\\n", out[2 * i]);   /* left channel */
    return 0;
}
"""

# The velocity contract: with a non-zero `vel_amp`, a high-velocity note must be
# louder than a low-velocity one (the `velocity` reserved input → the operator vca).
VEL_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
void __NAME___dsp_all_notes_off(void);
static int32_t out[1024];
static int64_t energy(uint32_t vel) {
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, vel);
    __NAME___dsp_render(out, 512);
    int64_t e = 0;
    for (int i = 0; i < 1024; i++) e += (int64_t)out[i] * out[i];
    __NAME___dsp_all_notes_off();
    return e;
}
int main(void) {
    int64_t hi = energy(127), lo = energy(1);
    if (hi <= 2 * lo) {
        printf("FAIL: velocity did not scale amplitude (hi=%lld lo=%lld)\\n",
               (long long)hi, (long long)lo);
        return 1;
    }
    printf("ok: __NAME__ velocity scales amplitude\\n");
    return 0;
}
"""

# A single fm_op operator with full velocity→amplitude (vel_amp = 32767), for the
# velocity contract.
VEL_PATCH: Patch = {
    "name": "vel_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {"id": "op", "type": "fm_op", "params": {"ratio": 65536, "vel_amp": 32767}},
        ],
        "wires": [],
        "voice_out": "op.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# The velocity→rate contract: with vel_rate full and vel_amp zero, a high-velocity
# note attacks faster, so it is louder during the attack window. Run one velocity
# per process (the engine's per-voice envelope/phase are static and shared across
# `note_on` calls in a single process).
VEL_RATE_HARNESS = """\
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
static int32_t out[256];
int main(int argc, char **argv) {
    uint32_t vel = (uint32_t)atoi(argv[1]);
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, vel);
    __NAME___dsp_render(out, 128);
    int64_t e = 0;
    for (int i = 0; i < 256; i++) e += (int64_t)out[i] * out[i];
    printf("%lld\\n", (long long)e);
    return 0;
}
"""

# A single fm_op operator with full velocity→rate (vel_rate = 32767, vel_amp = 0)
# and a non-instant attack (r1 = 20000), so the rate scaling is visible.
VEL_RATE_PATCH: Patch = {
    "name": "vel_rate_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {
                "id": "op",
                "type": "fm_op",
                "params": {"ratio": 65536, "vel_rate": 32767, "r1": 60, "l1": 99},
            },
        ],
        "wires": [],
        "voice_out": "op.audio",
    },
    "global": {"nodes": [], "wires": []},
}

# The retrigger contract: a note-on that *steals* a sounding voice must reset that
# voice's envelope to attack (not continue the old note's envelope). Compare, for
# the *same* note 72, a fresh attack ("fresh") against an attack after a steal
# ("steal", note 60 first): with retrigger the two energies match; without it the
# stolen note rides the old note's raised envelope and is much louder. One process
# per mode (the engine's per-voice envelope/phase are static and shared).
RETRIG_HARNESS = """\
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
static int32_t out[1024];
int main(int argc, char **argv) {
    int steal = argc > 1 && strcmp(argv[1], "steal") == 0;
    __NAME___dsp_reset();
    if (steal) { __NAME___dsp_note_on(60, 100); __NAME___dsp_render(out, 256); }
    __NAME___dsp_note_on(72, 100);
    __NAME___dsp_render(out, 256);
    int64_t e = 0;
    for (int i = 0; i < 512; i++) e += (int64_t)out[i] * out[i];
    printf("%lld\\n", (long long)e);
    return 0;
}
"""

RETRIG_PATCH: Patch = {
    "name": "retrig_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {
                "id": "op",
                "type": "fm_op",
                "params": {"ratio": 65536, "r1": 45, "l1": 99},
            },
        ],
        "wires": [],
        "voice_out": "op.audio",
    },
    "global": {"nodes": [], "wires": []},
}


# The voice-mode contracts: mono (one voice, last-note priority + note_off
# takeover) and unison (a note consumes `unison_count` voices, so a second note
# steals the whole stack). Observed through `dsp_lit` (the gated-note bitmask).
MODE_PATCH: Patch = {
    "name": "mode_test",
    "voices": 2,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
        ],
        "wires": [{"from": "ph.phase", "to": "osc.phase"}],
        "voice_out": "osc.audio",
    },
    "global": {"nodes": [], "wires": []},
}

MODE_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_note_off(uint32_t note);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
uint32_t __NAME___dsp_lit(uint32_t base);
int main(void) {
    /* mono: one voice, last-note priority, note_off takeover */
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__MODE_ID__, 1);
    __NAME___dsp_note_on(60, 100);
    __NAME___dsp_note_on(62, 100);
    __NAME___dsp_note_on(64, 100);
    uint32_t lit = __NAME___dsp_lit(60);
    if (lit != (1u << 4)) {
        printf("FAIL: mono last priority (lit=%u)\\n", lit);
        return 1;
    }
    __NAME___dsp_note_off(64);
    lit = __NAME___dsp_lit(60);
    if (lit != (1u << 2)) {
        printf("FAIL: mono takeover to 62 (lit=%u)\\n", lit);
        return 1;
    }
    __NAME___dsp_note_off(62);
    lit = __NAME___dsp_lit(60);
    if (lit != (1u << 0)) {
        printf("FAIL: mono takeover to 60 (lit=%u)\\n", lit);
        return 1;
    }

    /* unison count=2 on a 2-voice patch: a second note steals the whole stack */
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__MODE_ID__, 2);
    __NAME___dsp_set_param(__UNISON_COUNT_ID__, 2);
    __NAME___dsp_note_on(60, 100);
    __NAME___dsp_note_on(72, 100);
    lit = __NAME___dsp_lit(60);
    if (lit != (1u << 12)) {
        printf("FAIL: unison did not stack (lit=%u)\\n", lit);
        return 1;
    }

    printf("ok: __NAME__ mono priority/takeover + unison stacking\\n");
    return 0;
}
"""

# The legato contract: in mono, an overlapping note must NOT retrigger the
# envelope when legato is on (the envelope keeps running), but MUST when off.
# One process per legato value (the engine's static envelope/phase are shared).
LEGATO_PATCH: Patch = {
    "name": "legato_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {
                "id": "op",
                "type": "fm_op",
                "params": {"ratio": 65536, "r1": 45, "l1": 99},
            },
        ],
        "wires": [],
        "voice_out": "op.audio",
    },
    "global": {"nodes": [], "wires": []},
}

LEGATO_HARNESS = """\
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
static int32_t out[1024];
int main(int argc, char **argv) {
    int legato = atoi(argv[1]);
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__MODE_ID__, 1);
    __NAME___dsp_set_param(__LEGATO_ID__, legato);
    __NAME___dsp_note_on(60, 100);
    __NAME___dsp_render(out, 256);       /* the attack is underway */
    __NAME___dsp_note_on(64, 100);       /* overlap: retrigger iff legato is off */
    __NAME___dsp_render(out, 256);
    int64_t e = 0;
    for (int i = 0; i < 512; i++) e += (int64_t)out[i] * out[i];
    printf("%lld\\n", (long long)e);
    return 0;
}
"""

# The portamento contract: a note change glides the pitch (constant rate) instead
# of snapping. A single-voice sine steers from note 60 to note 72; with glide the
# average frequency over the window stays near 60 (few zero crossings), without it
# the window is all note 72 (roughly twice the crossings). One process per
# portamento value (the engine's static phase is shared).
GLIDE_PATCH: Patch = {
    "name": "glide_test",
    "voices": 1,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
        ],
        "wires": [{"from": "ph.phase", "to": "osc.phase"}],
        "voice_out": "osc.audio",
    },
    "global": {"nodes": [], "wires": []},
}

GLIDE_HARNESS = """\
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
static int32_t out[2048];
int main(int argc, char **argv) {
    int portamento = atoi(argv[1]);
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__PORTAMENTO_ID__, portamento);
    __NAME___dsp_note_on(60, 100);
    __NAME___dsp_render(out, 256);       /* settle at note 60 */
    __NAME___dsp_note_on(72, 100);       /* steal -> snap or glide to 72 */
    __NAME___dsp_render(out, 1024);
    int c = 0;                           /* positive-going zero crossings */
    for (int i = 0; i + 1 < 1024; i++)
        if (out[2 * i] < 0 && out[2 * (i + 1)] >= 0) c++;
    printf("%d\\n", c);
    return 0;
}
"""

# The multitimbral contract: `parts:` routes a note by channel+keyzone and layers
# (a note fires every matching part). A 2-part patch (part 0 = ch 0, part 1 = ch 1)
# makes `note_on_ch(60, vel, omni)` fire both parts (two stacked voices → ~4× the
# single-part energy) while `note_on_ch(60, vel, 0)` fires only part 0.
PARTS_PATCH: Patch = {
    "name": "parts_test",
    "voices": 4,
    "parts": {
        "count": 2,
        "channel": [0, 1],
        "low": [0, 0],
        "high": [127, 127],
    },
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
        ],
        "wires": [{"from": "ph.phase", "to": "osc.phase"}],
        "voice_out": "osc.audio",
    },
    "global": {"nodes": [], "wires": []},
}

PARTS_HARNESS = """\
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
static int32_t out[512];
int main(int argc, char **argv) {
    uint32_t ch = strcmp(argv[1], "omni") == 0 ? 0xFFFFFFFFu : 0u;
    __NAME___dsp_reset();
    __NAME___dsp_note_on_ch(60, 100, ch);
    __NAME___dsp_render(out, 256);
    int64_t e = 0;
    for (int i = 0; i < 512; i++) e += (int64_t)out[i] * out[i];
    printf("%lld\\n", (long long)e);
    return 0;
}
"""

# Per-part `level` (gain) and `delay` (onset offset): part 0 silent on channel 0
# (level 0) but loud on channel 1; a part-0 note delayed 100 ms is silent over its
# first 256 samples (still pending).
LEVEL_DELAY_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
static int32_t out[512];
static int64_t energy(void) {
    int64_t e = 0;
    for (int i = 0; i < 512; i++) e += (int64_t)out[i] * out[i];
    return e;
}
int main(void) {
    /* delay: part 0 delayed 100 ms -> the first 256 samples are silent */
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__DELAY_P0_ID__, 100);
    __NAME___dsp_note_on_ch(60, 100, 0u);
    __NAME___dsp_render(out, 256);
    if (energy() != 0) { printf("FAIL: per-part delay not silent\\n"); return 1; }

    /* level: part 0 silent -> channel 0 quiet, channel 1 (part 1) loud */
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__DELAY_P0_ID__, 0);
    __NAME___dsp_set_param(__LEVEL_P0_ID__, 0);
    __NAME___dsp_note_on_ch(60, 100, 0u);
    __NAME___dsp_render(out, 256);
    int64_t lvl0 = energy();
    __NAME___dsp_reset();
    __NAME___dsp_note_on_ch(60, 100, 1u);
    __NAME___dsp_render(out, 256);
    int64_t lvl1 = energy();
    if (lvl0 >= lvl1 / 100) {
        printf("FAIL: per-part level (ch0=%lld ch1=%lld)\\n",
               (long long)lvl0, (long long)lvl1);
        return 1;
    }
    printf("ok: __NAME__ per-part level + delay\\n");
    return 0;
}
"""

# The per-part voice-mode contract: the six mode params are per-part, so part 0
# (mono) and part 1 (poly) allocate independently. Part 0's mono priority is
# last-note; note_off takes over to the previous held note. Observed through
# `dsp_lit` (the gated-note bitmask in a 27-note window).
PARTS_MODE_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel);
void __NAME___dsp_note_off(uint32_t note);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
uint32_t __NAME___dsp_lit(uint32_t base);
int main(void) {
    /* part 0 mono (last-note priority), part 1 poly */
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__MODE_P0_ID__, 1);
    __NAME___dsp_set_param(__MODE_P1_ID__, 0);
    __NAME___dsp_note_on_ch(60, 100, 0u);
    __NAME___dsp_note_on_ch(62, 100, 0u);
    __NAME___dsp_note_on_ch(64, 100, 0u);
    __NAME___dsp_note_on_ch(70, 100, 1u);
    __NAME___dsp_note_on_ch(72, 100, 1u);
    uint32_t lit = __NAME___dsp_lit(60);
    /* part 0: only note 64 (bit 4); part 1: 70 + 72 (bits 10, 12) */
    if (lit != ((1u << 4) | (1u << 10) | (1u << 12))) {
        printf("FAIL: per-part mono/poly isolation (lit=%u)\\n", lit);
        return 1;
    }
    __NAME___dsp_note_off(64);
    lit = __NAME___dsp_lit(60);
    /* part 0 mono takeover to 62 (bit 2); part 1 unchanged */
    if (lit != ((1u << 2) | (1u << 10) | (1u << 12))) {
        printf("FAIL: per-part mono takeover (lit=%u)\\n", lit);
        return 1;
    }

    /* part 1 unison (count 2): the third stack steals the oldest stack */
    __NAME___dsp_reset();
    __NAME___dsp_set_param(__MODE_P1_ID__, 2);
    __NAME___dsp_set_param(__UNISON_COUNT_P1_ID__, 2);
    __NAME___dsp_note_on_ch(60, 100, 1u);
    __NAME___dsp_note_on_ch(72, 100, 1u);
    __NAME___dsp_note_on_ch(84, 100, 1u);
    lit = __NAME___dsp_lit(60);
    /* 6 unison voices wanted, 4 available -> the oldest stack (60) is stolen */
    if (lit != ((1u << 12) | (1u << 24))) {
        printf("FAIL: per-part unison stacking (lit=%u)\\n", lit);
        return 1;
    }
    printf("ok: __NAME__ per-part mono priority/takeover + poly isolation + unison\\n");
    return 0;
}
"""

# The §12.1 set_param seam contract: a bad id is rejected (-1, no write) and an
# out-of-range value is clamped to the param's [min, max] (the dsp_param table).
SET_PARAM_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
int __NAME___dsp_set_param(uint32_t id, int32_t value);
int32_t __NAME___dsp_get_param(uint32_t id);
uint32_t __NAME___dsp_param_count(void);
int main(void) {
    uint32_t n = __NAME___dsp_param_count();
    if (__NAME___dsp_set_param(n, 1) != -1) {
        printf("FAIL: bad id n\\n");
        return 1;
    }
    if (__NAME___dsp_set_param(n + 100, 1) != -1) {
        printf("FAIL: bad id n+100\\n");
        return 1;
    }
    /* the universal `mode` param is min 0, max 2 */
    if (__NAME___dsp_set_param(__MODE_ID__, 999) != 0) {
        printf("FAIL: clamp hi\\n");
        return 1;
    }
    if (__NAME___dsp_get_param(__MODE_ID__) != 2) {
        printf("FAIL: hi not clamped\\n");
        return 1;
    }
    if (__NAME___dsp_set_param(__MODE_ID__, -5) != 0) {
        printf("FAIL: clamp lo\\n");
        return 1;
    }
    if (__NAME___dsp_get_param(__MODE_ID__) != 0) {
        printf("FAIL: lo not clamped\\n");
        return 1;
    }
    printf("ok: __NAME__ set_param rejects bad ids and clamps values\\n");
    return 0;
}
"""

# The fixed cc-map contract (F5): every mapped CC's param id is a real, writable
# engine param (set accepted), the reverse table is consistent, and the coverage
# is complete (CC_PARAMS == the engine's param count).
CC_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
#include "cc_map.h"
int __NAME___dsp_set_param(uint32_t id, int32_t value);
uint32_t __NAME___dsp_param_count(void);
int main(void) {
    uint32_t n = __NAME___dsp_param_count();
    uint32_t seen = 0;
    for (uint32_t cc = 0; cc < 128; cc++) {
        if (cc_to_param[cc] == CC_NONE) continue;
        uint32_t id = cc_to_param[cc];
        if (id >= n) { printf("FAIL: id out of range\\n"); return 1; }
        if (__NAME___dsp_set_param(id, 1) != 0) {
            printf("FAIL: set rejected\\n");
            return 1;
        }
        if (param_to_cc[id] != cc) {
            printf("FAIL: reverse mismatch\\n");
            return 1;
        }
        seen++;
    }
    if (seen != CC_PARAMS || CC_PARAMS != n) { printf("FAIL: coverage\\n"); return 1; }
    printf("ok: __NAME__ a CC write reaches its mapped param\\n");
    return 0;
}
"""


def _include_args() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    return ["-I", str(root / "firmware" / "hal"), "-I", str(root / "firmware" / "gen")]


def _compile(patch: Patch) -> tuple[bool, str]:
    """Generate + compile the patch's dsp.c for host (object check only)."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-c",
                "-o",
                str(d / "dsp.o"),
                str(d / "dsp.c"),
            ],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stderr


def _sound(patch: Patch) -> tuple[bool, str]:
    """Generate, compile, and run the sound contract (non-silent then silent)."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(SOUND_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _velocity_responds(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the velocity contract (high velocity is louder)."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(VEL_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _velocity_rate_responds(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the velocity→rate contract (one process per velocity,
    so the engine's static per-voice envelope/phase don't leak between notes)."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(VEL_RATE_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        hi = int(
            subprocess.run(
                [str(d / "t"), "127"], capture_output=True, text=True
            ).stdout.strip()
        )
        lo = int(
            subprocess.run(
                [str(d / "t"), "1"], capture_output=True, text=True
            ).stdout.strip()
        )
        if hi <= 2 * lo:
            return False, f"velocity did not scale the envelope rate (hi={hi} lo={lo})"
        return True, "velocity scales the operator envelope rate"


def _retrigger_on_steal(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the steal-retrigger contract: a note-on that steals
    a sounding voice resets its envelope (the `trigger` reserved input). One process
    per mode, so the engine's static per-voice envelope/phase don't leak between
    notes."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(RETRIG_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        fresh = int(
            subprocess.run(
                [str(d / "t"), "fresh"], capture_output=True, text=True
            ).stdout.strip()
        )
        steal = int(
            subprocess.run(
                [str(d / "t"), "steal"], capture_output=True, text=True
            ).stdout.strip()
        )
        if steal > 3 * fresh:
            return False, f"steal did not retrigger (fresh={fresh} steal={steal})"
        return True, "a voice steal retriggers the envelope"


def _voice_ceiling() -> tuple[bool, str]:
    """The polyphony ceiling + steal-policy contract: a 4-voice patch holding a 5th
    note steals the *oldest* gated voice — the pool never grows past NVOICE.
    Observed through `dsp_lit` (the gated-note bitmask in a 27-note window)."""
    patch: Patch = {
        "name": "ceiling_test",
        "voices": 4,
        "voice": {
            "nodes": [
                {"id": "ph", "type": "phasor"},
                {"id": "osc", "type": "osc"},
            ],
            "wires": [{"from": "ph.phase", "to": "osc.phase"}],
            "voice_out": "osc.audio",
        },
        "global": {"nodes": [], "wires": []},
    }
    src = generate(patch)
    cname = "ceiling_test"
    harness = (
        "#include <stdio.h>\n#include <stdint.h>\n"
        f"void {cname}_dsp_reset(void);\n"
        f"void {cname}_dsp_note_on(uint32_t note, uint32_t velocity);\n"
        f"uint32_t {cname}_dsp_lit(uint32_t base);\n"
        "int main(void) {\n"
        f"    {cname}_dsp_reset();\n"
        f"    {cname}_dsp_note_on(60, 100);\n"
        f"    {cname}_dsp_note_on(61, 100);\n"
        f"    {cname}_dsp_note_on(62, 100);\n"
        f"    {cname}_dsp_note_on(63, 100);\n"
        f"    uint32_t full = {cname}_dsp_lit(60);\n"
        f"    {cname}_dsp_note_on(64, 100);\n"
        f"    uint32_t after = {cname}_dsp_lit(60);\n"
        '    if (full != 0xFu) { printf("FAIL: 4 notes did not fill 4 voices '
        '(lit=%x)\\n", full); return 1; }\n'
        '    if (after != 0x1Eu) { printf("FAIL: 5th note did not steal the oldest '
        '(lit=%x)\\n", after); return 1; }\n'
        '    printf("ok: voice ceiling: the 5th note steals the oldest of 4\\n");\n'
        "    return 0;\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        if run.returncode != 0:
            return False, run.stdout.strip() or run.stderr.strip()
        return True, run.stdout.strip()


def _asan_clean() -> tuple[bool, str]:
    """The generated fourop-fm DSP is ASan/UBSan-clean under worst-case load (128
    held notes -> repeated voice steals across the 20-voice pool). A sanitizer abort
    fails the test. `-fno-sanitize-recover=all` fails on the first error."""
    root = Path(__file__).resolve().parents[1]
    patch = as_patch(
        json.loads(
            (root / "examples" / "fourop-fm" / "patch.json").read_text(encoding="utf-8")
        )
    )
    src = generate(patch)
    tables_h, tables_c = generate_tables(patch)
    cname = "fourop_fm"
    harness = (
        "#include <stdint.h>\n"
        f"void {cname}_dsp_reset(void);\n"
        f"void {cname}_dsp_note_on(uint32_t note, uint32_t velocity);\n"
        f"void {cname}_dsp_render(int32_t *out, uint32_t frames);\n"
        "static int32_t out[512];\n"
        "int main(void) {\n"
        f"    {cname}_dsp_reset();\n"
        "    for (uint32_t n = 0; n < 128; n++) "
        f"{cname}_dsp_note_on(n, 100);\n"
        "    for (int s = 0; s < 32; s++) "
        f"{cname}_dsp_render(out, 256);\n"
        "    return 0;\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "tables.h").write_text(tables_h)
        (d / "tables.c").write_text(tables_c)
        (d / "harness.c").write_text(harness)
        sources = [str(d / "harness.c"), str(d / "dsp.c"), str(d / "tables.c")]
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-fsanitize=address,undefined",
                "-fno-sanitize-recover=all",
                "-g",
                *_include_args(),
                "-I",
                str(d),
                "-o",
                str(d / "t"),
                *sources,
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
        run = subprocess.run([str(d / "t")], capture_output=True, text=True, env=env)
        if run.returncode != 0:
            return False, "sanitizer flagged:\n" + (run.stderr or run.stdout)
        return True, "ASan/UBSan-clean (128 held notes)"


def _modes_behave(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the mono/unison contracts (mode params via
    set_param)."""
    src = generate(patch)
    mode_id = str(param_ids(patch)["mode"])
    count_id = str(param_ids(patch)["unison_count"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        harness = (
            MODE_HARNESS.replace("__NAME__", cname)
            .replace("__MODE_ID__", mode_id)
            .replace("__UNISON_COUNT_ID__", count_id)
        )
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _legato_behave(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the legato contract (mono overlap retrigger). One
    process per legato value, so the engine's static envelope/phase don't leak."""
    src = generate(patch)
    mode_id = str(param_ids(patch)["mode"])
    legato_id = str(param_ids(patch)["legato"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        harness = (
            LEGATO_HARNESS.replace("__NAME__", cname)
            .replace("__MODE_ID__", mode_id)
            .replace("__LEGATO_ID__", legato_id)
        )
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        on = int(
            subprocess.run(
                [str(d / "t"), "1"], capture_output=True, text=True
            ).stdout.strip()
        )
        off = int(
            subprocess.run(
                [str(d / "t"), "0"], capture_output=True, text=True
            ).stdout.strip()
        )
        if on <= 2 * off:
            return False, f"legato did not hold the envelope (on={on} off={off})"
        return True, "legato holds the envelope across an overlap"


def _glide_ramps(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the portamento contract: a note change glides the
    pitch (constant rate) rather than snapping. One process per portamento value."""
    src = generate(patch)
    portamento_id = str(param_ids(patch)["portamento"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        harness = GLIDE_HARNESS.replace("__NAME__", cname).replace(
            "__PORTAMENTO_ID__", portamento_id
        )
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        snap = int(
            subprocess.run(
                [str(d / "t"), "0"], capture_output=True, text=True
            ).stdout.strip()
        )
        glide = int(
            subprocess.run(
                [str(d / "t"), "100"], capture_output=True, text=True
            ).stdout.strip()
        )
        if glide >= snap - 3:
            return False, f"portamento did not glide (snap={snap} glide={glide})"
        return True, "portamento glides the pitch instead of snapping"


def _parts_route(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the multitimbral contract: channel routing + layering
    (one process per route, so the engine's static phase is shared)."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(PARTS_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        omni = int(
            subprocess.run(
                [str(d / "t"), "omni"], capture_output=True, text=True
            ).stdout.strip()
        )
        ch0 = int(
            subprocess.run(
                [str(d / "t"), "ch0"], capture_output=True, text=True
            ).stdout.strip()
        )
        if omni <= 3 * ch0:
            return False, f"parts routing/layering failed (omni={omni} ch0={ch0})"
        return True, "parts route by channel and layer (omni fires both parts)"


def _parts_level_delay(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the per-part level (gain) + delay (onset) contracts."""
    src = generate(patch)
    level_id = str(param_ids(patch)["level.p0"])
    delay_id = str(param_ids(patch)["delay.p0"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        harness = (
            LEVEL_DELAY_HARNESS.replace("__NAME__", cname)
            .replace("__LEVEL_P0_ID__", level_id)
            .replace("__DELAY_P0_ID__", delay_id)
        )
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _parts_modes(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the per-part voice-mode contract: the six mode
    params are per-part (mono for part 0, poly/unison for part 1)."""
    src = generate(patch)
    ids = param_ids(patch)
    subs = {
        "__NAME__": patch["name"].replace("-", "_").replace(".", "_"),
        "__MODE_P0_ID__": str(ids["mode.p0"]),
        "__MODE_P1_ID__": str(ids["mode.p1"]),
        "__UNISON_COUNT_P1_ID__": str(ids["unison_count.p1"]),
    }
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        harness = PARTS_MODE_HARNESS
        for k, v in subs.items():
            harness = harness.replace(k, v)
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


TAP_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
const int32_t *__NAME___dsp_tap(uint32_t ch);
static int32_t out[512];
static int64_t energy(const int32_t *p, uint32_t n) {
    int64_t e = 0;
    for (uint32_t i = 0; i < n; i++) e += (int64_t)p[i] * p[i];
    return e;
}
int main(void) {
    /* part 0 only (channel 0): its 4 operator taps are live, part 1's are silent */
    __NAME___dsp_reset();
    __NAME___dsp_note_on_ch(60, 100, 0u);
    __NAME___dsp_render(out, 256);
    __NAME___dsp_render(out, 256);
    __NAME___dsp_render(out, 256);
    int64_t e00 = energy(__NAME___dsp_tap(0), 256);
    int64_t e02 = energy(__NAME___dsp_tap(2), 256);
    int64_t e04 = energy(__NAME___dsp_tap(4), 256);
    int64_t e06 = energy(__NAME___dsp_tap(6), 256);
    int64_t e11 = energy(__NAME___dsp_tap(1), 256);
    int64_t e08 = energy(__NAME___dsp_tap(8), 256);  /* part 0 mix */
    int64_t e09 = energy(__NAME___dsp_tap(9), 256);  /* part 1 mix */
    if (e00 <= 0 || e02 <= 0 || e04 <= 0 || e06 <= 0) {
        printf("FAIL: part 0 taps silent (%lld %lld %lld %lld)\\n",
               (long long)e00, (long long)e02, (long long)e04, (long long)e06);
        return 1;
    }
    if (e11 != 0) {
        printf("FAIL: part 1 tap non-silent with no note (e=%lld)\\n", (long long)e11);
        return 1;
    }
    if (e08 <= 0) {
        printf("FAIL: part 0 mix tap silent\\n");
        return 1;
    }
    if (e09 != 0) {
        printf("FAIL: part 1 mix tap non-silent (e=%lld)\\n", (long long)e09);
        return 1;
    }
    /* mute op2 -> its tap (channel 2) goes silent, op1 stays live */
    __NAME___dsp_set_param(__OP2_MUTE_ID__, 1);
    __NAME___dsp_reset();
    __NAME___dsp_note_on_ch(60, 100, 0u);
    __NAME___dsp_render(out, 256);
    __NAME___dsp_render(out, 256);
    __NAME___dsp_render(out, 256);
    int64_t e2 = energy(__NAME___dsp_tap(2), 256);
    int64_t e0 = energy(__NAME___dsp_tap(0), 256);
    if (e2 != 0) {
        printf("FAIL: muted op2 tap non-silent (%lld)\\n", (long long)e2);
        return 1;
    }
    if (e0 <= 0) { printf("FAIL: op1 tap silent after op2 mute\\n"); return 1; }
    printf("ok: __NAME__ per-op + per-part taps (4 ops x 2 parts + 2 part mixes)\\n");
    return 0;
}
"""


def _taps_expose() -> tuple[bool, str]:
    """Generate + compile + run the per-op scope-tap contract: the `taps:` sources
    expose each operator's audio, per part, and a mute silences its tap."""
    root = Path(__file__).resolve().parents[1]
    patch = as_patch(
        json.loads(
            (root / "examples" / "fourop-fm" / "patch.json").read_text(encoding="utf-8")
        )
    )
    src = generate(patch)
    tables_h, tables_c = generate_tables(patch)
    ids = param_ids(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "tables.h").write_text(tables_h)
        (d / "tables.c").write_text(tables_c)
        harness = TAP_HARNESS.replace(
            "__NAME__", patch["name"].replace("-", "_").replace(".", "_")
        ).replace("__OP2_MUTE_ID__", str(ids["op2_mute.p0"]))
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                str(d / "tables.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _set_param_contract(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the §12.1 set_param contract (bad-id rejection +
    value clamp)."""
    src = generate(patch)
    mode_id = str(param_ids(patch)["mode"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(
            SET_PARAM_HARNESS.replace("__NAME__", cname).replace("__MODE_ID__", mode_id)
        )
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _cc_map_reaches(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the cc-map contract: a CC write through the generated
    `cc_map.h` table reaches a real, writable engine param."""
    from .generate import generate_cc_header

    src = generate(patch)
    header = generate_cc_header(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "cc_map.h").write_text(header)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(CC_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-I",
                str(d),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _sound_tables(patch: Patch) -> tuple[bool, str]:
    """Generate + compile (with tables.c) + run the sound contract for a table patch."""
    src = generate(patch)
    hdr, impl = generate_tables(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "tables.h").write_text(hdr)
        (d / "tables.c").write_text(impl)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(SOUND_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-I",
                str(d),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                str(d / "tables.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _sound_decay_tables(patch: Patch) -> tuple[bool, str]:
    """Generate + compile (with tables.c) + run the decay contract (for a patch
    with a post-voice IIR stage whose tail never reaches exact zero)."""
    src = generate(patch)
    hdr, impl = generate_tables(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "tables.h").write_text(hdr)
        (d / "tables.c").write_text(impl)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(DECAY_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-I",
                str(d),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                str(d / "tables.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _algorithms_render(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run the runtime-algorithm contract: each of the 8
    algorithms, selected via set_param, must render non-silent."""
    src = generate(patch)
    hdr, impl = generate_tables(patch)
    algo_id = str(param_ids(patch)["algorithm"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "tables.h").write_text(hdr)
        (d / "tables.c").write_text(impl)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        harness = ALGO_HARNESS.replace("__NAME__", cname).replace(
            "__ALGO_ID__", algo_id
        )
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-I",
                str(d),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                str(d / "tables.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _lfo_varies(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run a dump, checking the `lfo` output is non-constant
    (it oscillates) rather than a stuck DC value."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(DUMP_HARNESS.replace("__NAME__", cname))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        samples = [int(x) for x in run.stdout.split()]
    if not samples or len(set(samples)) < 2:
        return False, "lfo output is constant"
    return True, ""


# the waveform shapes (OPZ + OPL union): a small C probe against the HAL directly.
_WAVE_PROBE = r"""
#include <stdio.h>
#include <stdint.h>
#include "fm1_math.h"
int main(void) {
    int32_t sine_max = 0, sine_min = 0, sq_max = 0, sq_min = 0;
    int32_t half_min = 0, dhs_min = 0, rect_min = 0, pulse_peak = 0, pulse_odd_max = 0;
    int half_nonzero_second = 0;
    for (uint32_t n = 0; n < 1024; n++) {
        uint32_t ph = n << 22;
        int32_t s = fm1_sin_wave(ph, 0);    /* sine */
        int32_t h = fm1_sin_wave(ph, 2);    /* half sine */
        int32_t d = fm1_sin_wave(ph, 6);    /* double half sine */
        int32_t r = fm1_sin_wave(ph, 8);    /* rectified */
        int32_t p = fm1_sin_wave(ph, 9);    /* pulse */
        int32_t sq = fm1_sin_wave(ph, 10);  /* square */
        if (s > sine_max) sine_max = s;
        if (s < sine_min) sine_min = s;
        if (sq > sq_max) sq_max = sq;
        if (sq < sq_min) sq_min = sq;
        if (h < half_min) half_min = h;
        if (d < dhs_min) dhs_min = d;
        if (r < rect_min) rect_min = r;
        if (p > pulse_peak) pulse_peak = p;
        /* the band-limited pulse is |sin| in the even quadrants (q0/q2), ~zero in
           the odd ones (q1/q3) up to its Gibbs ringing around the 1->0 step */
        if (ph & 0x40000000u) {
            int32_t ap = p < 0 ? -p : p;
            if (ap > pulse_odd_max) pulse_odd_max = ap;
        }
        if (ph >= 0x80000000u && h != 0) half_nonzero_second = 1;
    }
    if (sine_max < 32000 || sine_min > -32000) {
        printf("FAIL: sine not full-scale (%d, %d)\n", sine_max, sine_min);
        return 1;
    }
    if (half_min < 0 || half_nonzero_second) { printf("FAIL: half sine\n"); return 1; }
    if (dhs_min < 0) { printf("FAIL: double half sine negative\n"); return 1; }
    if (rect_min < 0) { printf("FAIL: rectified negative\n"); return 1; }
    /* a band-limited pulse: a full-scale bump in q0/q2, but the off-quadrants never
       reach full scale (they ring around the 1->0 step, bounded well below 2^15) */
    if (pulse_peak < 30000 || pulse_odd_max > 20000) {
        printf("FAIL: pulse (peak %d, odd-max %d)\n", pulse_peak, pulse_odd_max);
        return 1;
    }
    if (sq_max < 32000 || sq_min > -32000) {
        printf("FAIL: square not full-scale (%d, %d)\n", sq_max, sq_min);
        return 1;
    }
    /* out-of-range ws (12..15, or any >11) degrades to sine, not an OOB read */
    if (fm1_sin_wave(0x20000000u, 12) != fm1_sin_wave(0x20000000u, 0)) {
        printf("FAIL: bad waveform does not degrade to sine\n");
        return 1;
    }
    printf("ok: 12 waveforms (OPZ + OPL shapes correct)\n");
    return 0;
}
"""


def _wave_shapes() -> tuple[bool, str]:
    """Compile + run the waveform-shape probe against the HAL."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "t.c").write_text(_WAVE_PROBE)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "t.c"),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


_MUTE_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
int __NAME___dsp_set_param(uint32_t id, int32_t value);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
static int32_t out[1024];
int main(void) {
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, 100);
    __NAME___dsp_render(out, 512);
    int64_t e = 0; for (int i = 0; i < 1024; i++) e += (int64_t)out[i] * out[i];
    if (e < 1000000) { printf("FAIL: unmuted silent\\n"); return 1; }
    __NAME___dsp_set_param(__MUTE_ID__, 1);
    __NAME___dsp_render(out, 512);
    int64_t t = 0; for (int i = 0; i < 1024; i++) t += (int64_t)out[i] * out[i];
    if (t != 0) {
        printf("FAIL: muted not silent (tail=%lld)\\n", (long long)t);
        return 1;
    }
    printf("ok: mute gates the output\\n");
    return 0;
}
"""


def _mute_gates(patch: Patch) -> tuple[bool, str]:
    """Generate + compile + run: the `mute` param silences the output."""
    src = generate(patch)
    mute_id = str(param_ids(patch)["g.mute"])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        harness = _MUTE_HARNESS.replace("__NAME__", cname).replace(
            "__MUTE_ID__", mute_id
        )
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return run.returncode == 0, run.stdout.strip()


def _goertzel(sig: list[int], freq: float, fs: float) -> float:
    """DFT magnitude at an arbitrary (possibly non-bin) frequency."""
    c = 2.0 * math.cos(2.0 * math.pi * freq / fs)
    s0 = 0.0
    s1 = 0.0
    s2 = 0.0
    for x in sig:
        s0 = x + c * s1 - s2
        s2 = s1
        s1 = s0
    return math.sqrt(s1 * s1 + s2 * s2 - c * s1 * s2)


def _naive_saw(n: int, inc: int) -> list[int]:
    """The un-corrected saw (same phase accumulator, no polyBLEP)."""
    ph = 0
    out: list[int] = []
    for _ in range(n):
        ph = (ph + inc) & 0xFFFFFFFF
        out.append((ph >> 16) - 32768)
    return out


def _naive_square(n: int, inc: int) -> list[int]:
    """The un-corrected square (width 0.5, same phase accumulator)."""
    ph = 0
    out: list[int] = []
    for _ in range(n):
        ph = (ph + inc) & 0xFFFFFFFF
        out.append(32767 if ph < 0x80000000 else -32767)
    return out


def _render_samples(patch: Patch, frames: int, note: int = 69) -> list[int]:
    """Generate + compile + run the patch, returning `frames` left-channel samples."""
    src = generate(patch)
    cname = patch["name"].replace("-", "_").replace(".", "_")
    harness = (
        "#include <stdio.h>\n#include <stdint.h>\n"
        f"void {cname}_dsp_note_on(uint32_t note, uint32_t velocity);\n"
        f"void {cname}_dsp_render(int32_t *out, uint32_t frames);\n"
        f"static int32_t out[{2 * frames}];\n"
        "int main(void) {\n"
        f"    {cname}_dsp_note_on({note}, 100);\n"
        f"    {cname}_dsp_render(out, {frames});\n"
        f'    for (int i = 0; i < {frames}; i++) printf("%d\\n", out[2 * i]);\n'
        "    return 0;\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError("compile failed:\n" + proc.stderr)
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        if run.returncode != 0:
            raise AssertionError("run failed:\n" + run.stderr)
    return [int(x) for x in run.stdout.split()]


def _up_crossings(samples: list[int]) -> int:
    """Count - → + zero crossings (the fundamental's cycle count)."""
    return sum(1 for a, b in zip(samples, samples[1:], strict=False) if a < 0 <= b)


def _level_taper() -> tuple[bool, str]:
    """The operator level taper: 0 = silence, 99 = maximum, 50 = a meaningful
    middle. Locks the 0.25 dB/step curve (0 = mute, 50 ≈ −12 dB) against the old
    0.75 dB/step curve where 50 read as ~silence. A flat instant envelope keeps the
    measurement about the level, not the EG."""

    def patch(level: int) -> Patch:
        return {
            "name": f"level_taper_{level}",
            "voices": 1,
            "voice": {
                "nodes": [
                    {
                        "id": "op",
                        "type": "fm_op",
                        "params": {
                            "ratio": 65536,
                            "level": level,
                            "r1": 99,
                            "r2": 99,
                            "r3": 99,
                            "r4": 99,
                            "l1": 99,
                            "l2": 99,
                            "l3": 99,
                        },
                    }
                ],
                "wires": [],
                "voice_out": "op.audio",
            },
            "global": {"nodes": [], "wires": []},
        }

    def energy(level: int) -> int:
        samples = _render_samples(patch(level), 512)
        return sum(s * s for s in samples)

    e0, e50, e99 = energy(0), energy(50), energy(99)
    if e0 == 0 and e99 > 4 * e50 and e50 > 0:
        return True, ""
    return (
        False,
        f"level taper: 0={e0} (want 0), 50={e50}, 99={e99} (want 99 > 4·50 > 0)",
    )


def _pm_semantics() -> tuple[bool, str]:
    """The phasor is a *phase* modulator, not an integrator: a DC-heavy modulator
    must not detune the carrier, and self-feedback must not collapse to a DC fixed
    point. 440 Hz over 8192 frames at 44.1 kHz is ~81.7 up-crossings."""
    dc = _render_samples(PM_DC_MOD, 8192)
    up_dc = _up_crossings(dc)
    fb = _render_samples(PM_FEEDBACK, 8192)
    up_fb = _up_crossings(fb)
    p2p = max(fb) - min(fb)
    ok = 70 <= up_dc <= 95 and 70 <= up_fb <= 95 and p2p > 12000
    if ok:
        return True, ""
    return False, (
        f"PM contract: DC-mod up-crossings {up_dc} (want ~82 at 440 Hz), "
        f"feedback up-crossings {up_fb}, p2p {p2p} (want > 12000)"
    )


def _release_tail() -> tuple[bool, str]:
    """note-off releases: after a key release the operator envelope keeps sounding
    (a release tail) and decays to silence — not an instant cut. The first 64
    frames after note-off must be non-silent; the last 2048 of an ~2.9 s release
    render must be near-silent (the release at r4 = 60 is ~1.9 s)."""
    src = generate(RELEASE_PATCH)
    cname = "release_test"
    harness = (
        "#include <stdio.h>\n#include <stdint.h>\n"
        f"void {cname}_dsp_note_on(uint32_t note, uint32_t velocity);\n"
        f"void {cname}_dsp_note_off(uint32_t note);\n"
        f"void {cname}_dsp_render(int32_t *out, uint32_t frames);\n"
        "static int32_t out[262144];\n"
        "int main(void) {\n"
        f"    {cname}_dsp_note_on(69, 100);\n"
        f"    {cname}_dsp_render(out, 512);\n"
        f"    {cname}_dsp_note_off(69);\n"
        f"    {cname}_dsp_render(out, 64);\n"
        "    int64_t e0 = 0; for (int i = 0; i < 128; i++) "
        "e0 += (int64_t)out[i] * out[i];\n"
        f"    {cname}_dsp_render(out, 131072);\n"
        "    int64_t e1 = 0; for (int i = 258048; i < 262144; i++) "
        "e1 += (int64_t)out[i] * out[i];\n"
        '    printf("%lld %lld\\n", (long long)e0, (long long)e1);\n'
        "    return 0;\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, "compile failed:\n" + proc.stderr
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        if run.returncode != 0:
            return False, "run failed:\n" + run.stderr
    e0, e1 = (int(x) for x in run.stdout.split())
    ok = e0 > 1_000_000 and e1 < 1_000_000
    if ok:
        return True, ""
    return (
        False,
        f"release tail: energy right after off {e0} (want > 1e6), "
        f"late {e1} (want < 1e6)",
    )


def _pitch_env() -> tuple[bool, str]:
    """The per-note pitch envelope moves pitch: with `on` and a +1-octave sustain,
    the carrier's fundamental doubles (≈2× up-crossings vs `off`)."""
    on = _render_samples(_penv_patch(1), 8192)
    off = _render_samples(_penv_patch(0), 8192)
    up_on = _up_crossings(on)
    up_off = _up_crossings(off)
    ok = up_off >= 60 and up_on >= 1.8 * up_off
    if ok:
        return True, ""
    return False, f"pitch envelope: on {up_on} vs off {up_off} up-crossings (want ≈2×)"


def _mod_pulse_samples(patch: Patch, width_depth: int, frames: int) -> list[int]:
    """Generate + compile + run the pulse-modulation patch with a given `width_depth`,
    returning `frames` left-channel samples. One fresh process per call (the engine's
    static phase/envelope are shared across renders within a process)."""
    src = generate(patch)
    cname = patch["name"].replace("-", "_").replace(".", "_")
    wid = str(param_ids(patch)["osc.width_depth"])
    harness = (
        "#include <stdio.h>\n#include <stdint.h>\n"
        f"void {cname}_dsp_reset(void);\n"
        f"void {cname}_dsp_note_on(uint32_t note, uint32_t velocity);\n"
        f"void {cname}_dsp_render(int32_t *out, uint32_t frames);\n"
        f"int {cname}_dsp_set_param(uint32_t id, int32_t value);\n"
        f"static int32_t out[{2 * frames}];\n"
        "int main(void) {\n"
        f"    {cname}_dsp_reset();\n"
        f"    {cname}_dsp_set_param({wid}, {width_depth});\n"
        f"    {cname}_dsp_note_on(69, 100);\n"
        f"    {cname}_dsp_render(out, {frames});\n"
        f'    for (int i = 0; i < {frames}; i++) printf("%d\\n", out[2 * i]);\n'
        "    return 0;\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "harness.c").write_text(harness)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError("compile failed:\n" + proc.stderr)
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        if run.returncode != 0:
            raise AssertionError("run failed:\n" + run.stderr)
    return [int(x) for x in run.stdout.split()]


def _modulation_works() -> None:
    """A wired `<param>_mod` input changes the output only when `<param>_depth` is
    non-zero (D23: effective = base + mod·depth). At depth 0 the LFO is inert (a
    constant square); at full depth it sweeps the duty, so the two renders differ."""
    base = _mod_pulse_samples(MOD_PULSE_TEST, 0, 512)
    modded = _mod_pulse_samples(MOD_PULSE_TEST, 32767, 512)
    diff = sum(abs(a - b) for a, b in zip(base, modded, strict=True))
    assert diff > 100_000, f"width modulation did not change the output (diff={diff})"
    print(f"ok: width modulation changes the output (sum|diff|={diff})")


def _saw_antialias() -> None:
    """The polyBLEP saw removes the wrap discontinuity and attenuates high
    harmonics vs a naive saw (the anti-aliasing claim, verified spectrally)."""
    src = generate(SAW_TEST)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        (d / "harness.c").write_text(DUMP_HARNESS.replace("__NAME__", "saw_test"))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                *_include_args(),
                "-o",
                str(d / "t"),
                str(d / "harness.c"),
                str(d / "dsp.c"),
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError("compile failed:\n" + proc.stderr)
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        samples = [int(x) for x in run.stdout.split()]

    n = len(samples)
    inc = 42852281  # note_to_inc(69) at 44.1 kHz (A4 = 440 Hz)
    naive = _naive_saw(n, inc)

    def max_jump(x: list[int]) -> int:
        return max(abs(x[i] - x[i - 1]) for i in range(1, len(x)))

    pj = max_jump(samples)
    nj = max_jump(naive)
    assert pj < nj * 0.85, f"polyBLEP saw max jump {pj} is not below naive {nj}"
    print(f"ok: polyBLEP saw max jump {pj} < naive {nj} (no full-scale wrap)")

    # near-Nyquist harmonic energy (relative to the fundamental) is attenuated
    fs = 44100.0
    f0 = fs * inc / (1 << 32)
    for h in (40, 50):
        f = f0 * h
        if f >= fs / 2:
            continue
        blep = _goertzel(samples, f, fs) / _goertzel(samples, f0, fs)
        naive_h = _goertzel(naive, f, fs) / _goertzel(naive, f0, fs)
        assert blep < naive_h * 0.75, (
            f"polyBLEP harmonic {h} not attenuated ({blep:.3f} vs {naive_h:.3f})"
        )
        print(
            f"ok: polyBLEP harmonic {h} attenuated ({blep:.3f} vs naive {naive_h:.3f})"
        )


def _pulse_antialias() -> None:
    """The polyBLEP pulse (square at width 0.5) attenuates its odd near-Nyquist
    harmonics vs the naive square (two BLEPs smooth both discontinuities)."""
    samples = _render_samples(PULSE_TEST, 2048)
    inc = 42852281  # note_to_inc(69) at 44.1 kHz (A4 = 440 Hz)
    naive = _naive_square(len(samples), inc)
    fs = 44100.0
    f0 = fs * inc / (1 << 32)
    for h in (41, 43, 45, 47, 49):  # odd harmonics near Nyquist (square has none even)
        f = f0 * h
        if f >= fs / 2:
            continue
        blep = _goertzel(samples, f, fs) / _goertzel(samples, f0, fs)
        naive_h = _goertzel(naive, f, fs) / _goertzel(naive, f0, fs)
        assert blep < naive_h * 0.75, (
            f"polyBLEP pulse harmonic {h} not attenuated ({blep:.3f} vs {naive_h:.3f})"
        )
        print(
            "ok: polyBLEP pulse harmonic "
            f"{h} attenuated ({blep:.3f} vs naive {naive_h:.3f})"
        )


def _table_osc_antialias() -> None:
    """The mip-mapped band-limited `osc` table removes the folded harmonics a naive
    square produces at a high note: at C7 (2093 Hz) harmonic 11 sits above Nyquist
    and folds to ~21077 Hz. The band-limited table (8 harmonics) has none of it —
    only the (much weaker) Gibbs ringing of the truncation remains."""
    note = 96  # C7
    inc = 203840951  # note_to_inc(96) at 44.1 kHz
    samples = _render_samples(OSC_TABLE_BL, 2048, note)
    naive = _naive_square(len(samples), inc)
    fs = 44100.0
    f0 = fs * inc / (1 << 32)
    alias = abs(fs - f0 * 11)  # harmonic 11 (23023 Hz) folds to 21077 Hz
    bl = _goertzel(samples, alias, fs) / _goertzel(samples, f0, fs)
    na = _goertzel(naive, alias, fs) / _goertzel(naive, f0, fs)
    assert bl < na * 0.5, f"folded harmonic 11 not attenuated ({bl:.3f} vs {na:.3f})"
    print(f"ok: table square drops folded harmonic 11 ({bl:.3f} vs {na:.3f})")


def _triangle_bandlimited() -> None:
    """The polyBLEP triangle (integrated square) has the ideal odd-harmonic 1/n^2
    spectrum — a band-limited triangle (unlike saw/square's 1/n, the triangle
    already rolls off fast, so the claim is the *correct* spectrum, not
    attenuation vs the naive triangle). The leaky integrator's note-on transient
    is skipped (measured over the steady-state tail)."""
    samples = _render_samples(TRIANGLE_TEST, 16384)
    tail = samples[8192:]  # steady state (the transient decays in ~2^13 samples)
    inc = 42852281
    fs = 44100.0
    f0 = fs * inc / (1 << 32)
    peak = max(abs(x) for x in tail)
    assert 28000 <= peak <= 34000, f"triangle peak {peak} is not full-scale"
    print(f"ok: polyBLEP triangle peak {peak} (full-scale)")
    # odd harmonics follow 1/n^2 (3 -> 1/9, 21 -> 1/441); a band-limited triangle
    for h, expect in ((3, 1.0 / 9.0), (21, 1.0 / 441.0)):
        got = _goertzel(tail, f0 * h, fs) / _goertzel(tail, f0, fs)
        assert expect * 0.7 <= got <= expect * 1.3, (
            f"triangle harmonic {h} {got:.4f} not ~1/{h * h}={expect:.4f}"
        )
        print(f"ok: polyBLEP triangle harmonic {h} ~1/{h * h} ({got:.4f})")
    # near-Nyquist odd harmonic stays tiny (no aliasing spike)
    h49 = _goertzel(tail, f0 * 49, fs) / _goertzel(tail, f0, fs)
    assert h49 < 0.005, f"triangle near-Nyquist harmonic 49 {h49:.4f} not tiny"
    print(f"ok: polyBLEP triangle near-Nyquist harmonic 49 tiny ({h49:.4f})")


def _compile_tables(hdr: str, impl: str) -> tuple[bool, str]:
    """Compile the generated tables.c (with its tables.h) for host."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "tables.h").write_text(hdr)
        (d / "tables.c").write_text(impl)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-I",
                str(d),
                "-c",
                "-o",
                str(d / "tables.o"),
                str(d / "tables.c"),
            ],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stderr


def _table_placeholder_resolves() -> None:
    """`${table.<name>}` resolves to the table's C name; unknown -> GenError."""
    from ._backend import substitute
    from ._ir import NodeInstance, NodeSpec

    inst = NodeInstance(id="w", type="wt", zone="voice", spec=NodeSpec(name="wt"))
    out = substitute(inst, "int32_t x = ${table.sine}[0];", "v", {"sine"}, False)
    assert "table_sine" in out and "${" not in out
    try:
        substitute(inst, "int32_t x = ${table.nope}[0];", "v", {"sine"}, False)
        raise AssertionError("unknown table not rejected")
    except GenError:
        pass


def _tune_pitch() -> None:
    """The tuned_phasor octave/semi/cent tuning shifts the fundamental by the
    expected ratio (octave +1 = ×2, semi +12 = ×2, cent +100 = ×2^(1/12))."""
    fs = 44100.0

    def fundamental(o: int, s: int, c: int) -> float:
        patch: Patch = {
            "name": f"tune_{o}_{s}_{c}".replace("-", "m"),
            "voices": 1,
            "voice": {
                "nodes": [
                    {
                        "id": "ph",
                        "type": "tuned_phasor",
                        "params": {"octave": o, "semi": s, "cent": c},
                    },
                    {"id": "osc", "type": "naive_osc", "params": {"shape": 1}},
                    {"id": "env", "type": "env"},
                    {"id": "vca", "type": "vca"},
                ],
                "wires": [
                    {"from": "ph.phase", "to": "osc.phase"},
                    {"from": "osc.audio", "to": "vca.audio"},
                    {"from": "env.cv", "to": "vca.cv"},
                ],
                "voice_out": "vca.audio",
            },
            "global": {"nodes": [], "wires": []},
        }
        src = generate(patch)
        cname = patch["name"]
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "dsp.c").write_text(src)
            (d / "harness.c").write_text(DUMP_HARNESS.replace("__NAME__", cname))
            proc = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    *_include_args(),
                    "-o",
                    str(d / "t"),
                    str(d / "harness.c"),
                    str(d / "dsp.c"),
                    "-lm",
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise AssertionError("compile failed:\n" + proc.stderr)
            run = subprocess.run([str(d / "t")], capture_output=True, text=True)
            samples = [int(x) for x in run.stdout.split()]
        # scan 200..4000 Hz for the peak (sine), return its frequency
        f0 = fs * 42852281 / (1 << 32)  # note 69 = 440 Hz
        lo, hi = max(20.0, f0 / 4.0), min(fs / 2.0, f0 * 16.0)
        best_f, best_m = 0.0, -1.0
        f = lo
        while f < hi:
            m = _goertzel(samples, f, fs)
            if m > best_m:
                best_m, best_f = m, f
            f *= 1.005
        return best_f

    f_oct1 = fundamental(1, 0, 0)
    f_oct0 = fundamental(0, 0, 0)
    ratio_oct = f_oct1 / f_oct0
    assert 1.98 <= ratio_oct <= 2.02, f"octave +1 ratio {ratio_oct:.3f} not ≈2"
    print(f"ok: tuned_phasor octave +1 doubles the fundamental ({ratio_oct:.3f})")

    # semi +12 is out of range (−11..+11) and clamps to semi +11 = 2^(11/12)
    f_semi = fundamental(0, 12, 0)
    ratio_semi = f_semi / f_oct0
    expect_semi = 2.0 ** (11.0 / 12.0)
    assert expect_semi * 0.99 <= ratio_semi <= expect_semi * 1.01, (
        f"semi +12 clamps to 2^(11/12): ratio {ratio_semi:.3f} vs {expect_semi:.3f}"
    )
    print(
        "ok: tuned_phasor semi +12 clamps to 2^(11/12) "
        f"({ratio_semi:.3f} vs {expect_semi:.3f})"
    )

    f_cent = fundamental(0, 1, 0)
    ratio_cent = f_cent / f_oct0
    expect = 2.0 ** (1.0 / 12.0)
    assert expect * 0.99 <= ratio_cent <= expect * 1.01, (
        f"semi +1 ratio {ratio_cent:.3f} not ≈2^(1/12)={expect:.3f}"
    )
    print(f"ok: tuned_phasor semi +1 ≈ 2^(1/12) ({ratio_cent:.3f} vs {expect:.3f})")

    f_cent100 = fundamental(0, 0, 100)
    ratio_cent100 = f_cent100 / f_oct0
    assert expect * 0.99 <= ratio_cent100 <= expect * 1.01, (
        f"cent +100 ratio {ratio_cent100:.3f} not ≈2^(1/12)={expect:.3f}"
    )
    print(
        f"ok: tuned_phasor cent +100 ≈ 2^(1/12) ({ratio_cent100:.3f} vs {expect:.3f})"
    )


def _phasor_detune() -> None:
    """The per-op `detune` (cents) on the phasor shifts the fundamental by an exact
    2^(cents/1200) ratio (via the fm1_detune_pitch table)."""
    fs = 44100.0

    def fundamental(detune: int) -> float:
        patch: Patch = {
            "name": f"detune_{detune}".replace("-", "m"),
            "voices": 1,
            "voice": {
                "nodes": [
                    {"id": "ph", "type": "phasor", "params": {"detune": detune}},
                    {"id": "osc", "type": "naive_osc", "params": {"shape": 1}},
                    {"id": "env", "type": "env"},
                    {"id": "vca", "type": "vca"},
                ],
                "wires": [
                    {"from": "ph.phase", "to": "osc.phase"},
                    {"from": "osc.audio", "to": "vca.audio"},
                    {"from": "env.cv", "to": "vca.cv"},
                ],
                "voice_out": "vca.audio",
            },
            "global": {"nodes": [], "wires": []},
        }
        src = generate(patch)
        cname = patch["name"]
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "dsp.c").write_text(src)
            (d / "harness.c").write_text(DUMP_HARNESS.replace("__NAME__", cname))
            proc = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    *_include_args(),
                    "-o",
                    str(d / "t"),
                    str(d / "harness.c"),
                    str(d / "dsp.c"),
                    "-lm",
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise AssertionError("compile failed:\n" + proc.stderr)
            run = subprocess.run([str(d / "t")], capture_output=True, text=True)
            samples = [int(x) for x in run.stdout.split()]
        f0 = fs * 42852281 / (1 << 32)
        lo, hi = max(20.0, f0 / 4.0), min(fs / 2.0, f0 * 16.0)
        best_f, best_m = 0.0, -1.0
        f = lo
        while f < hi:
            m = _goertzel(samples, f, fs)
            if m > best_m:
                best_m, best_f = m, f
            f *= 1.005
        return best_f

    f0 = fundamental(0)
    f50 = fundamental(50)
    ratio = f50 / f0
    expect = 2.0 ** (50.0 / 1200.0)
    assert expect * 0.99 <= ratio <= expect * 1.01, (
        f"detune +50c ratio {ratio:.4f} not ≈ {expect:.4f}"
    )
    print(f"ok: phasor detune +50c ≈ 2^(50/1200) ({ratio:.4f} vs {expect:.4f})")


def main() -> int:
    failures: int = 0

    ok, msg = _compile(POCKET_DRONE)
    print(
        ("ok: " if ok else "FAIL: ")
        + ("pocket-drone (two-op FM) compiles" if ok else msg)
    )
    failures += 0 if ok else 1

    ok, msg = _sound(SINE_ENV)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "sine_env renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _sound(WAVEFORM)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "osc waveform (double half sine) renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _sound_tables(ROUTE4_TEST)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "route4 + mix4 render non-silent then silent")
    )
    failures += 0 if ok else 1

    # the dogfood patch itself (examples/fourop-fm/patch.json) renders.
    ffm = as_patch(
        json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "examples"
                / "fourop-fm"
                / "patch.json"
            ).read_text(encoding="utf-8")
        )
    )
    ok, msg = _sound_decay_tables(ffm)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "fourop-fm (4-op FM) renders non-silent then decays to near-silence")
    )
    failures += 0 if ok else 1

    # the INIT PATCH/PART defaults emit as a per-part-expanded init table
    hdr = generate_dsp_header(ffm)
    if (
        "fourop_fm_init_entry fourop_fm_init[]" in hdr
        and "fourop_fm_INIT_N" in hdr
        and "{ 186u, 7 }" in hdr  # algorithm 7 (the additive algorithm)
        and "{ 0u, 65536 }" in hdr  # op1 ratio, part 0
        and "{ 93u, 65536 }" in hdr  # op1 ratio, part 1 (per-part expansion)
    ):
        print("ok: the init: table emits (algorithm 7 + per-part op params)")
    else:
        print("FAIL: the init: table did not emit correctly")
        failures += 1

    ok, msg = _algorithms_render(ffm)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "fourop-fm renders non-silent across all 8 algorithms")
    )
    failures += 0 if ok else 1

    # the velocity contract: a higher-velocity note is louder (the `velocity`
    # reserved input, routed through the operator's vel_amp depth).
    ok, msg = _velocity_responds(VEL_PATCH)
    print(
        ("ok: " if ok else "FAIL: ") + (msg or "velocity scales the operator amplitude")
    )
    failures += 0 if ok else 1

    # the level taper: 0 = silence, 99 = maximum, 50 = a meaningful middle.
    ok, msg = _level_taper()
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "level taper: 0 silence / 99 max / 50 half")
    )
    failures += 0 if ok else 1

    # velocity → envelope rate: a higher-velocity note attacks faster.
    ok, msg = _velocity_rate_responds(VEL_RATE_PATCH)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "velocity scales the operator envelope rate")
    )
    failures += 0 if ok else 1

    # retrigger: a note-on that steals a sounding voice resets its envelope.
    ok, msg = _retrigger_on_steal(RETRIG_PATCH)
    print(
        ("ok: " if ok else "FAIL: ") + (msg or "a voice steal retriggers the envelope")
    )
    failures += 0 if ok else 1

    # voice modes: mono (one voice, last-note priority, takeover) + unison (stack).
    ok, msg = _modes_behave(MODE_PATCH)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "mono priority/takeover + unison stacking")
    )
    failures += 0 if ok else 1

    # legato: a mono overlap retriggers the envelope iff legato is off.
    ok, msg = _legato_behave(LEGATO_PATCH)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "legato holds the envelope across an overlap")
    )
    failures += 0 if ok else 1

    # portamento: a note change glides the pitch (constant rate) instead of snapping.
    ok, msg = _glide_ramps(GLIDE_PATCH)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "portamento glides the pitch instead of snapping")
    )
    failures += 0 if ok else 1

    # parts: a note routes by channel/keyzone and layers (omni fires every part).
    ok, msg = _parts_route(PARTS_PATCH)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "parts route by channel and layer (omni fires both parts)")
    )
    failures += 0 if ok else 1

    # per-part level (gain) + delay (onset offset).
    ok, msg = _parts_level_delay(PARTS_PATCH)
    print(("ok: " if ok else "FAIL: ") + (msg or "per-part level + delay"))
    failures += 0 if ok else 1

    # the six voice-mode params are per-part (mono/poly/unison independence).
    ok, msg = _parts_modes(PARTS_PATCH)
    print(("ok: " if ok else "FAIL: ") + (msg or "per-part voice modes"))
    failures += 0 if ok else 1

    # the per-op scope taps (the `taps:` sources, per part, mute-aware).
    ok, msg = _taps_expose()
    print(("ok: " if ok else "FAIL: ") + (msg or "per-op scope taps"))
    failures += 0 if ok else 1

    # the §12.1 set_param seam contract: bad-id rejection + value clamp.
    ok, msg = _set_param_contract(MODE_PATCH)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "set_param rejects bad ids and clamps values")
    )
    failures += 0 if ok else 1

    # per-part params occupy a `part × param` id space (part-major, contiguous).
    pids = param_ids(PARTS_PATCH)
    if pids.get("osc.waveform.p0") is None or pids.get("osc.waveform.p1") is None:
        print("FAIL: per-part voice params are not in the param id space")
        failures += 1
    elif pids["osc.waveform.p0"] != pids["osc.waveform.p1"] - 9:
        print("FAIL: per-part params are not part-major contiguous")
        failures += 1
    elif pids.get("channel.p0") is None or pids.get("channel.p1") is None:
        print("FAIL: per-part routing params are not in the param id space")
        failures += 1
    else:
        print("ok: per-part params are part-major (channel.p0/p1 present)")

    # the generated sysex-layout pins the per-firmware record geometry (F4c).
    from ._records import MULTI_SLOTS, PART_SLOTS
    from .generate import generate_sysex_layout

    layout = generate_sysex_layout(PARTS_PATCH)
    n_params = 9  # 3 voice params (phasor inc_ratio+detune, osc waveform) + 6 mode
    expect = {
        "model": 0,
        "n_params": n_params,
        "n_parts": 2,
        "part_patch_size": 1 + 16 + n_params * 4 + 4,
        "multi_patch_size": 1 + 16 + 2 + 5 * 2 * 4 + 4,
        "settings_size": 1 + 4 + 4 + 4,
        "part_patch_bank_size": PART_SLOTS * (1 + 16 + n_params * 4 + 4),
        "multi_patch_bank_size": MULTI_SLOTS * (1 + 16 + 2 + 5 * 2 * 4 + 4),
    }
    if layout != expect:
        print(f"FAIL: sysex-layout geometry is wrong ({layout})")
        failures += 1
    else:
        print("ok: sysex-layout pins the record geometry (9 params, 2 parts)")

    # the generated synth_layout.h carries the runtime constants the framework uses.
    from .generate import generate_synth_header

    hdr = generate_synth_header(PARTS_PATCH)
    want = (
        "#define SYNTH_MODEL 0u\n"
        "#define SYNTH_N_PARAMS 9u\n"
        "#define SYNTH_N_PARTS 2u\n"
        "#define SYNTH_N_GLOBAL 0u\n"
        "#define SYNTH_ROUTING_BASE (SYNTH_N_PARTS * SYNTH_N_PARAMS + SYNTH_N_GLOBAL)\n"
    )
    if want not in hdr:
        print("FAIL: synth_layout.h carries the wrong constants")
        failures += 1
    else:
        print("ok: synth_layout.h carries the runtime constants")

    # the fixed cc map: one CC per param, ascending from base 16, skipping the
    # reserved CCs (sustain 64 + the channel-mode 120..127).
    from .generate import cc_map_reverse, generate_cc_map

    cm = generate_cc_map(PARTS_PATCH)
    real = set(param_ids(PARTS_PATCH).values())
    mapped_ids = [e["param"] for e in cm["entries"]]
    mapped_ccs = [e["cc"] for e in cm["entries"]]
    reserved = {64} | set(range(120, 128))
    if not (
        cm["base"] == 16
        and set(mapped_ids) == real
        and len(mapped_ids) == len(real)
        and mapped_ccs == sorted(mapped_ccs)
        and all(c not in reserved and c <= 127 for c in mapped_ccs)
        and set(cc_map_reverse(cm)) == real
    ):
        print("FAIL: the cc map is not complete/ascending/reserved-free")
        failures += 1
    else:
        print(
            f"ok: the cc map covers {len(mapped_ids)} params from CC 16 "
            "(reserved skipped)"
        )
    try:
        generate_cc_map(PARTS_PATCH, base=120)
        print("FAIL: an overflowing cc map was not rejected")
        failures += 1
    except GenError:
        print("ok: an overflowing cc map is rejected")

    # a CC write through the generated cc_map.h table reaches the mapped param.
    ok, msg = _cc_map_reaches(PARTS_PATCH)
    print(("ok: " if ok else "FAIL: ") + (msg or "a CC write reaches its mapped param"))
    failures += 0 if ok else 1

    # the cc header also carries the per-param [min, max] (the MIDI handler's scaling).
    from .generate import generate_cc_header

    hdr = generate_cc_header(PARTS_PATCH)
    if (
        f"static const int32_t param_min[{len(mapped_ids)}]" not in hdr
        or f"static const int32_t param_max[{len(mapped_ids)}]" not in hdr
    ):
        print("FAIL: the cc header lacks the per-param ranges")
        failures += 1
    else:
        print("ok: the cc header carries the per-param [min, max] ranges")

    # the patch-level `cc:` list limits the CC map (the fourop patch's 173 params
    # overflow the CC space; it declares its 50-param surface).
    cm_sub = generate_cc_map(ffm)
    if len(cm_sub["entries"]) == 56 and all(
        e["cc"] != 64 and not 120 <= e["cc"] <= 127 for e in cm_sub["entries"]
    ):
        print("ok: the cc: list limits the map (56 exposed, reserved skipped)")
    else:
        print("FAIL: the cc: list does not limit the map as declared")
        failures += 1
    try:
        generate_cc_map({**ffm, "cc": ["not_a_param"]})
        print("FAIL: an unknown cc: name was not rejected")
        failures += 1
    except GenError:
        print("ok: an unknown cc: name is rejected")

    # the dogfood panel (examples/fourop-fm/panel.json) resolves against the patch's
    # params (every widget/binding names a real set_param id).
    ffm_panel = as_panel(
        json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "examples"
                / "fourop-fm"
                / "panel.json"
            ).read_text(encoding="utf-8")
        )
    )
    try:
        generate_panel(ffm_panel, param_ids(ffm))
        print("ok: fourop-fm panel.json resolves against the patch params")
    except GenError as exc:
        print(f"FAIL: fourop-fm panel.json does not resolve ({exc})")
        failures += 1

    # feedback is per-operator only (opN.fb.level). The earlier carrier-feedback
    # master (algo.car_fb → fb1..fb4, gated onto the carriers) was scrapped — its
    # nonzero default left a spurious feedback floor on every carrier. Assert the
    # leftover is gone: `algo` is now just the algorithm selector, and no carrier
    # gets a master feed.
    ffm_ids = param_ids(ffm)
    algo_spec = load_library(LIBRARY_ROOT)["algo"]
    ok = (
        "feedback" not in ffm_ids
        and "algo.car_fb" not in ffm_ids
        and ffm_ids.get("algorithm") == ffm_ids.get("algo.algorithm")
        and ffm_ids.get("op1_feedback") == ffm_ids.get("op1.fb.level")
        and set(algo_spec.outs) == {"alg"}
        and "car_fb" not in algo_spec.params
        and "fb1" not in algo_spec.outs
    )
    print(
        ("ok: " if ok else "FAIL: ")
        + "feedback is per-operator only (no carrier master / feedback floor)"
    )
    failures += 0 if ok else 1

    # control/audio separation: a control-only node runs once per block, never per
    # sample — its ports are all `control`/`event`, no `audio`. A library node must
    # not smuggle an audio port into a control computation (or vice versa).
    lib = load_library(LIBRARY_ROOT)
    sep_ok = True
    for name in ("cmul", "csum", "lfo", "dx_env", "env", "pitch_env", "algo"):
        spec = lib[name]
        kinds = [p.kind for p in spec.ins.values()]
        kinds += [p.kind for p in spec.outs.values()]
        if AUDIO in kinds:
            print(f"FAIL: {name} is control-rate but has an audio port")
            sep_ok = False
    for name in (
        "gain",
        "mix",
        "vca",
        "osc",
        "phasor",
        "svf",
        "wavefolder",
        "mute",
        "delay1",
        "mix4",
        "route4",
    ):
        spec = lib[name]
        kinds = [p.kind for p in spec.ins.values()]
        kinds += [p.kind for p in spec.outs.values()]
        if AUDIO not in kinds:
            print(f"FAIL: {name} is audio-rate but has no audio port")
            sep_ok = False
    print(
        ("ok: " if sep_ok else "FAIL: ")
        + "control/audio separation (control-only nodes carry no audio port)"
    )
    failures += 0 if sep_ok else 1

    ok, msg = _sound(SVF_WF)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "svf + wavefolder renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _lfo_varies(LFO_TEST)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "lfo oscillates (non-constant control output)")
    )
    failures += 0 if ok else 1

    ok, msg = _wave_shapes()
    print(("ok: " if ok else "FAIL: ") + (msg or "waveforms have the right shapes"))
    failures += 0 if ok else 1

    ok, msg = _mute_gates(MUTE_TEST)
    print(("ok: " if ok else "FAIL: ") + (msg or "mute gates the output"))
    failures += 0 if ok else 1

    ok, msg = _sound(FM_OP)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "shipped fm_op macro renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _pm_semantics()
    print(
        ("ok: " if ok else "FAIL: ")
        + (
            msg
            or (
                "phase modulation (not frequency integration): "
                "DC-safe + feedback survives"
            )
        )
    )
    failures += 0 if ok else 1

    ok, msg = _release_tail()
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "note-off keeps the voice and decays (release tail)")
    )
    failures += 0 if ok else 1

    ok, msg = _pitch_env()
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "per-note pitch envelope bends the pitch (on/off)")
    )
    failures += 0 if ok else 1

    ok, msg = _sound(LPG_TEST)
    print(("ok: " if ok else "FAIL: ") + (msg or "lpg renders non-silent then silent"))
    failures += 0 if ok else 1

    ok, msg = _sound(DX_ENV)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "dx_env rate/level envelope renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _sound(PHASE_SHAPE)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "phase_shape (VPS) renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _sound(PHASE_DIST)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "phase_dist (classic PD) renders non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _sound(NAIVE_VCO)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "naive_vco (naive oscillator) renders non-silent then silent")
    )
    failures += 0 if ok else 1

    # the octave/semi/cent tuning must be emitted as fm1_tune_q16 (per voice)
    src = generate(NAIVE_VCO)
    if "fm1_tune_q16(" not in src:
        print("FAIL: the note-derived tuning (fm1_tune_q16) was not emitted")
        failures += 1
    else:
        print("ok: the note-derived tuning (fm1_tune_q16) is emitted")

    try:
        _tune_pitch()
    except AssertionError as exc:
        print(f"FAIL: tuned_phasor tuning: {exc}")
        failures += 1

    try:
        _phasor_detune()
    except AssertionError as exc:
        print(f"FAIL: phasor detune: {exc}")
        failures += 1

    ok, msg = _sound_tables(TABLE_OSC)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "table node reads a wavetable + spectrum, non-silent then silent")
    )
    failures += 0 if ok else 1

    ok, msg = _sound(SAW_TEST)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "band-limited saw renders non-silent then silent")
    )
    failures += 0 if ok else 1

    # the saw's note-on reciprocal must be emitted in the generated dsp.c
    src = generate(SAW_TEST)
    if "0x100000000ull /" not in src:
        print("FAIL: the note-on reciprocal (2^32/inc) was not emitted")
        failures += 1
    else:
        print("ok: the note-on reciprocal (2^32/inc) is emitted")

    # the polyBLEP removes the wrap discontinuity: verify the max sample-to-sample
    # jump is slope-bounded, not the ~65535 full-scale jump of a naive saw.
    try:
        _saw_antialias()
    except AssertionError as exc:
        print(f"FAIL: polyBLEP anti-aliasing: {exc}")
        failures += 1

    ok, msg = _sound(PULSE_TEST)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "band-limited pulse renders non-silent then silent")
    )
    failures += 0 if ok else 1

    try:
        _pulse_antialias()
    except AssertionError as exc:
        print(f"FAIL: polyBLEP pulse anti-aliasing: {exc}")
        failures += 1

    try:
        _table_osc_antialias()
    except AssertionError as exc:
        print(f"FAIL: table-osc band-limited anti-aliasing: {exc}")
        failures += 1

    # the pulse width is a settable param (default 0.5 = square), not a wireable
    # control input — it must appear in the flattened param table with that default.
    width_params = [
        p for p in generate_params(PULSE_TEST)["params"] if p["name"].endswith(".width")
    ]
    if len(width_params) != 1 or width_params[0]["default"] != 16384:
        print(f"FAIL: pulse width is not a defaulted param ({width_params})")
        failures += 1
    else:
        print("ok: pulse width is a settable param (default 0.5)")

    # the modulatable set is the continuous Q-format knobs — phase_dist.d /
    # phase_shape.d (the phase-distortion bend), wavefolder.amount, and pulse.width.
    # Discrete indices (shape/waveform) are *not* modulatable (set via set_param).
    specs = load_library(LIBRARY_ROOT)
    want_mod = {
        "phase_dist": {"d"},
        "phase_shape": {"d"},
        "wavefolder": {"amount"},
        "pulse": {"width"},
    }
    got_mod = {n: specs[n].modulatable for n in want_mod}
    if got_mod != want_mod:
        print(f"FAIL: modulatable params drifted ({got_mod})")
        failures += 1
    else:
        print("ok: d/amount/width are the modulatable params")

    try:
        _modulation_works()
    except AssertionError as exc:
        print(f"FAIL: width modulation: {exc}")
        failures += 1

    ok, msg = _sound(TRIANGLE_TEST)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "band-limited triangle renders non-silent then silent")
    )
    failures += 0 if ok else 1

    try:
        _triangle_bandlimited()
    except AssertionError as exc:
        print(f"FAIL: polyBLEP triangle band-limiting: {exc}")
        failures += 1

    ok, msg = _sound(PITCHED_NOISE)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "pitched_noise renders non-silent then silent")
    )
    failures += 0 if ok else 1

    # the note-derived cutoff must be emitted as 2*sin(pi*inc/2^32) (per voice)
    src = generate(PITCHED_NOISE)
    if "fm1_sin((note_to_inc(voice_note[v])" not in src:
        print("FAIL: the note-derived cutoff (2*sin) was not emitted")
        failures += 1
    else:
        print("ok: the note-derived cutoff (2*sin) is emitted")

    # a single-harmonic spectrum must generate a pure-sine wavetable (the IFFT)
    from ._tables import build_tables

    sine = build_tables({"s": {"kind": "spectrum", "harmonics": [32767]}})[0]
    if sine.values[0] != 0 or not 32000 <= sine.values[64] <= 32767:
        print(
            f"FAIL: spectrum table is not a sine ({sine.values[0]}, {sine.values[64]})"
        )
        failures += 1
    else:
        print(
            f"ok: spectrum table is an IFFT sine "
            f"(peak {sine.values[64]} at index 64, size {sine.size})"
        )

    # the routing table is the 8-algorithm 4-op FM matrix (8 × 5 rows × 4 weights).
    rt = build_tables({"routing": {"kind": "routing"}})[0]
    ok = rt.size == 8 * 5 * 4 and all(v in (0, 32767) for v in rt.values)
    # the 8 rows are indexed 0..7 (ymfm algs 0..7).
    alg0_carrier = rt.values[
        0 * 20 + 4 * 4 : 0 * 20 + 4 * 4 + 4
    ]  # stack → carrier [0,0,0,1]
    alg7_carrier = rt.values[
        7 * 20 + 4 * 4 : 7 * 20 + 4 * 4 + 4
    ]  # additive → [1,1,1,1]
    alg3_mod = rt.values[
        3 * 20 + 1 * 4 : 3 * 20 + 1 * 4 + 4
    ]  # ((O1->O2)+O3)->O4 → op1 modulates op2
    alg4_mod = rt.values[
        4 * 20 + 1 * 4 : 4 * 20 + 1 * 4 + 4
    ]  # two-pairs → op1 modulates op2
    ok = (
        ok
        and alg0_carrier == [0, 0, 0, 32767]
        and alg7_carrier == [32767, 32767, 32767, 32767]
        and alg3_mod == [32767, 0, 0, 0]
        and alg4_mod == [32767, 0, 0, 0]
    )
    if not ok:
        print(f"FAIL: routing table is wrong (size {rt.size}, alg0={alg0_carrier})")
        failures += 1
    else:
        print("ok: routing table is the 8-algorithm 4-op FM matrix (160 × 0/1)")

    bad: Patch = {
        "name": "bad",
        "voices": 1,
        "voice": {
            "nodes": [
                {"id": "ph", "type": "phasor"},
                {"id": "osc", "type": "osc"},
                {"id": "env", "type": "env"},
            ],
            "wires": [
                {"from": "ph.phase", "to": "osc.phase"},
                {"from": "osc.audio", "to": "env.gate"},  # audio -> event
            ],
        },
        "global": {"nodes": [], "wires": []},
    }
    try:
        generate(bad)
        print("FAIL: audio->event edge not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: audio->event edge rejected ({exc})")

    # a node id colliding with a reserved allocator input is a GenError (not a
    # silently-skipped wire).
    reserved_id: Patch = {
        "name": "reserved_id",
        "voices": 1,
        "voice": {
            "nodes": [{"id": "gate", "type": "osc"}],
            "wires": [],
        },
        "global": {"nodes": [], "wires": []},
    }
    try:
        generate(reserved_id)
        print("FAIL: reserved node id 'gate' not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: reserved node id rejected ({exc})")

    # a scope tap must name an audio-rate voice-zone output
    tap_patch: Patch = {
        "name": "tap_val",
        "voices": 1,
        "voice": {
            "nodes": [{"id": "osc", "type": "osc"}],
            "wires": [],
            "voice_out": "osc.audio",
        },
        "global": {"nodes": [], "wires": []},
    }
    try:
        generate({**tap_patch, "taps": ["nope.audio"]})
        print("FAIL: an unknown tap node was not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: unknown tap node rejected ({exc})")
    try:
        generate({**tap_patch, "taps": ["osc.phase"]})
        print("FAIL: a tap naming an input was not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: tap naming an input rejected ({exc})")

    # the flattened param table maps a named param to its set_param id
    params = generate_params(POCKET_DRONE)["params"]
    by_name = {p["name"]: p for p in params}
    lp = by_name.get("lp.cutoff")
    # `lp` is the last node in pocket-drone's graph, so its cutoff is the last
    # *node* id; the six universal voice-mode params (`vm_*`) are appended after it
    # (robust against param additions to earlier nodes — e.g. osc.waveform, vca.level).
    n_mode = 6
    if lp is None or lp["id"] != len(params) - 1 - n_mode:
        print("FAIL: params.json does not map lp.cutoff to the last node id")
        failures += 1
    else:
        print(f"ok: params.json maps lp.cutoff -> id {lp['id']}")
    if [p["name"] for p in params[-n_mode:]] != [
        "mode",
        "unison_count",
        "unison_detune",
        "legato",
        "portamento",
        "note_priority",
    ]:
        print("FAIL: the universal voice-mode params are not appended last")
        failures += 1
    else:
        print("ok: the six universal voice-mode params are appended last")

    # the params: manifest binds a friendly name to a flattened param + metadata
    params = generate_params(TABLE_DEMO)["params"]
    cutoff = next(p for p in params if p["target"] == "lp.cutoff")
    if cutoff["name"] != "cutoff" or cutoff["min"] != 0 or cutoff["unit"] != "Hz":
        print("FAIL: params.json does not bind cutoff -> lp.cutoff with metadata")
        failures += 1
    else:
        print(
            f"ok: params.json binds cutoff -> {cutoff['target']} "
            f"(unit={cutoff['unit']})"
        )

    # the friendly name and the target share one set_param id
    ids = param_ids(TABLE_DEMO)
    if ids["cutoff"] != ids["lp.cutoff"]:
        print("FAIL: friendly name and target do not share a set_param id")
        failures += 1
    else:
        print(f"ok: cutoff and lp.cutoff share set_param id {ids['cutoff']}")

    # the dsp.c carries the dsp_param metadata table
    src = generate(TABLE_DEMO)
    if "dsp_param" not in src or "table_demo_dsp_params" not in src:
        print("FAIL: dsp.c lacks the dsp_param metadata table")
        failures += 1
    else:
        print("ok: dsp.c emits the dsp_param metadata table")

    # tables: -> tables.h + tables.c that compile
    hdr, impl = generate_tables(TABLE_DEMO)
    ok, msg = _compile_tables(hdr, impl)
    print(("ok: " if ok else "FAIL: ") + ("tables.c compiles" if ok else msg))
    failures += 0 if ok else 1

    # a params: target that does not resolve is a GenError
    bad_params: Patch = {**TABLE_DEMO, "params": {"ghost": {"target": "nope.x"}}}
    try:
        generate(bad_params)
        print("FAIL: unknown params: target not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: unknown params: target rejected ({exc})")

    # a node body referencing an undeclared table is a GenError
    try:
        _table_placeholder_resolves()
        print("ok: ${table.<name>} resolves and rejects an unknown table")
    except AssertionError as exc:
        print(f"FAIL: table placeholder: {exc}")
        failures += 1

    ok, msg = _voice_ceiling()
    print(("ok: " if ok else "FAIL: ") + (msg or "voice ceiling + steal policy"))
    failures += 0 if ok else 1

    ok, msg = _asan_clean()
    print(("ok: " if ok else "FAIL: ") + (msg or "generated DSP is sanitizer-clean"))
    failures += 0 if ok else 1

    print("generator tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
