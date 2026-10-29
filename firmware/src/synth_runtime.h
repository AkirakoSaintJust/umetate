/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The synth runtime (docs/roadmap.md §6.11.4, F7): the preset integration — apply
 * a stored multi patch to the engine (its part-patch refs become the parts'
 * timbre params, its routing becomes the parts' channel/keyzone/level/delay).
 * The engine's `set_param` is the single write path, so applying a preset is just
 * parameter writes (no direct state access). */
#pragma once
#include <stdint.h>

typedef struct {
    uint32_t n_params;      /* the per-part timbre param count */
    uint32_t n_parts;
    uint32_t routing_base;  /* the id of part 0's channel param (the generated layout) */
    int (*set_param)(uint32_t id, int32_t value);
    const uint8_t *part_bank;   /* 64 part-patch records */
    const uint8_t *multi_bank;  /* 64 multi-patch records */
} synth_runtime_ctx;

/* apply the multi patch in `multi_slot` (0..63); a bad slot or record is a no-op */
void synth_preset_apply(const synth_runtime_ctx *ctx, uint32_t multi_slot);
