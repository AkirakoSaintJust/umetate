/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The device-side SysEx handler (docs/roadmap.md §6.11.4, F7): the shared envelope
 *
 *   F0 00 21 1D <model> <cmd> <ver> <payload…> <crc16-lo> <crc16-hi> F7
 *
 * and the five commands (identity request, param dump, part-patch dump, multi-patch
 * dump, settings dump; responses echo the command with the high bit). The C mirror
 * of `umetate/_sysex.py`. Feed the platform's SysEx byte stream with
 * `synth_sysex_feed`; call `synth_sysex_poll` from the main loop. Responses go out
 * through the platform's `midi_send_sysex` (provided by the includer). */
#pragma once
#include <stdint.h>

#define SYNTH_SX_MAX 384u   /* a frame + a response fit; longer frames are dropped */

typedef struct {
    uint32_t model;          /* the firmware's SysEx model byte */
    uint32_t n_params;       /* the timbre param count (the part-patch N, <= 64) */
    uint32_t n_parts;
    int32_t (*get_param)(uint32_t id);
    uint8_t *part_bank;      /* 64 part-patch records (the writable bank) */
    uint8_t *multi_bank;     /* 64 multi-patch records */
    uint8_t *settings;       /* the settings record (ST_RECORD bytes) */
} synth_sysex_ctx;

void synth_sysex_feed(uint8_t b);                    /* the platform's SysEx byte stream */
void synth_sysex_poll(const synth_sysex_ctx *ctx);   /* dispatch one completed frame */
