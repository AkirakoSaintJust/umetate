/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate)
 * Host test for the dual-core note queue (hal/fm1_ipc.h), covering FIFO order,
 * wrap-around, overrun counting and the "no lost note-off" rule. The queue's logic
 * is identical on target and host, since only the csync barrier (FM1_CPU1_USED) is
 * a target no-op here. */
#include <stdio.h>
#include "fm1_ipc.h"

volatile dsp_cmd dsp_cmd_buf[UMETATE_DSP_CMD_CAP];
volatile uint32_t dsp_cmd_head, dsp_cmd_tail, dsp_cmd_overrun, dsp_all_off_pending;
volatile dsp_status_t dsp_status;
volatile int32_t bend_q16;
volatile uint32_t lit_base;

static int failures;

static void ok(int cond, const char *what)
{
    printf("%s %s\n", cond ? "ok:" : "FAIL:", what);
    if (!cond)
        failures++;
}

static void reset_queue(void)
{
    uint32_t i;
    dsp_cmd_head = dsp_cmd_tail = dsp_cmd_overrun = dsp_all_off_pending = 0;
    for (i = 0; i < UMETATE_DSP_CMD_CAP; i++)
        dsp_cmd_buf[i] = (dsp_cmd){0, 0, 0, 0};
}

int main(void)
{
    dsp_cmd c;
    uint32_t i;

    /* FIFO order */
    reset_queue();
    dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, 60, 100);
    dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, 64, 90);
    dsp_cmd_push(UMETATE_DSP_CMD_NOTE_OFF, 60, 0);
    ok(dsp_cmd_pop(&c) && c.kind == UMETATE_DSP_CMD_NOTE_ON && c.note == 60 && c.vel == 100, "FIFO: first note-on in, first out");
    ok(dsp_cmd_pop(&c) && c.note == 64, "FIFO: second note-on");
    ok(dsp_cmd_pop(&c) && c.kind == UMETATE_DSP_CMD_NOTE_OFF && c.note == 60, "FIFO: note-off");
    ok(!dsp_cmd_pop(&c), "empty queue returns 0");

    /* wrap-around: fill, drain, fill again (indices wrap past CAP) */
    reset_queue();
    for (i = 0; i < UMETATE_DSP_CMD_CAP; i++)
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, (uint16_t)(i % 128u), 1);
    ok(dsp_cmd_head == UMETATE_DSP_CMD_CAP && dsp_cmd_overrun == 0, "full queue: no overrun, head = CAP");
    for (i = 0; i < UMETATE_DSP_CMD_CAP; i++) {
        if (!dsp_cmd_pop(&c) || c.note != i % 128u) { ok(0, "wrap-around drain order"); break; }
    }
    ok(i == UMETATE_DSP_CMD_CAP, "wrap-around: all CAP entries drained in order");
    for (i = 0; i < 5; i++)
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, (uint16_t)(200 + i), 1);
    ok(dsp_cmd_pop(&c) && c.note == 200, "wrap-around: index wrapped, entries still FIFO");

    /* overrun: a note-on is dropped and counted, a note-off sets all_off_pending */
    reset_queue();
    for (i = 0; i < UMETATE_DSP_CMD_CAP; i++)
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, 60, 1);
    dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, 61, 1);   /* overrun: droppable */
    ok(dsp_cmd_overrun == 1 && dsp_all_off_pending == 0, "overrun: a note-on is dropped and counted");
    dsp_cmd_push(UMETATE_DSP_CMD_NOTE_OFF, 60, 0);  /* overrun: never lost */
    ok(dsp_cmd_overrun == 2 && dsp_all_off_pending == 1, "overrun: a note-off is never lost (all_off_pending set)");

    printf("%s\n", failures ? "SOME TESTS FAILED" : "IPC queue test passed");
    return failures ? 1 : 0;
}
