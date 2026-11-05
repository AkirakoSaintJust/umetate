/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The generic app core (see synth_app.h): the preset save/load/init/name flow and
 * the modal popup state machine, over a project's generated seam + banks. This is
 * included by rib.c after the platform + the synth services, before the app. */
#include "synth_app.h"
#include "synth_runtime.h"
#include "ui.h"

/* ---- the preset record helpers (the same logic every project needs) ---- */

/* save one part's timbre into a single-part slot; remember it as that part's source
 * so a multi-patch can reference it. */
static void save_part_to(synth_app_ctx *ctx, uint8_t part, uint16_t slot)
{
    int32_t params[SYNTH_PARAM_MAX];
    uint32_t i, base = (uint32_t)part * ctx->n_params;
    if (slot >= PRESET_PART_SLOTS)
        return;
    for (i = 0; i < ctx->n_params; i++)
        params[i] = ctx->get_param(base + i);
    preset_part_pack(ctx->part_bank + (uint32_t)slot * PP_RECORD(ctx->n_params),
                     ui_name_get(part), params, ctx->n_params);
    ctx->part_slot[part] = (uint8_t)slot;
    ctx->bank_dirty = 1;
    ctx->t_change = fm1_ms;
}

/* the first empty single-part slot (0xFF), or 0xFF when the bank is full */
static uint8_t empty_part_slot(const synth_app_ctx *ctx)
{
    uint32_t i;
    for (i = 0; i < PRESET_PART_SLOTS; i++)
        if (ctx->part_bank[i * PP_RECORD(ctx->n_params)] == PRESET_EMPTY)
            return (uint8_t)i;
    return 0xFFu;
}

/* save the composition (each part's source single part + the routing) into a
 * multi-patch slot. `mode` = the active part's live edits: 0 = discard,
 * 1 = save-as-new, 2 = mutate in place. */
static void save_multi(synth_app_ctx *ctx, uint16_t slot, uint8_t mode)
{
    int32_t lv[SYNTH_APP_MAX_PARTS], dl[SYNTH_APP_MAX_PARTS];
    int32_t ch[SYNTH_APP_MAX_PARTS], lo[SYNTH_APP_MAX_PARTS], hi[SYNTH_APP_MAX_PARTS];
    uint32_t i;
    if (slot >= PRESET_MULTI_SLOTS)
        return;
    if (mode != 0u) {
        uint8_t part = ui_part(), dst = ctx->part_slot[part];
        if (mode == 1u || dst == 0xFFu) {
            dst = empty_part_slot(ctx);
            if (dst == 0xFFu)
                return;
        }
        save_part_to(ctx, part, dst);
    }
    for (i = 0; i < ctx->n_parts; i++) {
        ch[i] = ctx->get_param(ctx->routing_base + 0u * ctx->n_parts + i);
        lo[i] = ctx->get_param(ctx->routing_base + 1u * ctx->n_parts + i);
        hi[i] = ctx->get_param(ctx->routing_base + 2u * ctx->n_parts + i);
        lv[i] = ctx->get_param(ctx->routing_base + 3u * ctx->n_parts + i);
        dl[i] = ctx->get_param(ctx->routing_base + 4u * ctx->n_parts + i);
    }
    preset_multi_pack(ctx->multi_bank + (uint32_t)slot * MP_RECORD(ctx->n_parts),
                      ui_name_get(ctx->n_parts), ctx->part_slot, lv, dl, ch, lo, hi,
                      ctx->n_parts);
    ctx->multi_dirty = 1;
    ctx->t_change = fm1_ms;
}

/* load a single-part slot into a part (its params, not its routing). */
static void load_part(synth_app_ctx *ctx, uint8_t part, uint32_t slot)
{
    char name[PRESET_NAME_LEN];
    int32_t params[SYNTH_PARAM_MAX];
    const uint8_t *rec = ctx->part_bank + slot * PP_RECORD(ctx->n_params);
    uint32_t i, base = (uint32_t)part * ctx->n_params;
    if (slot >= PRESET_PART_SLOTS || rec[0] == PRESET_EMPTY ||
        !preset_part_unpack(rec, ctx->n_params, name, params))
        return;
    for (i = 0; i < ctx->n_params; i++)
        ctx->set_param(base + i, params[i]);
    ui_name_set(part, name);
    ctx->part_slot[part] = (uint8_t)slot;
}

