/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The oscilloscope / spectrogram analysis core (integer, CPU0 UI path). */
#pragma once
#include <stdint.h>

#define SCOPE_N 256u          /* the snapshot window (one render block) */
#define SCOPE_FS 44100u       /* the fixed DSP sample rate */
#define SCOPE_BINS 120u       /* the spectrogram bar count (2 px each on 240 px) */

void scope_push(const int32_t *stereo, uint32_t n);   /* the audio ISR stores the left channel */
int16_t scope_at(uint32_t i);                         /* the last snapshot (downsampled) */
void scope_spectrum(uint16_t *mag, uint32_t nbins);   /* Q15 Goertzel magnitudes */
uint32_t scope_seq(void);                             /* snapshot sequence (for the UI dirty check) */
