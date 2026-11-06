/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The device-side MIDI handler host test: scripted messages against recording
 * seam stubs: note routing, the CC map + value scaling, sustain, panic, bend. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../src/synth_midi.h"

/* the platform's MIDI read, scripted by the test */
static uint8_t q_st[32], q_d1[32], q_d2[32];
static uint32_t q_n, q_r;
int midi_get(uint8_t *st, uint8_t *d1, uint8_t *d2)
{
    if (q_r == q_n)
        return 0;
    *st = q_st[q_r];
    *d1 = q_d1[q_r];
    *d2 = q_d2[q_r];
    q_r++;
    return 1;
}
static void push(uint8_t st, uint8_t d1, uint8_t d2)
{
    q_st[q_n] = st;
    q_d1[q_n] = d1;
    q_d2[q_n] = d2;
    q_n++;
}

/* the seam stubs: record the calls */
static uint32_t on_n, off_n, all_n, set_n, bend_n;
static uint32_t on_note[8], on_vel[8], on_ch[8], off_note[8];
static uint32_t set_id[8], set_val[8], bend_val;

static void st_note_on(uint32_t n, uint32_t v, uint32_t c)
{
    on_note[on_n] = n;
    on_vel[on_n] = v;
    on_ch[on_n] = c;
    on_n++;
}
static void st_note_off(uint32_t n) { off_note[off_n++] = n; }
static void st_all_off(void) { all_n++; }
static int st_set_param(uint32_t id, int32_t v)
{
    set_id[set_n] = id;
    set_val[set_n] = (uint32_t)v;
    set_n++;
    return 0;
}
static void st_bend(uint32_t b)
{
    bend_val = b;
    bend_n++;
}

/* the test's cc tables: CC 16 -> param 3 (0..127), CC 17 -> param 7 (-1..15) */
static uint16_t cc_map[128];
static int32_t pmin[8] = {0, 0, 0, 0, 0, 0, 0, -1};
static int32_t pmax[8] = {0, 0, 0, 127, 0, 0, 0, 15};

#include "../src/synth_midi.c"

static int bad;
static void check(const char *what, int ok)
{
    printf("midi: %-72s %s\n", what, ok ? "ok" : "FAIL");
    bad += !ok;
}

static void begin(void)
{
    q_n = q_r = 0;
    on_n = off_n = all_n = set_n = bend_n = 0;
}

int main(void)
{
    uint32_t i;
    synth_midi_ctx ctx = {st_note_on, st_note_off, st_all_off, st_set_param, st_bend,
                          cc_map, pmin, pmax, 0u, {0}};
    for (i = 0; i < 128u; i++)
        cc_map[i] = SYNTH_CC_NONE;
    cc_map[16] = 3;
    cc_map[17] = 7;

    /* notes route to the seam with the channel */
    begin();
    push(0x90, 60, 100);
    push(0x91, 62, 90);
    push(0x80, 60, 0);
    push(0x90, 62, 0); /* velocity 0 = off */
    synth_midi_poll(&ctx);
    check("note on/off route with the channel",
          on_n == 2 && on_note[0] == 60 && on_vel[0] == 100 && on_ch[0] == 0 &&
              on_note[1] == 62 && on_ch[1] == 1 && off_n == 2 && off_note[0] == 60 &&
              off_note[1] == 62);

    /* a CC scales the 7-bit value to the param's range */
    begin();
    push(0xB0, 16, 127); /* param 3, 0..127 */
    push(0xB0, 17, 127); /* param 7, -1..15 */
    push(0xB0, 17, 0);
    push(0xB0, 17, 64); /* -1 + 16*64/127 = 7 */
    push(0xB0, 20, 100); /* unassigned */
    synth_midi_poll(&ctx);
    check("a CC reaches its param, scaled to its range",
          set_n == 4 && set_id[0] == 3 && set_val[0] == 127 && set_id[1] == 7 &&
              set_val[1] == 15 && set_val[2] == (uint32_t)-1 && set_val[3] == 7);

    /* sustain holds note-offs until the pedal lifts */
    begin();
    push(0xB0, 64, 127);
    push(0x90, 60, 100);
    push(0x80, 60, 0);
    synth_midi_poll(&ctx);
    check("sustain defers the note-off", off_n == 0);
    begin();
    push(0xB0, 64, 0);
    synth_midi_poll(&ctx);
    check("lifting sustain flushes the deferred note-offs", off_n == 1 && off_note[0] == 60);

    /* panic: all notes off + the pedal cleared */
    begin();
    push(0xB0, 64, 127);
    push(0x90, 60, 100);
    push(0xB0, 123, 0);
    synth_midi_poll(&ctx);
    check("panic clears everything", all_n == 1 && off_n == 0);
    begin();
    push(0x80, 60, 0);
    synth_midi_poll(&ctx);
    check("the pedal is cleared after panic", off_n == 1 && off_note[0] == 60);

    /* pitch bend: center = unity, full up = +2 semitones */
    begin();
    push(0xE0, 0, 64);   /* 8192: center */
    push(0xE0, 127, 127); /* 16383: full up */
    synth_midi_poll(&ctx);
    check("bend maps to Q16 cents", bend_n == 2 && bend_val == 65536u + 8191 * 1600);

    printf("%s\n", bad ? "MIDI TEST FAILED" : "midi test passed");
    return bad != 0;
}
