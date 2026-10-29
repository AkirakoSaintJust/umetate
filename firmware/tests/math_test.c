/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate)
 * Host parity for hal/fm1_math.h (docs/roadmap.md P2-3): saturating Q arithmetic,
 * the sine/exp/log tables against libm, and a kiss_fft round-trip. The software
 * fallback here is the reference the emulator/device hw path must match. */
#include <stdio.h>
#include <math.h>
#include <stdint.h>
#include "fm1_math.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifdef FM1_MATH_FFT
#include "kiss_fft/kiss_fft.h"
#endif

static int failures;

static void ok(int cond, const char *what)
{
    printf("%s %s\n", cond ? "ok:" : "FAIL:", what);
    if (!cond)
        failures++;
}

int main(void)
{
    /* ---- saturating Q arithmetic ---- */
    ok(fm1_q15_mul(16384, 16384) == 8192, "q15_mul: 0.5*0.5 = 0.25");
    ok(fm1_q15_mul(32767, 32767) == 32766, "q15_mul: (1-eps)*(1-eps) stays in range");
    ok(fm1_q15_mul(-32768, 32768) == -32768, "q15_mul: -1.0*1.0 = -1.0");
    ok(fm1_q16_mul(65536, 32768) == 32768, "q16_mul: 1.0*0.5 = 0.5");
    ok(fm1_q31_mul(0x40000000, 0x40000000) == 0x20000000, "q31_mul: 0.5*0.5 = 0.25");
    ok(fm1_sat_add32(INT32_MAX, 1) == INT32_MAX, "sat_add32: saturates at INT32_MAX");
    ok(fm1_sat_add32(INT32_MIN, -1) == INT32_MIN, "sat_add32: saturates at INT32_MIN");
    ok(fm1_sat_sub32(INT32_MIN, 1) == INT32_MIN, "sat_sub32: saturates at INT32_MIN");
    ok(fm1_sat_add32(100000, 200000) == 300000, "sat_add32: no clamp in range");
    ok(fm1_shr_round(3, 1) == 2, "shr_round: 3>>1 rounds to 2");
    ok(fm1_shr_round(5, 2) == 1, "shr_round: 5>>2 rounds to 1");
    ok(fm1_madd_sat(100, 32768, 32768, 15) == 32868, "madd_sat: 100 + 1.0*1.0 in Q15");

    /* ---- sine parity (Q15 vs libm) ---- */
    {
        uint32_t i;
        int worst = 0;
        for (i = 0; i < 4096; i++) {
            uint32_t phase = i * 0x100000u;       /* 4096 samples over the cycle */
            int32_t approx = fm1_sin(phase);
            double exact = sin(2.0 * M_PI * (double)phase / 4294967296.0) * 32768.0;
            int err = (int)(approx - (int32_t)lrint(exact));
            if (err < 0)
                err = -err;
            if (err > worst)
                worst = err;
        }
        ok(worst <= 256, "sine: quarter-table within one bin (~256 LSB) of libm");
        ok(fm1_sin(0) == 0, "sine: phase 0 -> 0");
        ok(fm1_sin(0x40000000u) == 32767, "sine: phase pi/2 -> +1.0");
        ok(fm1_sin(0xC0000000u) == -32767, "sine: phase 3pi/2 -> -1.0");
        ok(fm1_cos(0) == 32767, "cos: phase 0 -> +1.0");
    }

    /* ---- exp/log tables ---- */
    ok(fm1_exp2_q16[0] == 65536 && fm1_exp2_q16[128] > 0, "exp2: 2^0 = 1.0, monotone");
    ok(fm1_log2_q16[0] == 0 && fm1_log2_q16[255] > 0, "log2: log2(1)=0, log2(1+255/256)>0");
    {
        int i, mono = 1;
        for (i = 1; i < 256; i++)
            if (fm1_exp2_q16[i] >= fm1_exp2_q16[i - 1])
                mono = 0;
        ok(mono, "exp2: strictly decreasing decay curve");
    }

    /* ---- tuning parity (fm1_tune_q16 vs libm) ---- */
    ok(fm1_tune_q16(0, 0, 0) == 65536, "tune: 0 oct / 0 semi / 0 cent = 1.0");
    ok(fm1_tune_q16(1, 0, 0) == 131072, "tune: +1 octave = 2.0");
    ok(fm1_tune_q16(-1, 0, 0) == 32768, "tune: -1 octave = 0.5");
    {
        static const struct { int o, s, c; } cases[] = {
            {0, 0, 0}, {1, 0, 0}, {-1, 0, 0}, {0, 12 - 12, 0}, {0, -11, 0},
            {0, 7, 0}, {0, 0, 100}, {0, 0, -100}, {2, 5, 42}, {-3, -11, -100},
            {3, 11, 100}, {0, 0, 50},
        };
        int k, worst = 0;
        for (k = 0; k < (int)(sizeof cases / sizeof cases[0]); k++) {
            int o = cases[k].o, s = cases[k].s, c = cases[k].c;
            int32_t approx = fm1_tune_q16(o, s, c);
            double exact = pow(2.0, o + s / 12.0 + c / 1200.0) * 65536.0;
            int err = (int)(approx - (int32_t)lrint(exact));
            if (err < 0) err = -err;
            if (err > worst) worst = err;
        }
        ok(worst <= 512, "tune: 2^(octave+semi/12+cent/1200) within ~512 LSB of libm");
    }

#ifdef FM1_MATH_FFT
    /* ---- FFT round-trip (kiss_fft, float) ---- */
    {
        enum { N = 64 };
        static char mem[8192];
        size_t memlen = sizeof mem;
        kiss_fft_cpx in[N], out[N], back[N];
        kiss_fft_cfg fwd = kiss_fft_alloc(N, 0, mem, &memlen);
        kiss_fft_cfg inv = kiss_fft_alloc(N, 1, NULL, NULL);
        int k, flat = 1, roundtrip = 1;
        if (!fwd || !inv) {
            ok(0, "fft: alloc");
            return 1;
        }
        /* impulse -> flat spectrum */
        for (k = 0; k < N; k++)
            in[k].r = in[k].i = 0;
        in[0].r = 1.0f;
        kiss_fft(fwd, in, out);
        for (k = 0; k < N; k++)
            if (fabsf(out[k].r - 1.0f) > 1e-4f || fabsf(out[k].i) > 1e-4f)
                flat = 0;
        ok(flat, "fft: impulse -> flat spectrum");
        /* sinusoid (8 cycles) -> a single peak at bin 8 and 56 */
        {
            int peak = 0;
            for (k = 0; k < N; k++) {
                in[k].r = sinf(2.0f * (float)M_PI * 8.0f * (float)k / (float)N);
                in[k].i = 0;
            }
            kiss_fft(fwd, in, out);
            for (k = 1; k < N; k++)
                if (out[k].r > out[peak].r)
                    peak = k;
            ok(peak == 8 || peak == 56, "fft: 8-cycle sinusoid peaks at bin 8/56");
        }
        /* round-trip: forward then inverse recovers the input / N */
        for (k = 0; k < N; k++) {
            in[k].r = (k % 7) - 3;
            in[k].i = (k % 5) - 2;
        }
        kiss_fft(fwd, in, out);
        kiss_fft(inv, out, back);
        for (k = 0; k < N; k++)
            if (fabsf(back[k].r / N - in[k].r) > 1e-3f || fabsf(back[k].i / N - in[k].i) > 1e-3f)
                roundtrip = 0;
        ok(roundtrip, "fft: forward+inverse round-trip / N");
    }
#else
    printf("note: FFT skipped (compile with -DFM1_MATH_FFT to test it)\n");
#endif

    printf("%s\n", failures ? "SOME TESTS FAILED" : "math test passed");
    return failures ? 1 : 0;
}
