/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The dual-core DSP transport (docs/roadmap.md §12.1), defined once and shared by
 * both cores and by every engine — the demo's rib_dsp.c and the generated
 * `<synth>_dsp.c` both reference these (fm1_ipc.h declares them). Core 0 produces
 * note events; core 1 drains the queue, renders, and publishes the reverse status.
 * Plain .bss, 64-byte aligned, csync barriers: the cores share the caches
 * (fm1_cpu1.h), so ordering is the only concern. */
#include "fm1_ipc.h"

volatile dsp_cmd dsp_cmd_buf[UMETATE_DSP_CMD_CAP] __attribute__((aligned(64)));
volatile uint32_t dsp_cmd_head, dsp_cmd_tail, dsp_cmd_overrun, dsp_all_off_pending;
volatile dsp_status_t dsp_status __attribute__((aligned(64)));
volatile int32_t bend_q16 = 65536;
volatile uint32_t lit_base;   /* core 0 writes: the octave's base note */
