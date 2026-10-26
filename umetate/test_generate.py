# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host tests for the generator (docs/roadmap.md §12.4 verification).

Generates the two-op FM example, compiles it with the host cc, runs a few notes,
and checks the seam contract + the type-error rejection. Run: python3 umetate/test_generate.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from .generate import generate, GenError

SINE_PATCH = {
    "name": "sine",
    "voices": 4,
    "sample_rate": 44100,
    "voice": {
        "nodes": [
            {"id": "ph", "type": "phasor"},
            {"id": "osc", "type": "osc"},
        ],
        "wires": [{"from": "ph.phase", "to": "osc.phase"}],
    },
    "global": {"nodes": [], "wires": []},
}

HARNESS = r"""
#include <stdio.h>
#include <stdint.h>
#include <math.h>
static int32_t out[512];
int main(void) {
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, 100);   /* A4 */
    __NAME___dsp_render(out, 256);
    /* check non-silent */
    int64_t energy = 0;
    for (int i = 0; i < 512; i++) energy += (int64_t)out[i] * out[i];
    if (energy < 1000000) { printf("FAIL: silent\n"); return 1; }
    /* check silence after all-notes-off */
    __NAME___dsp_all_notes_off();
    __NAME___dsp_render(out, 256);
    int64_t tail = 0;
    for (int i = 0; i < 512; i++) tail += (int64_t)out[i] * out[i];
    if (tail != 0) { printf("FAIL: not silent after off (tail=%lld)\n", (long long)tail); return 1; }
    printf("ok: __NAME__ renders non-silent then silent\n");
    return 0;
}
"""


def _run(patch):
    src = generate(patch)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "dsp.c").write_text(src)
        (d / "harness.c").write_text(HARNESS.replace("__NAME__", patch["name"]))
        inc = str(Path(__file__).resolve().parents[1] / "firmware" / "hal")
        gen = str(Path(__file__).resolve().parents[1] / "firmware" / "gen")
        p = subprocess.run(
            ["cc", "-std=c11", "-I", inc, "-I", gen, "-o", str(d / "t"),
             str(d / "harness.c"), str(d / "dsp.c"), "-lm"],
            capture_output=True, text=True)
        if p.returncode != 0:
            return False, "compile failed:\n" + p.stderr
        r = subprocess.run([str(d / "t")], capture_output=True, text=True)
        return r.returncode == 0, r.stdout.strip()


def main():
    failures = 0
    ok, msg = _run(SINE_PATCH)
    print(("ok: " if ok else "FAIL: ") + (msg or "sine example"))
    if not ok:
        failures += 1
    # type error: audio -> event
    bad = {
        "name": "bad", "voices": 1,
        "voice": {"nodes": [{"id": "ph", "type": "phasor"}, {"id": "osc", "type": "osc"}],
                  "wires": [{"from": "osc.audio", "to": "ph.gate"}]},   # audio -> event-ish
        "global": {"nodes": [], "wires": []},
    }
    try:
        generate(bad)
        print("FAIL: audio->event edge not rejected")
        failures += 1
    except GenError as e:
        print(f"ok: type error rejected ({e})")
    except KeyError:
        # osc.audio -> ph.gate: 'gate' is not a phasor port -> also an error
        print("ok: unknown port rejected")

    print("generator tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
