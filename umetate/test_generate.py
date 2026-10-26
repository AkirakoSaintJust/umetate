# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host tests for the generator (docs/roadmap.md §12.4 verification).

- pocket-drone (two-op FM, with the `op` macro + delay1 feedback + global chain)
  must *compile* for host (the acceptance is "compiles to a dsp.c that builds").
- a delay-free patch must render non-silent then silent (the seam contract).
- an audio->event edge must be rejected with a type error.
Run: python3 -m umetate.test_generate
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from .generate import generate, GenError

POCKET_DRONE = {
    "name": "pocket-drone",
    "voices": 8,
    "sample_rate": 44100,
    "macros": {
        "op": {
            "ins": {"gate": "event", "freq": "control", "fm": "audio"},
            "outs": {"audio": "audio"},
            "params": {"ratio": "ph.inc", "level": "vca.level"},
            "nodes": [
                {"id": "ph", "type": "phasor"},
                {"id": "osc", "type": "osc"},
                {"id": "env", "type": "env"},
                {"id": "vca", "type": "vca"},
            ],
            "wires": [
                {"from": "freq", "to": "ph.inc"},
                {"from": "fm", "to": "ph.fm"},
                {"from": "ph.phase", "to": "osc.phase"},
                {"from": "osc.audio", "to": "vca.audio"},
                {"from": "gate", "to": "env.gate"},
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
            {"from": "note", "to": "carrier.freq"},
            {"from": "note", "to": "mod.freq"},
            {"from": "gate", "to": "carrier.gate"},
            {"from": "gate", "to": "mod.gate"},
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

# a delay-free voice for the sound check (phasor -> osc -> env -> vca)
SINE_ENV = {
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

SOUND_HARNESS = r"""
#include <stdio.h>
#include <stdint.h>
static int32_t out[1024];
int main(void) {
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, 100);
    __NAME___dsp_render(out, 512);
    int64_t e = 0; for (int i = 0; i < 1024; i++) e += (int64_t)out[i] * out[i];
    if (e < 1000000) { printf("FAIL: silent\n"); return 1; }
    __NAME___dsp_all_notes_off();
    __NAME___dsp_render(out, 512);
    int64_t t = 0; for (int i = 0; i < 1024; i++) t += (int64_t)out[i] * out[i];
    if (t != 0) { printf("FAIL: not silent after off (tail=%lld)\n", (long long)t); return 1; }
    printf("ok: __NAME__ renders non-silent then silent\n");
    return 0;
}
"""


def _compile(patch):
    src = generate(patch)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "dsp.c").write_text(src)
        (d / "empty.c").write_text("int main(void){return 0;}\n")
        root = Path(__file__).resolve().parents[1]
        inc = str(root / "firmware" / "hal")
        gen = str(root / "firmware" / "gen")
        p = subprocess.run(["cc", "-std=c11", "-c", "-I", inc, "-I", gen,
                            "-o", str(d / "dsp.o"), str(d / "dsp.c")],
                           capture_output=True, text=True)
        return p.returncode == 0, p.stderr


def _sound(patch):
    src = generate(patch)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "dsp.c").write_text(src)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(SOUND_HARNESS.replace("__NAME__", cname))
        root = Path(__file__).resolve().parents[1]
        inc = str(root / "firmware" / "hal")
        gen = str(root / "firmware" / "gen")
        p = subprocess.run(["cc", "-std=c11", "-I", inc, "-I", gen, "-o", str(d / "t"),
                            str(d / "harness.c"), str(d / "dsp.c"), "-lm"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return False, "compile failed:\n" + p.stderr
        r = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return r.returncode == 0, r.stdout.strip()


def main():
    failures = 0

    ok, msg = _compile(POCKET_DRONE)
    print(("ok: " if ok else "FAIL: ") + ("pocket-drone (two-op FM) compiles" if ok else msg))
    if not ok:
        failures += 1

    ok, msg = _sound(SINE_ENV)
    print(("ok: " if ok else "FAIL: ") + (msg or "sine_env renders non-silent then silent"))
    if not ok:
        failures += 1

    bad = {
        "name": "bad", "voices": 1,
        "voice": {
            "nodes": [{"id": "ph", "type": "phasor"}, {"id": "osc", "type": "osc"},
                      {"id": "env", "type": "env"}],
            "wires": [{"from": "ph.phase", "to": "osc.phase"},
                      {"from": "osc.audio", "to": "env.gate"}],   # audio -> event
        },
        "global": {"nodes": [], "wires": []},
    }
    try:
        generate(bad)
        print("FAIL: audio->event edge not rejected")
        failures += 1
    except GenError as e:
        print(f"ok: audio->event edge rejected ({e})")

    print("generator tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
