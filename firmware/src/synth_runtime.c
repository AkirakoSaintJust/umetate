/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The synth runtime implementation (synth_runtime.h). */
#include "synth_runtime.h"
#include "presets.h"

void synth_preset_apply(const synth_runtime_ctx *ctx, uint32_t multi_slot)
{
    char name[PRESET_NAME_LEN];
    int32_t params[SYNTH_PARAM_MAX];
    uint32_t p, i;
    const uint8_t *rec;

    if (multi_slot >= PRESET_MULTI_SLOTS || ctx->n_params > SYNTH_PARAM_MAX || !ctx->multi_bank)
        return;
    rec = ctx->multi_bank + multi_slot * MP_RECORD(ctx->n_parts);
    {
        uint8_t part_slot[8];
        int32_t level[8], delay[8], channel[8], low[8], high[8];
        if (ctx->n_parts > 8u ||
            !preset_multi_unpack(rec, ctx->n_parts, name, part_slot, level, delay, channel,
                                 low, high))
            return;
        for (p = 0; p < ctx->n_parts; p++) {
            /* the single part: its params become part p's timbre block */
            if (part_slot[p] < PRESET_PART_SLOTS && ctx->part_bank &&
                preset_part_unpack(
                    ctx->part_bank + (uint32_t)part_slot[p] * PP_RECORD(ctx->n_params),
                    ctx->n_params, name, params)) {
                for (i = 0; i < ctx->n_params; i++)
                    ctx->set_param(p * ctx->n_params + i, params[i]);
            }
            /* the routing: channel, low, high, level, delay */
            ctx->set_param(ctx->routing_base + 0u * ctx->n_parts + p, channel[p]);
            ctx->set_param(ctx->routing_base + 1u * ctx->n_parts + p, low[p]);
            ctx->set_param(ctx->routing_base + 2u * ctx->n_parts + p, high[p]);
            ctx->set_param(ctx->routing_base + 3u * ctx->n_parts + p, level[p]);
            ctx->set_param(ctx->routing_base + 4u * ctx->n_parts + p, delay[p]);
        }
    }
}
