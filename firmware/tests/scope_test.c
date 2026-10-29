/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* Host test for the scope/spectrogram core (firmware/src/scope.c):
 * - the snapshot stores the left channel (clamped) and is readable back;
 * - a pure sine peaks in the right Goertzel bin (the spectrum is correct);
 * - a silent block reads back silent (no stray state);
 * - the spectrum cost fits the CPU0 budget (a coarse, relative bound). */
#define _POSIX_C_SOURCE 199309L
#include "scope.h"
#include "fm1_math.h"
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

static int failures;

static void ok(int cond, const char *what)
{
    printf("%s %s\n", cond ? "ok:" : "FAIL:", what);
    if (!cond)
        failures++;
}

/* a pure sine at `f` Hz into a stereo Q15 block */
static void fill_sine(int32_t *stereo, uint32_t n, uint32_t f)
{
    uint32_t inc = (uint32_t)(((uint64_t)f << 32) / SCOPE_FS), phase = 0, i;
    for (i = 0; i < n; i++) {
        int32_t s = fm1_sin(phase);
        stereo[2u * i] = s;
        stereo[2u * i + 1u] = -s;
        phase += inc;
    }
}

static double now_ms(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec * 1e3 + (double)t.tv_nsec / 1e6;
}

int main(void)
{
    static int32_t stereo[2u * SCOPE_N];
    static uint16_t mag[SCOPE_BINS];
    uint32_t i, peak;
    double t0, dt;

    /* 1. the snapshot stores the left channel (clamped to Q15). */
    fill_sine(stereo, SCOPE_N, 1000u);
    scope_push(stereo, SCOPE_N);
    ok(scope_at(0) == (int16_t)stereo[0], "snapshot: scope_at(0) is the left channel");
    ok(scope_at(SCOPE_N - 1u) == (int16_t)stereo[2u * (SCOPE_N - 1u)],
       "snapshot: scope_at(N-1) is the last left sample");

    /* 2. a silent block reads back silent (the snapshot is fully overwritten). */
    memset(stereo, 0, sizeof stereo);
    scope_push(stereo, SCOPE_N);
    ok(scope_at(0) == 0 && scope_at(SCOPE_N - 1u) == 0, "snapshot: a silent block is silent");

    /* 3. a pure 2000 Hz sine peaks in the bin covering 2000 Hz. */
    fill_sine(stereo, SCOPE_N, 2000u);
    scope_push(stereo, SCOPE_N);
    scope_spectrum(mag, SCOPE_BINS);
    peak = 0;
    for (i = 1; i < SCOPE_BINS; i++)
        if (mag[i] > mag[peak])
            peak = i;
    /* bin b covers (b+1)*fs/(2*nbins) = (b+1)*183.75 Hz; 2000 Hz -> ~9.9. */
    ok(peak >= 9u && peak <= 11u, "spectrum: 2000 Hz peaks at bin ~10");
    ok(mag[peak] > 0u && mag[0] < mag[peak], "spectrum: the peak bin dominates");

    /* 4. budget: 120 bins over 256 samples must be well under a UI frame (33 ms). */
    t0 = now_ms();
    for (i = 0; i < 8; i++)
        scope_spectrum(mag, SCOPE_BINS);
    dt = (now_ms() - t0) / 8.0;
    ok(dt < 8.0, "budget: scope_spectrum under 8 ms (a 30 Hz UI frame is 33 ms)");
    printf("        scope_spectrum: %.3f ms (%u bins)\n", dt, SCOPE_BINS);

    printf("%s\n", failures ? "SCOPE TEST FAILED" : "scope test passed");
    return failures != 0;
}