/* apply a multi patch and remember its name + each part's source single part. */
static void apply_multi(synth_app_ctx *ctx, uint16_t slot)
{
    synth_runtime_ctx rc;
    char name[PRESET_NAME_LEN];
    uint8_t ps[SYNTH_APP_MAX_PARTS];
    int32_t lv[SYNTH_APP_MAX_PARTS], dl[SYNTH_APP_MAX_PARTS];
    int32_t ch[SYNTH_APP_MAX_PARTS], lo[SYNTH_APP_MAX_PARTS], hi[SYNTH_APP_MAX_PARTS];
    uint32_t i;
    rc.n_params = ctx->n_params;
    rc.n_parts = ctx->n_parts;
    rc.routing_base = ctx->routing_base;
    rc.set_param = ctx->set_param;
    rc.part_bank = ctx->part_bank;
    rc.multi_bank = ctx->multi_bank;
    synth_preset_apply(&rc, slot);
    if (slot >= PRESET_MULTI_SLOTS)
        return;
    if (preset_multi_unpack(ctx->multi_bank + slot * MP_RECORD(ctx->n_parts),
                            ctx->n_parts, name, ps, lv, dl, ch, lo, hi)) {
        for (i = 0; i < ctx->n_parts; i++)
            ctx->part_slot[i] = ps[i];
        ui_name_set(ctx->n_parts, name);
    }
}

/* ---- the public API ---- */

void synth_app_boot(synth_app_ctx *ctx)
{
    int32_t bc, mt;
    uint32_t i;
    memset(ctx->part_bank, 0xFF, PP_BANK(ctx->n_params));   /* 0xFF = empty */
    memset(ctx->multi_bank, 0xFF, MP_BANK(ctx->n_parts));
    preset_part_bank_load(ctx->part_bank, ctx->n_params);
    preset_multi_bank_load(ctx->multi_bank, ctx->n_params, ctx->n_parts);
    if (preset_settings_load(ctx->settings) ||
        !preset_settings_unpack(ctx->settings, &bc, &mt))
        bc = 0, mt = 0;
    if (bc >= 0 && bc <= 15)
        ctx->set_param(ctx->routing_base + 0u * ctx->n_parts + 0u, bc);
    (void)mt;
    memcpy(ctx->saved_settings, ctx->settings, ST_RECORD);
    for (i = 0; i < ctx->n_parts; i++)
        ctx->part_slot[i] = 0xFFu;
    ctx->cur_slot = 0u;
    ctx->browser.open = 0;
    apply_multi(ctx, 0u);                                   /* slot 0: a valid record applies */
    /* a fresh boot shows the INIT names (the loaded multi's name is carried in the
     * record for the browser, not the boot header) */
    for (i = 0; i < ctx->n_parts; i++)
        ui_name_set((uint8_t)i, "INIT PART");
    ui_name_set((uint8_t)ctx->n_parts, "INIT MULTI");
}

void synth_app_init_patch(synth_app_ctx *ctx)
{
    uint32_t i, p;
    for (i = 0; i < ctx->init_n; i++) {
        uint16_t id;
        int32_t value;
        ctx->get_init(i, &id, &value);
        ctx->set_param(id, value);
    }
    ui_part_set(0u);
    ui_op_set(0u);
    for (p = 0; p < ctx->n_parts; p++)
        ui_part_mute_set((uint8_t)p, 0u);
    for (p = 0; p < ctx->n_parts; p++) {
        ctx->part_slot[p] = 0xFFu;
        ui_name_set((uint8_t)p, "INIT PART");
    }
    ui_name_set((uint8_t)ctx->n_parts, "INIT MULTI");
}

/* reset one part's timbre to the init values + clear its source slot + name. */
static void init_one_part(synth_app_ctx *ctx, uint8_t part)
{
    uint32_t i, base = (uint32_t)part * ctx->n_params;
    for (i = 0; i < ctx->init_n; i++) {
        uint16_t id;
        int32_t value;
        ctx->get_init(i, &id, &value);
        if (id >= base && id < base + ctx->n_params)
            ctx->set_param(id, value);
    }
    ctx->part_slot[part] = 0xFFu;
    ui_name_set(part, "INIT PART");
}

void synth_app_init_part(synth_app_ctx *ctx)
{
    init_one_part(ctx, ui_part());
}

void synth_app_save(synth_app_ctx *ctx)
{
    uint16_t ps = ctx->part_slot[ui_part()];
    ui_save_begin(0u, ps == 0xFFu ? 0u : ps, ctx->cur_slot);
}

