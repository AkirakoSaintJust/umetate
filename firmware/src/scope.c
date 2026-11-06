/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate)
 *
 * The oscilloscope / spectrogram analysis core (docs/roadmap.md §6.10 planned
 * widgets). Pure integer, because the pi32v2 is soft-FP, and runs on CPU0 in the
 * UI path, never in the audio callback.
 *
 *   scope_push()        the audio ISR stores the left channel (ch 0, one block).
 *   scope_push_ch()     the app stores one per-op/per-part tap channel.
 *   scope_at[_ch]()     the scope widget reads a channel back (downsampled).
 *   scope_spectrum[_ch]()  a Goertzel bank at linearly-spaced bins -> Q15 magnitudes.
 *
 * The snapshot is one-writer (the ISR/app) / one-reader (the UI), so there is no
 * locking, the UI may read a block mid-update and show a torn frame, which is
 * harmless for a display (a bounded, non-blocking "last block" snapshot).
 */
#include "scope.h"
#include "fm1_math.h"                       /* fm1_cos (Q15 LUT) */

static int16_t scope_buf[SCOPE_CH][SCOPE_N];  /* the last SCOPE_N samples per channel (Q15) */
static int64_t scope_pw[SCOPE_BINS];        /* the Goertzel powers, one per bin */
static uint32_t scope_seq_n;

static void scope_store(uint32_t ch, const int32_t *mono, uint32_t n)
{
    uint32_t i;
    if (ch >= SCOPE_CH)
        return;
    if (n > SCOPE_N)
        n = SCOPE_N;
    for (i = 0; i < SCOPE_N; i++) {
        uint32_t j = n ? (i * n) / SCOPE_N : 0u;
        int32_t v = mono[j];
        scope_buf[ch][i] = (int16_t)(v > 32767 ? 32767 : v < -32767 ? -32767 : v);
    }
    scope_seq_n++;
}

void scope_push(const int32_t *stereo, uint32_t n)
{
    /* decimate the left channel (ch 0) into SCOPE_N points. */
    uint32_t i;
    if (n > SCOPE_N)
        n = SCOPE_N;
    for (i = 0; i < SCOPE_N; i++) {
        uint32_t j = n ? (i * n) / SCOPE_N : 0u;
        int32_t v = stereo[2u * j];
        scope_buf[0][i] = (int16_t)(v > 32767 ? 32767 : v < -32767 ? -32767 : v);
    }
    scope_seq_n++;
}

void scope_push_ch(uint32_t ch, const int32_t *mono, uint32_t n)
{
    scope_store(ch, mono, n);
}

uint32_t scope_seq(void) { return scope_seq_n; }

int16_t scope_at(uint32_t i)
{
    return scope_buf[0][i < SCOPE_N ? i : SCOPE_N - 1u];
}

int16_t scope_at_ch(uint32_t ch, uint32_t i)
{
    return scope_buf[ch < SCOPE_CH ? ch : 0u][i < SCOPE_N ? i : SCOPE_N - 1u];
}

/* Goertzel *power* (|X|^2) at frequency f over a channel's snapshot. `k` is
 * 2*cos(2*pi*f/fs) in Q15 ([-65536, 65536], an int32); the states stay < ~2^31
 * for a 256-point window. Integer throughout, int64 for the products. */
static int64_t scope_goertzel_power(uint32_t ch, uint32_t f, uint32_t fs)
{
    uint32_t phase = (uint32_t)(((uint64_t)f << 32) / fs);
    int32_t k = (int32_t)((uint32_t)fm1_cos(phase) << 1);
    int32_t s0 = 0, s1 = 0, s2 = 0;
    uint32_t i;
    for (i = 0; i < SCOPE_N; i++) {
        int32_t xn = scope_buf[ch][i];
        s0 = xn + (int32_t)(((int64_t)k * s1) >> 15) - s2;
        s2 = s1;
        s1 = s0;
    }
    return (int64_t)s1 * s1 + (int64_t)s2 * s2 - (((int64_t)k * s1 * s2) >> 15);
}

/* integer log2 (the highest set bit): a log-power scale for the spectrogram.
 * each step is 6 dB, which is how the ear hears power. Avoids the 64-bit division
 * that a linear `pw*32767/peak` normalization would need (no `__divdi3` on target). */
static uint32_t scope_log2(uint64_t v)
{
    uint32_t n = 0;
    while (v > 1u) {
        v >>= 1;
        n++;
    }
    return n;
}

/* The spectrogram magnitudes for a channel: nbins linearly-spaced Goertzel bins
 * over [0, fs/2], each a log-power magnitude normalized to Q15 against the
 * loudest bin. */
void scope_spectrum_ch(uint32_t ch, uint16_t *mag, uint32_t nbins)
{
    uint32_t b, peak_bits = 1;
    int64_t peak = 0;
    if (ch >= SCOPE_CH)
        ch = 0u;
    if (nbins > SCOPE_BINS)
        nbins = SCOPE_BINS;
    for (b = 0; b < nbins; b++) {
        uint32_t f = (b + 1u) * (SCOPE_FS / 2u) / nbins;
        int64_t pw = scope_goertzel_power(ch, f, SCOPE_FS);
        scope_pw[b] = pw;
        if (pw > peak)
            peak = pw;
    }
    if (peak > 0)
        peak_bits = scope_log2((uint64_t)peak);
    for (b = 0; b < nbins; b++) {
        uint32_t bits = scope_pw[b] > 0 ? scope_log2((uint64_t)scope_pw[b]) : 0u;
        uint32_t v = (bits * 32767u) / peak_bits;   /* 32-bit: log-power, Q15 */
        mag[b] = (uint16_t)(v > 32767u ? 32767u : v);
    }
}

void scope_spectrum(uint16_t *mag, uint32_t nbins)
{
    scope_spectrum_ch(0u, mag, nbins);
}
