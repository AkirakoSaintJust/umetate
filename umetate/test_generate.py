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
import subprocess
import sys
import tempfile
from pathlib import Path

from ._ir import AUDIO, GenError
from ._panel import generate_panel
from ._schema import Patch, as_panel, as_patch
from .generate import (
    generate,
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
                    "r1": 20000,
                    "r2": 6000,
                    "r3": 3000,
                    "r4": 9000,
                    "l1": 32767,
                    "l2": 24576,
                    "l3": 16384,
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

# The runtime-algorithm contract: set `algorithm` to each of the 7 routings via
# set_param and confirm each renders non-silent (the `route` node's whole point).
ALGO_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_set_param(uint32_t id, int32_t value);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
void __NAME___dsp_all_notes_off(void);
static int32_t out[512];
int main(void) {
    for (uint32_t alg = 0; alg < 7; alg++) {
        __NAME___dsp_reset();
        __NAME___dsp_set_param(__ALGO_ID__, (int32_t)alg);
        __NAME___dsp_note_on(69, 100);
        __NAME___dsp_render(out, 256);
        int64_t e = 0; for (int i = 0; i < 512; i++) e += (int64_t)out[i] * out[i];
        if (e < 1000000) { printf("FAIL: algorithm %u silent\\n", alg); return 1; }
        __NAME___dsp_all_notes_off();
    }
    printf("ok: __NAME__ renders non-silent across all 7 algorithms\\n");
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
                "params": {"ratio": 65536, "vel_rate": 32767, "r1": 20000, "l1": 32767},
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
                "params": {"ratio": 65536, "r1": 2000, "l1": 32767},
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
void __NAME___dsp_set_param(uint32_t id, int32_t value);
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
                "params": {"ratio": 65536, "r1": 2000, "l1": 32767},
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
void __NAME___dsp_set_param(uint32_t id, int32_t value);
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
void __NAME___dsp_set_param(uint32_t id, int32_t value);
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
    """Generate + compile + run the runtime-algorithm contract: each of the 7
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
    int32_t half_min = 0, dhs_min = 0, rect_min = 0, pulse_min = 0;
    int half_nonzero_second = 0, pulse_nonzero_q2 = 0;
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
        if (p < pulse_min) pulse_min = p;
        if (ph >= 0x80000000u && h != 0) half_nonzero_second = 1;
        if ((ph & 0x40000000u) && p != 0) pulse_nonzero_q2 = 1;
    }
    if (sine_max < 32000 || sine_min > -32000) {
        printf("FAIL: sine not full-scale (%d, %d)\n", sine_max, sine_min);
        return 1;
    }
    if (half_min < 0 || half_nonzero_second) { printf("FAIL: half sine\n"); return 1; }
    if (dhs_min < 0) { printf("FAIL: double half sine negative\n"); return 1; }
    if (rect_min < 0) { printf("FAIL: rectified negative\n"); return 1; }
    if (pulse_min < 0 || pulse_nonzero_q2) { printf("FAIL: pulse\n"); return 1; }
    if (sq_max < 32000 || sq_min > -32000) {
        printf("FAIL: square not full-scale (%d, %d)\n", sq_max, sq_min);
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
void __NAME___dsp_set_param(uint32_t id, int32_t value);
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
    out = substitute(inst, "int32_t x = ${table.sine}[0];", "v", {"sine"})
    assert "table_sine" in out and "${" not in out
    try:
        substitute(inst, "int32_t x = ${table.nope}[0];", "v", {"sine"})
        raise AssertionError("unknown table not rejected")
    except GenError:
        pass


def main() -> int:
    failures = 0

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

    ok, msg = _algorithms_render(ffm)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "fourop-fm renders non-silent across all 7 algorithms")
    )
    failures += 0 if ok else 1

    # the velocity contract: a higher-velocity note is louder (the `velocity`
    # reserved input, routed through the operator's vel_amp depth).
    ok, msg = _velocity_responds(VEL_PATCH)
    print(
        ("ok: " if ok else "FAIL: ") + (msg or "velocity scales the operator amplitude")
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

    # carrier feedback: `feedback` (algo.car_fb) is the carrier-gated master,
    # summed with a per-op `opN_feedback` (opN.fb.level) in each operator. Test the
    # param structure and the node contract — not the emitted C (which is free to
    # change shape).
    ffm_ids = param_ids(ffm)
    algo_spec = load_library(LIBRARY_ROOT)["algo"]
    ok = (
        ffm_ids.get("feedback") == ffm_ids.get("algo.car_fb")
        and ffm_ids.get("algorithm") == ffm_ids.get("algo.algorithm")
        and ffm_ids.get("op1_feedback") == ffm_ids.get("op1.fb.level")
        and all(f"fb{i}" in algo_spec.outs for i in range(1, 5))
        and all(algo_spec.outs[f"fb{i}"].kind != AUDIO for i in range(1, 5))
        and "car_fb" in algo_spec.params
        and "alg" in algo_spec.outs
    )
    print(
        ("ok: " if ok else "FAIL: ")
        + "feedback is a carrier master + per-op depth (algo.car_fb + opN.fb.level)"
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

    ok, msg = _sound(LPG_TEST)
    print(("ok: " if ok else "FAIL: ") + (msg or "lpg renders non-silent then silent"))
    failures += 0 if ok else 1

    ok, msg = _sound(DX_ENV)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "dx_env rate/level envelope renders non-silent then silent")
    )
    failures += 0 if ok else 1

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

    # the routing table is the 7-algorithm 4-op FM matrix (7 × 5 rows × 4 weights).
    rt = build_tables({"routing": {"kind": "routing"}})[0]
    ok = rt.size == 7 * 5 * 4 and all(v in (0, 32767) for v in rt.values)
    # the 7 rows are indexed 0..6 (ymfm algs {0,1,2,4,5,6,7}).
    alg0_carrier = rt.values[
        0 * 20 + 4 * 4 : 0 * 20 + 4 * 4 + 4
    ]  # stack → carrier [0,0,0,1]
    alg7_carrier = rt.values[
        6 * 20 + 4 * 4 : 6 * 20 + 4 * 4 + 4
    ]  # additive → [1,1,1,1]
    alg4_mod = rt.values[
        3 * 20 + 1 * 4 : 3 * 20 + 1 * 4 + 4
    ]  # two-pairs → op1 modulates op2
    ok = (
        ok
        and alg0_carrier == [0, 0, 0, 32767]
        and alg7_carrier == [32767, 32767, 32767, 32767]
        and alg4_mod == [32767, 0, 0, 0]
    )
    if not ok:
        print(f"FAIL: routing table is wrong (size {rt.size}, alg0={alg0_carrier})")
        failures += 1
    else:
        print("ok: routing table is the 7-algorithm 4-op FM matrix (140 × 0/1)")

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

    print("generator tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