void synth_app_apply(synth_app_ctx *ctx, uint8_t kind, uint16_t slot)
{
    if (kind == 0u) {
        ctx->pending_part = 1u;                 /* load a single part */
        ctx->pending_slot = slot;
        ui_part_chooser_begin(ui_part(), 0);
    } else if (slot != ctx->cur_slot) {
        apply_multi(ctx, slot);
        ctx->cur_slot = slot;
    }
}

void synth_app_slot_name(const synth_app_ctx *ctx, uint8_t kind, uint16_t slot,
                         char *out, uint32_t cap)
{
    uint32_t i;
    if (!out || !cap)
        return;
    out[0] = 0;
    if (kind == 0u) {
        if (slot < PRESET_PART_SLOTS) {
            char name[PRESET_NAME_LEN];
            int32_t params[SYNTH_PARAM_MAX];
            const uint8_t *rec = ctx->part_bank + (uint32_t)slot * PP_RECORD(ctx->n_params);
            if (rec[0] != PRESET_EMPTY &&
                preset_part_unpack(rec, ctx->n_params, name, params)) {
                for (i = 0; i + 1u < cap && name[i]; i++)
                    out[i] = name[i];
                out[i] = 0;
            }
        }
    } else if (slot < PRESET_MULTI_SLOTS) {
        char name[PRESET_NAME_LEN];
        uint8_t ps[SYNTH_APP_MAX_PARTS];
        int32_t lv[SYNTH_APP_MAX_PARTS], dl[SYNTH_APP_MAX_PARTS];
        int32_t ch[SYNTH_APP_MAX_PARTS], lo[SYNTH_APP_MAX_PARTS], hi[SYNTH_APP_MAX_PARTS];
        const uint8_t *rec = ctx->multi_bank + (uint32_t)slot * MP_RECORD(ctx->n_parts);
        if (rec[0] != PRESET_EMPTY &&
            preset_multi_unpack(rec, ctx->n_parts, name, ps, lv, dl, ch, lo, hi)) {
            for (i = 0; i + 1u < cap && name[i]; i++)
                out[i] = name[i];
            out[i] = 0;
        }
    }
}

void synth_app_input(synth_app_ctx *ctx)
{
    ctx->last_input_ms = fm1_ms;
}

