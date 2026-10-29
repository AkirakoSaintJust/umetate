/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate)
 *
 * Fixed-point math contract + hardware acceleration (docs/roadmap.md P2-3).
 * Integer-first, "Q in the name" (dsp-study §6). Two parts:
 *
 *   1. Saturating Q arithmetic + the transcendental tables — integer only, safe
 *      to include anywhere (no float, no heap).
 *   2. The FFT (kiss_fft, float) — opt-in: define FM1_MATH_FFT in the one TU that
 *      needs it (the DSP TU; the generator's live `ifft` node). Float stays out
 *      of every other object (the "no FP leaks" rule).
 *
 * Hardware mapping (target only): the saturating Q arithmetic is portable C; the
 * SDK's hw vector DSP (vendor/jieli/fftvec_math_drv.h, nn_function_vec) and the
 * hw FFT (libFFT_pi32v2_OnChip.a via hwfft_*) are the accelerated paths, wired in
 * P2-8. The tables below are `const` XIP (gen/math_tables.h, generated).
 */
#pragma once
#include <stdint.h>
#include "math_tables.h"                       /* fm1_sin_q15 / fm1_exp2_q16 / fm1_log2_q16 */
#include "wavetable.h"                         /* fm1_wave (the 12-wave OPZ+OPL union) */
#include "analog_wave.h"                       /* fm1_analog_wave (the 4 analogue shapes) */

/* These helpers must inline into the hot loop: `.dsp_text` (SRAM) may not call into
 * XIP flash (a flash write would hang the core). `always_inline` makes the intent
 * non-negotiable — a `static inline` alone was not enough for the pi32v2 clang. */
#define FM1_MATH_INLINE static inline __attribute__((always_inline))

/* --------------------------------------------------- saturating Q arithmetic */

/* Q15 x Q15 -> Q15, rounded. The per-sample multiply for Q15 signals/levels. */
FM1_MATH_INLINE int32_t fm1_q15_mul(int32_t a, int32_t b)
{
    return (int32_t)(((int64_t)a * b + (1 << 14)) >> 15);
}

/* Q16 x Q16 -> Q16, rounded (gains, coefficients). */
FM1_MATH_INLINE int32_t fm1_q16_mul(int32_t a, int32_t b)
{
    return (int32_t)(((int64_t)a * b + (1 << 15)) >> 16);
}

/* Q31 x Q31 -> Q31, rounded. */
FM1_MATH_INLINE int32_t fm1_q31_mul(int32_t a, int32_t b)
{
    return (int32_t)(((int64_t)a * b + (1 << 30)) >> 31);
}

/* Rounding right shift (the SDK's PSHR). */
FM1_MATH_INLINE int32_t fm1_shr_round(int32_t x, int shift)
{
    return (x + (1 << (shift - 1))) >> shift;
}

/* Saturating 32-bit add/sub (accumulation never wraps). */
FM1_MATH_INLINE int32_t fm1_sat_add32(int32_t a, int32_t b)
{
    int32_t r = (int32_t)((uint32_t)a + (uint32_t)b);
    if (((a ^ r) & (b ^ r)) < 0)
        return a < 0 ? INT32_MIN : INT32_MAX;
    return r;
}

FM1_MATH_INLINE int32_t fm1_sat_sub32(int32_t a, int32_t b)
{
    int32_t r = (int32_t)((uint32_t)a - (uint32_t)b);
    if (((a ^ b) & (a ^ r)) < 0)
        return a < 0 ? INT32_MIN : INT32_MAX;
    return r;
}

/* Saturating multiply-accumulate: acc += (a * b) >> shift. */
FM1_MATH_INLINE int32_t fm1_madd_sat(int32_t acc, int32_t a, int32_t b, int shift)
{
    int32_t p = (int32_t)(((int64_t)a * b + ((int64_t)1 << (shift - 1))) >> shift);
    return fm1_sat_add32(acc, p);
}

/* ------------------------------------------------------ transcendental tables */

/* Full-cycle sine, Q15, from the quarter table (fm1_sin_q15, midpoint-sampled).
 * `phase` is Q32 (wrapping accumulator: inc = f * 2^32 / FS). */
FM1_MATH_INLINE int32_t fm1_sin(uint32_t phase)
{
    uint32_t q = phase >> 30;                 /* quadrant 0..3 */
    uint32_t i = (phase >> 22) & 255u;        /* 8-bit index into the 256-entry table */
    int32_t v = fm1_sin_q15[q & 1u ? 255u - i : i];
    return (q & 2u) ? -v : v;
}

FM1_MATH_INLINE int32_t fm1_cos(uint32_t phase) { return fm1_sin(phase + 0x40000000u); }

/* The 12-waveform union of the OPZ (YM2414) and OPL2/OPL3 (YM3812) sets, from
   ymfm's `opz_registers` and `opl_registers_base` constructors (BSD-3-Clause,
   re-implemented in linear Q15). `phase` is Q32 (full cycle); `ws` is 0..11.
   0-7 are the OPZ set (sine, triangle, half sine, half triangle, double sine,
   double triangle, double half sine, double half triangle); 8-11 are the OPL-only
   shapes (rectified |sin|, pulse, square, saw). A bad `ws` degrades to sine.
   Precomputed into gen/wavetable.h (`fm1_wave[12 * 1024]`, tools/gen_wavetable.py):
   one load per sample, no switch. The `(ws << 10)` base is block-rate — the
   oscillator node hoists it with its block_derived. */
FM1_MATH_INLINE int32_t fm1_sin_wave(uint32_t phase, uint32_t ws)
{
    return fm1_wave[((ws & 15u) << 10) | (phase >> 22)];
}

/* 4-input weighted sum against a routing-matrix row (a `const int16_t *` of four
   0/1 Q15 weights): out = a*w0 + b*w1 + c*w2 + d*w3. */
FM1_MATH_INLINE int32_t fm1_route4(const int16_t *w, int32_t a, int32_t b, int32_t c, int32_t d)
{
    return fm1_q15_mul(a, w[0]) + fm1_q15_mul(b, w[1])
         + fm1_q15_mul(c, w[2]) + fm1_q15_mul(d, w[3]);
}

/* fm1_exp2_q16[i] = 2^(-i/256) in Q16  (exponential decay: envelopes, note-to-inc).
 * fm1_log2_q16[i] = log2(1 + i/256) in Q16  (log-domain FM). Both indexed directly. */

/* ------------------------------------------------------ ROM transcendentals */
/* The pi32v2's on-chip ROM math (driver/cpu/wl82/asm/math.h, Apache-2.0): hardware
 * routines, NOT lookup tables. JieLi Q-notation — `aQ` is the input Q-format, `rQ`
 * the output's. The angle unit + exact Q mapping are the JieLi convention, pinned
 * when P2-8 emits coefficient computation (it has the SDK docs). Control-rate /
 * accuracy-sensitive use; the LUT fm1_sin above stays the per-sample hot loop. */
#if defined(UMETATE_TARGET)
#include "jieli/math.h"
#define fm1_cos_sin(a, aQ, rsin, rcos, rQ)  math_cos_sin(a, aQ, rsin, rcos, rQ)
#define fm1_atan2(y, x, r, rQ)              math_atan2(y, x, r, rQ)
#define fm1_exp(a, aQ, r, rQ)               math_exp(a, aQ, r, rQ)
#define fm1_log(a, aQ, r, rQ)               math_log(a, aQ, r, rQ)
#define fm1_sqrt(a, aQ, r, rQ)              math_sqrt(a, aQ, r, rQ)
#endif

/* ------------------------------------------------------- FFT (float, opt-in) */
#ifdef FM1_MATH_FFT
#include "kiss_fft/kiss_fft.h"
typedef kiss_fft_cfg fm1_fft_cfg;
typedef kiss_fft_cpx fm1_fft_cpx;
#define fm1_fft_alloc(nfft, inverse, mem, lenmem) kiss_fft_alloc(nfft, inverse, mem, lenmem)
#define fm1_fft(cfg, in, out) kiss_fft(cfg, in, out)
#define fm1_fft_free kiss_fft_free
#define fm1_fft_next_fast_size kiss_fft_next_fast_size
#endif
