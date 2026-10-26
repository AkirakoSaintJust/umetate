/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments */
#pragma once
#include <stdint.h>

enum { UMETATE_DSP_VOICES = 4u };

#if defined(UMETATE_TARGET_DSP)
#define UMETATE_DSP_API __attribute__((section(".dsp_text"), noinline, used))
#else
#define UMETATE_DSP_API
#endif

void rib_dsp_reset(void);
UMETATE_DSP_API void rib_dsp_render(int32_t *out, uint32_t frames);
UMETATE_DSP_API void rib_dsp_note_on(uint32_t note, uint32_t velocity);
UMETATE_DSP_API void rib_dsp_note_off(uint32_t note);
UMETATE_DSP_API void rib_dsp_set_bend_q16(uint32_t bend);
UMETATE_DSP_API uint32_t rib_dsp_lit(uint32_t base_note);
UMETATE_DSP_API int rib_dsp_quiet(void);