uint8_t synth_app_step(synth_app_ctx *ctx)
{
    uint32_t rel, b;
    int32_t k1, k2;

    if (ui_confirm_open()) {
        /* the yes/no popup: SAVE = do it, HOME = cancel */
        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_SAVE)) {
            ui_confirm_commit();
            ui_act_init_patch();
        }
        if (b & (1u << BTN_HOME))
            ui_confirm_cancel();
        if (b)
            synth_app_input(ctx);
        return 1u;
    }
    if (ui_name_editing() != 0xFFu) {
        /* the name editor: KNOB1 = char, KNOB2 = cursor, SEL = backspace,
           SAVE = ok, HOME = cancel; the keys + page are inert while open. */
        k1 = fm1_enc_take(ENC_KNOB1);
        k2 = fm1_enc_take(ENC_KNOB2);
        if (k1)
            ui_name_editor_char(k1);
        if (k2)
            ui_name_editor_move(k2);
        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_SEL))
            ui_name_editor_backspace();
        if (b & (1u << BTN_SAVE))
            ui_name_editor_commit();
        if (b & (1u << BTN_HOME))
            ui_name_editor_cancel();
        if (k1 || k2 || b)
            synth_app_input(ctx);
        return 1u;
    }
    if (ui_save_mode_open()) {
        /* the save-mode chooser (step 2 of a multi-patch save): KNOB1 = mode,
           SAVE = save, HOME = back to the slot chooser. */
        k1 = fm1_enc_take(ENC_KNOB1);
        (void)fm1_enc_take(ENC_KNOB2);
        if (k1)
            ui_save_mode_move(k1);
        if (k1)
            synth_app_input(ctx);
        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_SAVE)) {
            uint8_t mode = ui_save_mode();
            uint16_t slot = ui_save_slot();
            ui_save_mode_commit();
            ui_save_commit();
            save_multi(ctx, slot, mode);
            ui_popup_msg("SAVED SUCCESSFULLY");
            ctx->saved_ms = fm1_ms;
        }
        if (b & (1u << BTN_HOME))
            ui_save_mode_cancel();
        if (b)
            synth_app_input(ctx);
        return 1u;
    }
    if (ui_save_open()) {
        /* the save chooser: KNOB1 = kind, KNOB2 = slot, SAVE = save, HOME = cancel */
        k1 = fm1_enc_take(ENC_KNOB1);
        k2 = fm1_enc_take(ENC_KNOB2);
        if (k1)
            ui_save_kind_move(k1);
        if (k2)
            ui_save_slot_move(k2);
        if (k1 || k2)
            synth_app_input(ctx);
        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_SAVE)) {
            uint8_t kind = ui_save_kind();
            uint16_t slot = ui_save_slot();
            if (kind == 0u) {
                ui_save_commit();
                ctx->pending_part = 2u;         /* save a single part */
                ctx->pending_slot = slot;
                ui_part_chooser_begin(ui_part(), 0);
            } else {
                ui_save_mode_begin();           /* step 2 for a multi-patch */
            }
        }
        if (b & (1u << BTN_HOME))
            ui_save_cancel();
        if (b)
            synth_app_input(ctx);
        return 1u;
    }
    if (ui_part_chooser_open()) {
        /* the "which single part" chooser: KNOB1 = part, SAVE = apply, HOME = cancel */
        uint8_t part, pending;
        k1 = fm1_enc_take(ENC_KNOB1);
        if (k1)
            ui_part_chooser_move(k1);
        if (k1)
            synth_app_input(ctx);
        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_SAVE)) {
            part = ui_part_chooser_part();
            pending = ctx->pending_part;
            ui_part_chooser_commit();
            if (pending == 1u)
                load_part(ctx, part, ctx->pending_slot);
            else if (pending == 2u) {
                save_part_to(ctx, part, ctx->pending_slot);
                ui_popup_msg("SAVED SUCCESSFULLY");
                ctx->saved_ms = fm1_ms;
            } else if (pending == 3u)
                init_one_part(ctx, part);
            ctx->pending_part = 0u;
        }
        if (b & (1u << BTN_HOME)) {
            ui_part_chooser_cancel();
            ctx->pending_part = 0u;
        }
        if (b)
            synth_app_input(ctx);
        return 1u;
    }
    if (ui_copy_open()) {
        /* the page-copy chooser: KNOB1 = target, SAVE = copy, HOME = cancel */
        k1 = fm1_enc_take(ENC_KNOB1);
        if (k1)
            ui_copy_move(k1);
        if (k1)
            synth_app_input(ctx);
        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_SAVE)) {
            uint8_t part, op;
            ui_copy_target(&part, &op);
            ui_copy_commit();
            ui_copy_apply(part, op);
            ui_popup_msg("COPIED SUCCESSFULLY");
            ctx->saved_ms = fm1_ms;
        }
        if (b & (1u << BTN_HOME))
            ui_copy_cancel();
        if (b)
            synth_app_input(ctx);
        return 1u;
    }
    return 0u;
}

void synth_app_browser_step(synth_app_ctx *ctx, int32_t delta, uint32_t now,
                            uint8_t single_part)
{
    if (single_part)
        ui_browser_step(&ctx->browser, delta, now, 0u, PRESET_PART_SLOTS, 0u,
                        2000u);
    else
        ui_browser_step(&ctx->browser, delta, now, 1u, PRESET_MULTI_SLOTS,
                        ctx->cur_slot, 2000u);
}

void synth_app_tick(synth_app_ctx *ctx, uint32_t now, uint8_t quiet)
{
    /* the SysEx settings write reached `settings`: persist it once silent */
    if (memcmp(ctx->settings, ctx->saved_settings, ST_RECORD)) {
        ctx->set_dirty = 1;
        ctx->t_change = now;
    }
    /* the "SAVED/COPIED" acknowledgement lingers ~750 ms */
    if (ctx->saved_ms && now - ctx->saved_ms >= 750u) {
        ui_popup_hide();
        ctx->saved_ms = 0u;
    }
    /* a modal popup with no input for ~3 s closes without committing */
    if (ui_popup_active() && now - ctx->last_input_ms >= 3000u) {
        ui_popup_cancel_all();
        ctx->pending_part = 0u;
        ctx->last_input_ms = now;
    }
    /* silent-only saves (the store erases with interrupts off) */
    if (quiet && now - ctx->t_change > 2000u) {
        if (ctx->bank_dirty) {
            preset_part_bank_save(ctx->part_bank, ctx->n_params);
            ctx->bank_dirty = 0;
        }
        if (ctx->multi_dirty) {
            preset_multi_bank_save(ctx->multi_bank, ctx->n_params, ctx->n_parts);
            ctx->multi_dirty = 0;
        }
        if (ctx->set_dirty) {
            preset_settings_save(ctx->settings);
            memcpy(ctx->saved_settings, ctx->settings, ST_RECORD);
            ctx->set_dirty = 0;
        }
    }
}
