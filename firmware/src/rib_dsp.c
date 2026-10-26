/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments */
#include <stdint.h>
#include "rib_dsp.h"

#define NV UMETATE_DSP_VOICES
#define DSP_FN UMETATE_DSP_API

static struct {
    volatile uint32_t inc;
    volatile int32_t gate;
    int32_t amp;
    uint32_t ph, age;
    uint8_t note;
} voice[NV];
static volatile uint32_t bend_q16 = 65536;
static uint32_t ages;

static DSP_FN int32_t sine(uint32_t phase)
{
    int32_t x = (int32_t)phase >> 16;
    int32_t ax = x < 0 ? -x : x;
    int32_t y = (x * (32768 - ax)) >> 13;
    int32_t ay = y < 0 ? -y : y;
    y += ((((y * ay) >> 15) - y) * 7373) >> 15;
    return y > 32767 ? 32767 : y < -32767 ? -32767 : y;
}

void rib_dsp_reset(void)
{
    uint32_t i;
    for (i = 0; i < NV; i++) {
        voice[i].inc = 0;
        voice[i].gate = 0;
        voice[i].amp = 0;
        voice[i].ph = 0;
        voice[i].age = 0;
        voice[i].note = 0;
    }
    bend_q16 = 65536;
    ages = 0;
}

void rib_dsp_render(int32_t *out, uint32_t frames)
{
    uint32_t v, i;
    for (v = 0; v < NV; v++) {
        uint32_t phase = voice[v].ph;
        uint32_t step = (uint32_t)(((uint64_t)voice[v].inc * bend_q16) >> 16);
        int32_t amp = voice[v].amp, gate = voice[v].gate;
        if (!amp && !gate)
            continue;
        for (i = 0; i < frames; i++) {
            int32_t sample;
            if (amp < gate) { amp += 48; if (amp > gate) amp = gate; }
            else if (amp > gate) { amp -= 6; if (amp < gate) amp = gate; }
            phase += step;
            sample = (sine(phase) * amp) >> 15;
            out[2u * i] += sample;
            out[2u * i + 1u] += sample;
        }
        voice[v].ph = phase;
        voice[v].amp = amp;
    }
}

void rib_dsp_note_on(uint32_t note, uint32_t velocity)
{
    static const uint32_t inc_c9[12] = {
        815363807u, 863847862u, 915214929u, 969636441u, 1027294024u, 1088380105u,
        1153098554u, 1221665363u, 1294309365u, 1371273005u, 1452813141u, 1539201906u};
    uint32_t v, pick = 0, best = 0xFFFFFFFFu;
    if (note > 127u || !velocity)
        return;
    for (v = 0; v < NV; v++) {
        uint32_t score = voice[v].note == note && voice[v].gate ? 0u
                       : voice[v].gate ? 0x80000000u + voice[v].age : (uint32_t)voice[v].amp + 1u;
        if (score < best) { best = score; pick = v; }
    }
    voice[pick].note = (uint8_t)note;
    voice[pick].age = ++ages;
    voice[pick].inc = inc_c9[note % 12u] >> (10u - note / 12u);
    voice[pick].gate = (int32_t)(velocity * 90u);
}

void rib_dsp_note_off(uint32_t note)
{
    uint32_t v;
    for (v = 0; v < NV; v++)
        if (voice[v].note == note)
            voice[v].gate = 0;
}

void rib_dsp_set_bend_q16(uint32_t bend) { bend_q16 = bend; }

uint32_t rib_dsp_lit(uint32_t base_note)
{
    uint32_t k, lit = 0;
    for (k = 0; k < NV; k++)
        if (voice[k].gate && voice[k].note >= base_note && voice[k].note < base_note + 27u)
            lit |= 1u << (voice[k].note - base_note);
    return lit;
}

int rib_dsp_quiet(void)
{
    uint32_t v;
    for (v = 0; v < NV; v++)
        if (voice[v].gate || voice[v].amp)
            return 0;
    return 1;
}
