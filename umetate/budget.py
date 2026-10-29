# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate budget` — measure the polyphony budget (roadmap §6.11.4, F6).

Generates the patch at each `--voices` count (and a forced `--parts` count),
compiles it for host, and times a worst-case `render(256)` — every voice sounding,
envelopes open. The host figure is a *relative* measure (per-voice cost and
linearity); the 2.9 ms device fit is the emulator's job (a built firmware, F7) and
is reported `blocked` until then. The voice count is a measured claim, not an
estimate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ._schema import Patch, as_patch
from .generate import generate, generate_tables

_ROOT = Path(__file__).resolve().parents[1]
_INCLUDES = [
    "-I",
    str(_ROOT / "firmware" / "hal"),
    "-I",
    str(_ROOT / "firmware" / "gen"),
]

_TIMING_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
#include <time.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
static int32_t out[512];
int main(void) {
    struct timespec t0, t1;
    double us;
    __NAME___dsp_reset();
    for (uint32_t n = 0; n < 128; n++) __NAME___dsp_note_on(n, 100);
    for (int s = 0; s < 16; s++) __NAME___dsp_render(out, 256);   /* envelopes open */
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int k = 0; k < 2000; k++) __NAME___dsp_render(out, 256);
    clock_gettime(CLOCK_MONOTONIC, &t1);
    us = (double)(t1.tv_sec - t0.tv_sec) * 1e6
       + (double)(t1.tv_nsec - t0.tv_nsec) / 1e3;
    printf("render256 %.3f\\n", us / 2000.0);
    return 0;
}
"""


def _measure(patch: Patch) -> float:
    """Generate + compile + time the worst-case render(256) (µs, host)."""
    src = generate(patch)
    tables_h, tables_c = generate_tables(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src)
        if tables_h:
            (d / "tables.h").write_text(tables_h)
            (d / "tables.c").write_text(tables_c)
        cname = patch["name"].replace("-", "_").replace(".", "_")
        (d / "harness.c").write_text(_TIMING_HARNESS.replace("__NAME__", cname))
        sources = [str(d / "harness.c"), str(d / "dsp.c")]
        if tables_c:
            sources.append(str(d / "tables.c"))
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-D_POSIX_C_SOURCE=199309L",
                "-O2",
                f"-I{d}",
                *_INCLUDES,
                "-o",
                str(d / "t"),
                *sources,
                "-lm",
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise SystemExit(
                f"budget: the generated dsp.c does not compile:\n{proc.stderr}"
            )
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        if run.returncode != 0:
            raise SystemExit(f"budget: the timing harness failed:\n{run.stdout}")
        line = run.stdout.strip()
        if not line.startswith("render256 "):
            raise SystemExit(f"budget: unexpected harness output {line!r}")
        return float(line.split()[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="umetate budget", description="measure the polyphony budget"
    )
    parser.add_argument("patch", help="patch.json (the engine to measure)")
    parser.add_argument(
        "--voices",
        default="",
        help="comma-separated voice counts (default: the patch's)",
    )
    parser.add_argument(
        "--parts", type=int, help="force the parts count (default: the patch's)"
    )
    args = parser.parse_args(argv)

    try:
        raw = json.loads(Path(args.patch).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"budget: cannot read patch {args.patch!r}: {exc}", file=sys.stderr)
        return 1
    patch = as_patch(raw)

    if args.voices:
        try:
            counts = [int(v) for v in args.voices.split(",")]
        except ValueError as exc:
            print(f"budget: bad --voices {args.voices!r}: {exc}", file=sys.stderr)
            return 1
    else:
        counts = [patch["voices"]]

    declared = patch.get("parts")
    parts_count = (
        args.parts if args.parts is not None else (declared["count"] if declared else 1)
    )
    print(f"budget: {args.patch} (parts {parts_count})")
    print(f"  {'voices':>6}  {'host render(256)':>17}  {'per voice':>10}")
    for n in counts:
        if n < 1:
            print(f"budget: bad voice count {n}", file=sys.stderr)
            return 1
        measured: Patch = {**patch, "voices": n}
        if args.parts is not None:
            measured["parts"] = {"count": args.parts}
        us = _measure(measured)
        print(f"  {n:>6}  {us:>14.1f} us  {us / n:>7.2f} us")

    print(
        "device fit (2.9 ms): measured by the emulator — `umetate emu --check "
        "--mhz 240` boots the built firmware and holds a chord (F7e); the host "
        "figures above are the relative per-voice measure."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
