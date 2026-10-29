/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The device-side MIDI handler implementation (synth_midi.h). `midi_get` is the
 * platform's (provided by the includer: platform.c on device, a stub in tests). */
#include "synth_midi.h"

static uint8_t sustain_on;
static uint8_t sustain_pend[128]; /* note-offs deferred by the sustain pedal */

void synth_midi_poll(const synth_midi_ctx *ctx)
{
    uint8_t st, d1, d2;
    while (midi_get(&st, &d1, &d2)) {
        uint32_t ty = st & 0xF0u, ch = st & 0x0Fu;
        if (st >= 0xF8u)
            continue; /* clock/transport: the app's concern */
        if (ty == 0x90u && d2) { /* note on */
            ctx->note_on(d1, d2, ch);
            sustain_pend[d1] = 0; /* a fresh on cancels any deferred off */
        } else if (ty == 0x80u || ty == 0x90u) { /* note off (velocity 0 = off) */
            if (sustain_on)
                sustain_pend[d1] = 1;
            else
                ctx->note_off(d1);
        } else if (ty == 0xB0u) { /* control change */
            if (d1 == 64u) { /* sustain */
                sustain_on = d2 >= 64u;
                if (!sustain_on) {
                    uint32_t n;
                    for (n = 0; n < 128u; n++)
                        if (sustain_pend[n]) {
                            sustain_pend[n] = 0;
                            ctx->note_off(n);
                        }
                }
            } else if (d1 == 123u) { /* all notes off */
                uint32_t n;
                ctx->all_off();
                for (n = 0; n < 128u; n++)
                    sustain_pend[n] = 0;
                sustain_on = 0;
            } else if (d1 < 128u && ctx->cc_map[d1] != SYNTH_CC_NONE) {
                uint32_t id = ctx->cc_map[d1];
                int32_t v = ctx->param_min[id] +
                            (ctx->param_max[id] - ctx->param_min[id]) * (int32_t)d2 / 127;
                ctx->set_param(id, v);
            }
        } else if (ty == 0xE0u) { /* pitch bend, 14-bit, ±2 semitones (Q16 cents) */
            int32_t b = (int32_t)((uint32_t)d1 | (uint32_t)d2 << 7) - 8192;
            ctx->set_bend((uint32_t)(65536 + b * 1600));
        }
    }
}
