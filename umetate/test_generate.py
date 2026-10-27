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

import math
import subprocess
import sys
import tempfile
from pathlib import Path

from ._ir import GenError
from ._schema import Patch
from .generate import generate, generate_params, generate_tables, param_ids

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
            {"id": "carrier", "type": "op", "params": {"ratio": 1}},
            {"id": "mod", "type": "op", "params": {"ratio": 2}},
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
            {"id": "carrier", "type": "fm_op", "params": {"ratio": 1}},
            {"id": "mod", "type": "fm_op", "params": {"ratio": 2}},
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
        "nodes": [{"id": "carrier", "type": "sawop", "params": {"ratio": 1}}],
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

    ok, msg = _sound(SVF_WF)
    print(
        ("ok: " if ok else "FAIL: ")
        + (msg or "svf + wavefolder renders non-silent then silent")
    )
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

    # the note-derived cutoff must be emitted as 2*sin(pi*inc/2^32)
    src = generate(PITCHED_NOISE)
    if "fm1_sin((note_to_inc(note)" not in src:
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
    if lp is None or lp["id"] != 4:
        print("FAIL: params.json does not map lp.cutoff to id 4")
        failures += 1
    else:
        print(f"ok: params.json maps lp.cutoff -> id {lp['id']}")

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
