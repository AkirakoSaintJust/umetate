#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Generate gen/wavetable.h, the 12-waveform OPZ+OPL union, band-limited for
pulse/square/saw.

The layout (one contiguous Q15 table, `fm1_wave`):
  - waves 0-8 (the sin-derived OPZ set + rectified |sin|): one 1024-sample table
    each. They are band-limited by construction (sin and its rectified/doubled
    derivatives have finite harmonic content), so they need no anti-aliasing.
  - waves 9 (pulse), 10 (square), 11 (saw): MIP=6 band-limited tables each, with
    harmonic counts 2^5..2^0 (32,16,8,4,2,1), the "multitable" anti-aliasing
    fix for the top octaves. Each is an additive (truncated-Fourier / offline
    IFFT) synthesis of the *naive* shape, so the highest harmonics that would
    otherwise alias above Nyquist are simply not present, and the oscillator picks
    the level whose top harmonic sits below Nyquist for the current note.

`fm1_wave_base[12]` gives each waveform's mip-0 offset (in 1024-sample units),
and a reader adds `mip << 10` for waves 9..11. Total 27648 samples (54 KB, const
XIP).

The output is deterministic, and it is checked in (as gen/wavetable.h).

Run from the firmware root:  python3 tools/gen_wavetable.py
"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "gen" / "wavetable.h"
N = 1024  # samples per table (10-bit phase index, matching fm1_sin's resolution)
MIP = 6  # band-limited mip levels for pulse/square/saw
BL_WAVES = (9, 10, 11)  # the waves that get mip-mapped band-limited tables


def q15(x: float) -> int:
    v = int(round(x * 32768.0))
    return max(-32768, min(32767, v))


def clamp15(x: float) -> int:
    """Round an already-Q15 value and clamp it into [-32768, 32767]."""
    v = int(round(x))
    return max(-32768, min(32767, v))


# the quarter sine, identical to gen_math_tables.py's fm1_sin_q15
SIN = [q15(math.sin(math.pi / 2.0 * i / 256)) for i in range(256)]


def fm1_sin(phase: int) -> int:
    q = (phase >> 30) & 3
    i = (phase >> 22) & 255
    v = SIN[255 - i] if (q & 1) else SIN[i]
    return -v if (q & 2) else v


def q15_mul(a: int, b: int) -> int:
    return (a * b + (1 << 14)) >> 15


def sin_wave(phase: int, ws: int) -> int:
    """The exact C fm1_sin_wave(phase, ws) as a pure function of the top 10 bits."""
    s = fm1_sin(phase)
    a = -s if s < 0 else s
    half = (phase >> 31) & 1
    q = (phase >> 30) & 3
    if ws == 0:
        return s
    if ws == 1:
        return q15_mul(s, a)                      # triangle (sin . |sin|)
    if ws == 2:
        return 0 if half else a                  # half sine
    if ws == 3:
        return 0 if half else q15_mul(s, a)      # half triangle
    if ws == 4:
        return 0 if half else fm1_sin((phase << 1) & 0xFFFFFFFF)   # double sine
    if ws == 5:
        s2 = fm1_sin((phase << 1) & 0xFFFFFFFF)
        return 0 if half else q15_mul(s2, -s2 if s2 < 0 else s2)   # double triangle
    if ws == 6:
        s2 = fm1_sin((phase << 1) & 0xFFFFFFFF)
        return 0 if half else (-s2 if s2 < 0 else s2)              # double half sine
    if ws == 7:
        s2 = fm1_sin((phase << 1) & 0xFFFFFFFF)
        return 0 if half else q15_mul(s2, s2)     # double half triangle (sin^2)
    if ws == 8:
        return a                                  # rectified |sin|
    if ws == 9:
        return 0 if (q & 1) else a                # pulse (half-rectified)
    if ws == 10:
        return -32767 if half else 32767          # square
    if ws == 11:
        return (phase >> 16) - 32768              # saw
    return s


def band_limited(ws: int, harm: int) -> list[int]:
    """The band-limited Q15 table for waveform `ws`, harmonics 1..harm (a
    truncated Fourier series, the offline IFFT). DC + sine + cosine
    coefficients are projected from the exact naive shape with a DFT, so the
    quirky OPL `pulse` (ws 9) is handled identically to square/saw, with no
    hand-derived series. The result keeps the naive shape's exact harmonic
    amplitudes, and the Gibbs overshoot at a discontinuity is clamped to
    full-scale."""
    a = [0.0] * (harm + 1)
    b = [0.0] * (harm + 1)
    for k in range(harm + 1):
        sa = sb = 0.0
        for i in range(N):
            ang = 2.0 * math.pi * k * i / N
            v = sin_wave(i << 22, ws)
            sa += v * math.cos(ang)
            sb += v * math.sin(ang)
        a[k] = sa * 2.0 / N
        b[k] = sb * 2.0 / N
    out: list[int] = []
    for i in range(N):
        ang = 2.0 * math.pi * i / N
        total = a[0] * 0.5  # the DC term (a_0/2 = the mean)
        for k in range(1, harm + 1):
            total += a[k] * math.cos(k * ang) + b[k] * math.sin(k * ang)
        out.append(clamp15(total))
    return out


def c_array(name: str, ctype: str, values: list[int]) -> list[str]:
    lines = [f"static const {ctype} {name}[{len(values)}] = {{"]
    row: list[str] = []
    for v in values:
        row.append(f"{v:>6d}")
        if len(row) == 16:
            lines.append("    " + ", ".join(row) + ",")
            row = []
    if row:
        lines.append("    " + ", ".join(row) + ",")
    lines.append("};")
    return lines


def main() -> None:
    wave: list[int] = []
    base: list[int] = []
    for ws in range(12):
        base.append(len(wave) // N)  # the mip-0 offset (units of N samples)
        if ws in BL_WAVES:
            for mip in range(MIP):
                wave.extend(band_limited(ws, 1 << (MIP - 1 - mip)))
        else:
            for p in range(N):
                wave.append(sin_wave(p << 22, ws))

    h = [
        "/* SPDX-License-Identifier: GPL-3.0-only",
        " * Copyright (C) 2026 P1Onken (umetate)",
        " * GENERATED by tools/gen_wavetable.py, do not edit by hand.",
        " * The 12-waveform OPZ (YM2414) + OPL (YM3812) union, Q15.",
        " * Waves 0-8 are one 1024-sample table each; waves 9 (pulse), 10 (square),",
        " * 11 (saw) are MIP=6 band-limited tables (harmonic counts 32..1) for the",
        " * top-octave anti-aliasing. `fm1_wave_base[ws]` is ws's mip-0 offset in",
        " * 1024-sample units; the per-sample index is",
        " *   fm1_wave[(fm1_wave_base[ws] + mip) << 10 | (phase >> 22)].",
        " */",
        "#pragma once",
        "#include <stdint.h>",
        "",
    ]
    h += c_array("fm1_wave", "int16_t", wave)
    h += [""]
    h += c_array("fm1_wave_base", "uint8_t", base)
    OUT.write_text("\n".join(h) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(wave)} samples, {len(base)} wave bases)")


if __name__ == "__main__":
    main()
