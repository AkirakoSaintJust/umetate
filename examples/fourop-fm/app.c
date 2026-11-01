/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* fourop-fm's app half of the frozen contract (docs/roadmap.md §6.11.4, F7): the
 * glue between the generated engine, the generated panel, the platform, and the
 * framework's synth services. Included by src/rib.c (the framework) in the
 * `umetate build --synth examples/fourop-fm` composition.
 *
 * Two independent-timbre parts: part 0 = MIDI channel 0 (the panel + the CC
 * surface edit part 0's timbre), part 1 = channel 1 (its timbre comes from the
 * multi patch / SysEx). The engine owns the param truth; the panel's values are
 * mirrored in and out every pass. */
#include "dsp.h"            /* the generated seam prototypes (gen/dsp.h) */
#include "cc_map.h"         /* the generated cc -> param + [min, max] tables */
#include "synth_layout.h"   /* the generated model byte + param/part counts */
#include "panel.h"          /* the generated UI tables (gen/panel.h) */
#include "presets.h"        /* the framework's record store */
#include "synth_midi.h"     /* the framework's MIDI handler */
#include "synth_sysex.h"    /* the framework's SysEx handler */
#include "synth_runtime.h"  /* the framework's preset apply */

/* ---- the preset store's writable memory (the banks + the settings record) ----
 * The 128 single-part records (40 576 B) do not fit CPU0's 96 KiB .bss alongside
 * the rest of the firmware, so the banks live in .pool (the big-buffer region;
 * app.ld): flash is the persistence, RAM is just the working copy reloaded each
 * boot. */
static uint8_t part_bank[PP_BANK(SYNTH_N_PARAMS)] __attribute__((section(".pool")));
static uint8_t multi_bank[MP_BANK(SYNTH_N_PARTS)] __attribute__((section(".pool")));
static uint8_t settings[ST_RECORD], saved_settings[ST_RECORD];
static uint32_t idle_ok, bank_dirty, multi_dirty, set_dirty, t_change;
/* each part's source single-part slot (0xFF = live, no slot) — the multi-patch's
 * part_slot[] refs; set by load/save, reset by INIT. */
static uint8_t part_slot_cur[SYNTH_N_PARTS];
static uint32_t cur_slot;                      /* the loaded multi-patch slot (0 = boot) */

/* ---- the engine seam wrappers (the synth_midi / synth_runtime seams). Dual-core
 * (D3, the default): core 0 pushes note events, core 1 allocates + renders (the
 * generated <name>_render_block). Single-core fallback (or CPU1 gave up): direct. */
static void note_on_seam(uint32_t note, uint32_t velocity, uint32_t channel)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, (uint8_t)(channel & 0xFFu),
                     (uint16_t)note, (uint16_t)velocity);
        return;
    }
#endif
    fourop_fm_dsp_note_on_ch(note, velocity, channel);
}
static void note_off_seam(uint32_t note)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_OFF, 0xFFu, (uint16_t)note, 0);
        return;
    }
#endif
    fourop_fm_dsp_note_off(note);
}
static void all_off_seam(void)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_ALL_OFF, 0xFFu, 0, 0);
        return;
    }
#endif
    fourop_fm_dsp_all_notes_off();
}
static int set_param_seam(uint32_t id, int32_t value)
{
    return fourop_fm_dsp_set_param(id, value);
}
static void bend_seam(uint32_t bend) { fourop_fm_dsp_set_bend_q16(bend); }

static synth_midi_ctx midi_ctx = {
    note_on_seam, note_off_seam, all_off_seam, set_param_seam, bend_seam,
    cc_to_param, param_min, param_max,
};
static synth_sysex_ctx sysex_ctx = {
    SYNTH_MODEL, SYNTH_N_PARAMS, SYNTH_N_PARTS, fourop_fm_dsp_get_param,
    part_bank, multi_bank, settings,
};
static synth_runtime_ctx runtime_ctx = {
    SYNTH_N_PARAMS, SYNTH_N_PARTS, SYNTH_ROUTING_BASE, set_param_seam,
    part_bank, multi_bank,
};

/* ---- audio callback (split-core by default: CPU0 drains + renders its range,
   dispatching CPU1 for the other half; single-core fallback) */
static void app_audio(int32_t *out, uint32_t n)
{
#if FM1_CPU1_USED
    fourop_fm_render_block((uint32_t)(uintptr_t)out);   /* CPU0: drain + split render */
#else
    fourop_fm_dsp_render(out, n);
#endif
    /* the per-op scope taps: channel 0 = the final mix (platform.c), channels
     * 1..N_TAP_CH = the 4 operators x 2 parts (the HOME 4-op scope/spectro). */
    for (uint32_t k = 0; k < fourop_fm_N_TAP_CH; k++)
        scope_push_ch(1u + k, fourop_fm_dsp_tap(k), n);
}

static int quiet_seam(void)
{
#if FM1_CPU1_USED
    return (int)dsp_status.quiet;
#else
    return fourop_fm_dsp_quiet();
#endif
}

/* ---- the panel <-> engine mirror: the engine owns the truth */
static int32_t last_ui[UI_PARAM_MAX];
static void ui_sync(void)
{
    int32_t *v = ui_params();
    uint32_t i;
    for (i = 0; i < PANEL.n_params; i++) {
        int32_t e = fourop_fm_dsp_get_param(i);
        if (v[i] != e) {
            if (last_ui[i] != v[i]) {                 /* the panel wrote it */
                fourop_fm_dsp_set_param(i, v[i]);
                e = fourop_fm_dsp_get_param(i);      /* the clamped value */
            }
            v[i] = e;
        }
        last_ui[i] = v[i];
    }
    /* part mute: force a muted part's `level` routing param to 0 (the UI's level
     * value is preserved; unmuting restores it through the normal mirror). The
     * routing layout is field-major (channel/low/high/level/delay), so part p's
     * level is SYNTH_ROUTING_BASE + 3*SYNTH_N_PARTS + p. */
    for (i = 0; i < SYNTH_N_PARTS; i++) {
        if (ui_part_muted((uint8_t)i))
            fourop_fm_dsp_set_param(SYNTH_ROUTING_BASE + 3u * SYNTH_N_PARTS + i, 0);
    }
}

/* ---- the app's action hooks (called by ui.c) */
void ui_act_note_on(uint8_t note, uint8_t vel)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, 0xFFu, note, vel);
        return;
    }
#endif
    fourop_fm_dsp_note_on(note, vel);                /* omni: every matching part */
}
void ui_act_note_off(uint8_t note)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_OFF, 0xFFu, note, 0);
        return;
    }
#endif
    fourop_fm_dsp_note_off(note);
}
void ui_act_set_step(uint8_t step) { (void)step; }
void ui_act_panic(void)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_ALL_OFF, 0xFFu, 0, 0);
        return;
    }
#endif
    fourop_fm_dsp_all_notes_off();
}
void ui_act_play(void) { }
void ui_act_stop(void) { }
/* ---- the app's save/load/apply helpers (the "single part" / "multi-patch" split) ---- */

/* save one part's timbre into a single-part slot; remember it as that part's
 * source so a multi-patch can reference it. */
static void save_part_to(uint8_t part, uint16_t slot)
{
    int32_t params[SYNTH_PARAM_MAX];
    uint32_t i, base = (uint32_t)part * SYNTH_N_PARAMS;
    if (slot >= PRESET_PART_SLOTS)
        return;
    for (i = 0; i < SYNTH_N_PARAMS; i++)
        params[i] = fourop_fm_dsp_get_param(base + i);
    preset_part_pack(part_bank + (uint32_t)slot * PP_RECORD(SYNTH_N_PARAMS),
                     ui_name_get(part), params, SYNTH_N_PARAMS);
    part_slot_cur[part] = (uint8_t)slot;
    bank_dirty = 1;
    t_change = fm1_ms;
}

static void save_part(uint8_t part, uint16_t slot) { save_part_to(part, slot); }

/* the first empty single-part slot (0xFF), or 0xFF when the bank is full */
static uint8_t empty_part_slot(void)
{
    uint32_t i;
    for (i = 0; i < PRESET_PART_SLOTS; i++)
        if (part_bank[i * PP_RECORD(SYNTH_N_PARAMS)] == PRESET_EMPTY)
            return (uint8_t)i;
    return 0xFFu;
}

/* save the composition (each part's source single part + the routing) into a
 * multi-patch slot. `mode` = what to do with the active part's live edits:
 * 0 = discard, 1 = save-as-new, 2 = mutate in place. */
static void save_multi(uint16_t slot, uint8_t mode)
{
    int32_t lv[SYNTH_N_PARTS], dl[SYNTH_N_PARTS], ch[SYNTH_N_PARTS];
    int32_t lo[SYNTH_N_PARTS], hi[SYNTH_N_PARTS];
    uint32_t i;
    if (slot >= PRESET_MULTI_SLOTS)
        return;
    if (mode != 0u) {
        uint8_t part = ui_part(), dst = part_slot_cur[part];
        if (mode == 1u || dst == 0xFFu) {          /* save-as-new, or no source yet */
            dst = empty_part_slot();
            if (dst == 0xFFu)
                return;                            /* bank full: nothing to save */
        }
        save_part_to(part, dst);                   /* mode 2 overwrites the source slot */
    }
    for (i = 0; i < SYNTH_N_PARTS; i++) {
        ch[i] = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 0u * SYNTH_N_PARTS + i);
        lo[i] = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 1u * SYNTH_N_PARTS + i);
        hi[i] = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 2u * SYNTH_N_PARTS + i);
        lv[i] = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 3u * SYNTH_N_PARTS + i);
        dl[i] = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 4u * SYNTH_N_PARTS + i);
    }
    preset_multi_pack(multi_bank + (uint32_t)slot * MP_RECORD(SYNTH_N_PARTS),
                      ui_name_get(2u), part_slot_cur, lv, dl, ch, lo, hi, SYNTH_N_PARTS);
    multi_dirty = 1;
    t_change = fm1_ms;
}

/* load a single-part slot into a part (its params, not its routing). */
static void load_part(uint8_t part, uint32_t slot)
{
    char name[PRESET_NAME_LEN];
    int32_t params[SYNTH_PARAM_MAX];
    const uint8_t *rec = part_bank + slot * PP_RECORD(SYNTH_N_PARAMS);
    uint32_t i, base = (uint32_t)part * SYNTH_N_PARAMS;
    if (slot >= PRESET_PART_SLOTS || rec[0] == PRESET_EMPTY ||
        !preset_part_unpack(rec, SYNTH_N_PARAMS, name, params))
        return;
    for (i = 0; i < SYNTH_N_PARAMS; i++)
        fourop_fm_dsp_set_param(base + i, params[i]);
    ui_name_set(part, name);                        /* reflect the loaded part's name */
    part_slot_cur[part] = (uint8_t)slot;
}

/* apply a multi patch and remember its name + each part's source single part. */
static void apply_multi(uint32_t slot)
{
    char name[PRESET_NAME_LEN];
    uint8_t ps[SYNTH_N_PARTS];
    int32_t lv[SYNTH_N_PARTS], dl[SYNTH_N_PARTS], ch[SYNTH_N_PARTS];
    int32_t lo[SYNTH_N_PARTS], hi[SYNTH_N_PARTS];
    uint32_t i;
    synth_preset_apply(&runtime_ctx, slot);
    if (slot >= PRESET_MULTI_SLOTS)
        return;
    if (preset_multi_unpack(multi_bank + slot * MP_RECORD(SYNTH_N_PARTS),
                            SYNTH_N_PARTS, name, ps, lv, dl, ch, lo, hi)) {
        for (i = 0; i < SYNTH_N_PARTS; i++)
            part_slot_cur[i] = ps[i];
        ui_name_set(1u, name);
    }
}

void ui_act_save(void)
{
    /* SAVE opens the save chooser (single part / multi-patch + slot); the commit
     * runs in the main loop. Pre-fill with the active part's source slot and the
     * current multi-patch slot. */
    uint16_t ps = part_slot_cur[ui_part()];
    ui_save_begin(0u, ps == 0xFFu ? 0u : ps, (uint16_t)cur_slot);
}

void ui_act_init_patch(void)
{
    uint32_t i;
    for (i = 0; i < fourop_fm_INIT_N; i++)
        fourop_fm_dsp_set_param(fourop_fm_init[i].id, fourop_fm_init[i].value);
    /* the spec's init state: part 1 active, op 1 active, part 1 unmuted, part 2 muted */
    ui_part_set(0u);
    ui_op_set(0u);
    ui_part_mute_set(0u, 0u);
    ui_part_mute_set(1u, 1u);
    part_slot_cur[0] = part_slot_cur[1] = 0xFFu;
    ui_name_set(0u, "INIT PART");
    ui_name_set(1u, "INIT PART");
    ui_name_set(2u, "INIT MULTI");
}
/* reset one part's timbre to the spec's init values + clear its source slot + name. */
static void init_part(uint8_t part)
{
    uint32_t i;
    for (i = 0; i < fourop_fm_INIT_N; i++) {
        uint16_t id = fourop_fm_init[i].id;
        if (id >= (uint32_t)part * SYNTH_N_PARAMS &&
            id < (uint32_t)(part + 1u) * SYNTH_N_PARAMS)
            fourop_fm_dsp_set_param(id, fourop_fm_init[i].value);
    }
    part_slot_cur[part] = 0xFFu;
    ui_name_set(part, "INIT PART");
}
void ui_act_init_part(void)
{
    init_part(ui_part());
}
void ui_act_name(uint8_t which)
{
    ui_name_editor_begin(which);
}
void ui_draw_custom(const ui_widget *w) { (void)w; }   /* no custom widgets in this panel */

/* ---- MIDI: the framework handlers, from the main loop and while the screen draws */
static void app_idle(void)
{
    if (idle_ok)
        synth_midi_poll(&midi_ctx);
}

#define KEY0 53u   /* key 0 = F3 */
#define GLO_CTX 5u /* the GLO context id (panel.json key order: home/edit/env/lfo/fx/glo) */

/* ---- the main loop, split for the browser emulator: app_init (the setup) +
   app_step (one millisecond of the loop). app_main keeps the frozen contract for
   the host/target builds; a web build drives app_init + app_step from an
   AudioWorklet instead of the blocking loop. */
static uint32_t app_prev, app_lit;
static uint8_t app_held[27];
static int32_t app_oct;
static uint32_t app_last_scl_ms, app_scl_pending, app_scl_pending_ms;
static uint32_t app_browser_open, app_browser_slot, app_browser_ms;
static uint32_t app_pbro_open, app_pbro_slot, app_pbro_ms;
static uint8_t app_pending_part;                    /* 0 = none, 1 = load, 2 = save, 3 = init */
static uint16_t app_pending_slot;                   /* the slot for a pending load/save */
static uint32_t app_alg_ms;                         /* the last ALGORITHM-knob turn (popup auto-close) */
static uint32_t app_saved_ms;                       /* the last save (the "SAVED SUCCESSFULLY" linger) */

static void app_init(void)
{
    int32_t bc, mt;

    app_prev = 0;
    app_lit = 0;
    memset(app_held, 0, sizeof app_held);
    app_oct = 0;
    app_last_scl_ms = app_scl_pending = app_scl_pending_ms = 0;
    app_browser_open = app_browser_slot = app_browser_ms = 0;
    app_pbro_open = app_pbro_slot = app_pbro_ms = 0;

    fourop_fm_dsp_reset();
#if FM1_CPU1_USED
    {
        fm1_guard_unlock_top();
        fm1_guard_pc_open();
        (void)fm1_cpu1_start();
        fm1_guard_enable(FM1_GUARD_PC);
        fm1_guard_lock_top();
    }
    lit_base = KEY0;
#endif
    memset(part_bank, 0xFF, sizeof part_bank);         /* 0xFF = empty before a load */
    memset(multi_bank, 0xFF, sizeof multi_bank);
    preset_part_bank_load(part_bank, SYNTH_N_PARAMS);   /* an unreadable slot stays 0xFF = empty */
    preset_multi_bank_load(multi_bank, SYNTH_N_PARAMS, SYNTH_N_PARTS);
    if (preset_settings_load(settings) || !preset_settings_unpack(settings, &bc, &mt))
        bc = 0, mt = 0;
    if (bc >= 0 && bc <= 15)
        set_param_seam(SYNTH_ROUTING_BASE + 0u * SYNTH_N_PARTS + 0u, bc);  /* part 0's channel */
    /* master_tune has no pitch-tune param in this patch; it rides along for later */
    (void)mt;
    memcpy(saved_settings, settings, ST_RECORD);
    part_slot_cur[0] = part_slot_cur[1] = 0xFFu;
    cur_slot = 0u;
    apply_multi(0u);                                   /* multi slot 0: a valid record applies */

    ui_init(&PANEL);
    ui_name_set(0u, "INIT PART");
    ui_name_set(1u, "INIT PART");
    ui_name_set(2u, "INIT MULTI");
    ui_sync();                                         /* the engine's defaults reach the screen */
}

static void app_step(void)
{
    uint32_t keys, down, up, b, rel, base, k;
    int32_t e, ch0;

    platform_poll();

    keys = fm1_in.notes;
    down = keys & ~app_prev;
    up = app_prev & ~keys;
    app_prev = keys;
    base = (uint32_t)((int32_t)KEY0 + 12 * app_oct);
    {
        uint32_t now = fm1_ms;
        uint32_t scl = fm1_in.buttons & (1u << BTN_SEL);
        ch0 = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 0u * SYNTH_N_PARTS + 0u);
        if (ch0 < 0 || ch0 > 15)
            ch0 = 0;
        if (ui_name_editing() != 0xFFu) {
            /* the name editor: KNOB1 = char, KNOB2 = cursor, SEL = backspace,
               SAVE = ok, HOME = cancel; the keys + page are inert while open. */
            int32_t k1 = fm1_enc_take(ENC_KNOB1);
            int32_t k2 = fm1_enc_take(ENC_KNOB2);
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
        } else if (ui_save_mode_open()) {
            /* the save-mode chooser (step 2 of a multi-patch save): KNOB1 =
               mode, SAVE = save, HOME = back to the slot chooser. */
            int32_t k1 = fm1_enc_take(ENC_KNOB1);
            int32_t k2 = fm1_enc_take(ENC_KNOB2);
            if (k1)
                ui_save_mode_move(k1);
            (void)k2;                              /* the slot is fixed in step 2 */
            b = fm1_input_edges(&rel);
            if (b & (1u << BTN_SAVE)) {
                uint8_t mode = ui_save_mode();
                uint16_t slot = ui_save_slot();
                ui_save_mode_commit();
                ui_save_commit();
                save_multi(slot, mode);
                ui_popup_saved();
                app_saved_ms = fm1_ms;
            }
            if (b & (1u << BTN_HOME))
                ui_save_mode_cancel();
        } else if (ui_save_open()) {
            /* the save chooser: KNOB1 = kind, KNOB2 = slot, SAVE = save,
               HOME = cancel; the keys + page are inert while open. */
            int32_t k1 = fm1_enc_take(ENC_KNOB1);
            int32_t k2 = fm1_enc_take(ENC_KNOB2);
            if (k1)
                ui_save_kind_move(k1);
            if (k2)
                ui_save_slot_move(k2);
            b = fm1_input_edges(&rel);
            if (b & (1u << BTN_SAVE)) {
                uint8_t kind = ui_save_kind();
                uint16_t slot = ui_save_slot();
                if (kind == 0u) {
                    ui_save_commit();
                    app_pending_part = 2u;             /* save a single part */
                    app_pending_slot = slot;
                    ui_part_chooser_begin(ui_part(), 0);
                } else {
                    ui_save_mode_begin();          /* step 2 for a multi-patch */
                }
            }
            if (b & (1u << BTN_HOME))
                ui_save_cancel();
        } else if (ui_part_chooser_open()) {
            /* the "which single part" chooser: KNOB1 = part, SAVE = apply, HOME = cancel */
            int32_t k1 = fm1_enc_take(ENC_KNOB1);
            if (k1)
                ui_part_chooser_move(k1);
            b = fm1_input_edges(&rel);
            if (b & (1u << BTN_SAVE)) {
                uint8_t part = ui_part_chooser_part(), pending = app_pending_part;
                ui_part_chooser_commit();
                if (pending == 1u) load_part(part, app_pending_slot);
                else if (pending == 2u) {
                    save_part(part, app_pending_slot);
                    ui_popup_saved();
                    app_saved_ms = fm1_ms;
                } else if (pending == 3u) init_part(part);
                app_pending_part = 0u;
            }
            if (b & (1u << BTN_HOME)) {
                ui_part_chooser_cancel();
                app_pending_part = 0u;
            }
        } else if (ui_copy_open()) {
            /* the page-copy chooser: KNOB1 = target, SAVE = copy, HOME = cancel */
            int32_t k1 = fm1_enc_take(ENC_KNOB1);
            if (k1)
                ui_copy_move(k1);
            b = fm1_input_edges(&rel);
            if (b & (1u << BTN_SAVE)) {
                uint8_t part, op;
                ui_copy_target(&part, &op);
                ui_copy_commit();
                ui_copy_apply(part, op);
                ui_popup_saved();
                app_saved_ms = fm1_ms;
            }
            if (b & (1u << BTN_HOME))
                ui_copy_cancel();
        } else {
        for (k = 0; k < 27u; k++) {                /* the keys: play + echo, or SEL chords */
            if (down >> k & 1u) {
                if (scl) {
                    ui_op_mute_active();           /* SEL + key: mute the active op, no note */
                    app_held[k] = 0u;
                } else {
                    app_held[k] = (uint8_t)(base + k);
                    ui_handle(UI_SRC_KEY, app_held[k]);
                    midi_send(0x90u | (uint32_t)ch0, app_held[k], 100);
                }
            }
            if (up >> k & 1u && app_held[k]) {
                ui_act_note_off(app_held[k]);
                midi_send(0x80u | (uint32_t)ch0, app_held[k], 0);
                app_held[k] = 0u;
            }
        }

        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_EDIT)) {
            if (scl && ui_copy_available())
                ui_copy_begin();                    /* SEL+EDIT: copy the page's params */
            else
                ui_handle(UI_SRC_BTN_EDIT, -1);
        }
        if (b & (1u << BTN_HOME)) ui_handle(UI_SRC_BTN_HOME, -1);
        if (b & (1u << BTN_ENV)) ui_handle(UI_SRC_BTN_ENV, -1);
        if (b & (1u << BTN_LFO)) ui_handle(UI_SRC_BTN_LFO, -1);
        if (b & (1u << BTN_FX)) ui_handle(UI_SRC_BTN_FX, -1);
        if (b & (1u << BTN_GLO)) ui_handle(UI_SRC_BTN_GLO, -1);

        /* OCT-/OCT+: shift the keybed base note a whole octave (clamped ±2) */
        if (b & (1u << BTN_OCT_DOWN)) app_oct = app_oct > -2 ? app_oct - 1 : app_oct;
        if (b & (1u << BTN_OCT_UP))   app_oct = app_oct <  2 ? app_oct + 1 : app_oct;

        /* SEL: a tap advances the operator (deferred so a second tap within the
           window is a part switch instead); a double-tap switches the part. */
        if (b & (1u << BTN_SEL)) {
            if (now - app_last_scl_ms < 300u) {
                ui_part_next();
                app_scl_pending = 0;
            } else {
                app_scl_pending = 1;
                app_scl_pending_ms = now;
            }
            app_last_scl_ms = now;
        }

        /* ARP/SEQ/PLAY/REC: plain = operator mutes 1-4; SEL+ARP/PLAY = part 1
           mute, SEL+SEQ/REC = part 2 mute. */
        if (b & (1u << BTN_ARP)) {
            if (scl) ui_part_mute_toggle(0u);
            else ui_handle(UI_SRC_BTN_ARP, -1);
        }
        if (b & (1u << BTN_PLAY)) {
            if (scl) ui_part_mute_toggle(0u);
            else ui_handle(UI_SRC_BTN_PLAY, -1);
        }
        if (b & (1u << BTN_SEQ)) {
            if (scl) ui_part_mute_toggle(1u);
            else ui_handle(UI_SRC_BTN_SEQ, -1);
        }
        if (b & (1u << BTN_REC)) {
            if (scl) ui_part_mute_toggle(1u);
            else ui_handle(UI_SRC_BTN_REC, -1);
        }

        /* SAVE: plain = open the save chooser (single part / multi-patch);
           SEL+SAVE = INIT PATCH (INIT PART in GLO). */
        if (b & (1u << BTN_SAVE)) {
            if (scl) {
                if (ui_top() == GLO_CTX) {
                    app_pending_part = 3u;             /* init a single part */
                    ui_part_chooser_begin(ui_part(), "INIT PATCH");
                } else
                    ui_act_init_patch();
            } else {
                ui_handle(UI_SRC_BTN_SAVE, -1);
            }
        }

        /* the deferred single-tap (no second tap within the window) */
        if (app_scl_pending && now - app_scl_pending_ms >= 300u) {
            ui_handle(UI_SRC_BTN_SEL, -1);
            app_scl_pending = 0;
        }
        }
    }
    if (ui_popup_active()) {
        /* a modal popup captures all control: drain the page + preset encoders so
           a twist during the popup doesn't fire on the page once it closes. */
        fm1_enc_take(ENC_ALGORITHM);
        fm1_enc_take(ENC_SELECT);
        fm1_enc_take(ENC_KNOB1);
        fm1_enc_take(ENC_KNOB2);
        fm1_enc_take(ENC_KNOB3);
        fm1_enc_take(ENC_KNOB4);
        fm1_enc_take(ENC_PRESETS);
    } else {
        if ((e = fm1_enc_take(ENC_ALGORITHM)) != 0) {
            ui_handle(UI_SRC_ENC_ALGORITHM, e);
            app_alg_ms = fm1_ms;                   /* the algorithm scroll popup */
            ui_popup_alg((uint32_t)ui_params()[PANEL.alg]);
        }
        if ((e = fm1_enc_take(ENC_SELECT)) != 0) ui_handle(UI_SRC_ENC_SELECT, e);
        if ((e = fm1_enc_take(ENC_KNOB1)) != 0) ui_handle(UI_SRC_ENC_KNOB1, e);
        if ((e = fm1_enc_take(ENC_KNOB2)) != 0) ui_handle(UI_SRC_ENC_KNOB2, e);
        if ((e = fm1_enc_take(ENC_KNOB3)) != 0) ui_handle(UI_SRC_ENC_KNOB3, e);
        if ((e = fm1_enc_take(ENC_KNOB4)) != 0) ui_handle(UI_SRC_ENC_KNOB4, e);
    }

    /* the algorithm scroll popup auto-closes ~600 ms after the knob stops */
    if (app_alg_ms && fm1_ms - app_alg_ms >= 600u) {
        ui_popup_hide();
        app_alg_ms = 0u;
    }

    /* the "SAVED SUCCESSFULLY" acknowledgement lingers ~750 ms */
    if (app_saved_ms && fm1_ms - app_saved_ms >= 750u) {
        ui_popup_hide();
        app_saved_ms = 0u;
    }

    /* the preset browsers: the PRESETS encoder opens the multi-patch (2-part)
       browser except in GLO, where it opens the single-part browser; 2 s with
       no encoder input loads the selection (or, if already loaded, just clears). */
    {
        int32_t pe = fm1_enc_take(ENC_PRESETS);
        if (ui_top() == GLO_CTX) {
            if (pe != 0) {
                if (!app_pbro_open) {
                    app_pbro_open = 1;
                    app_pbro_slot = 0u;
                }
                if (pe > 0)
                    app_pbro_slot = (app_pbro_slot + 1u) % PRESET_PART_SLOTS;
                else
                    app_pbro_slot = (app_pbro_slot + PRESET_PART_SLOTS - 1u) % PRESET_PART_SLOTS;
                app_pbro_ms = fm1_ms;
                {
                    char name[PRESET_NAME_LEN];
                    int32_t params[SYNTH_PARAM_MAX];
                    const uint8_t *rec =
                        part_bank + app_pbro_slot * PP_RECORD(SYNTH_N_PARAMS);
                    if (rec[0] != PRESET_EMPTY &&
                        preset_part_unpack(rec, SYNTH_N_PARAMS, name, params))
                        ui_popup_show_part(app_pbro_slot, name);
                    else
                        ui_popup_show_part(app_pbro_slot, 0);
                }
            }
            if (app_pbro_open && fm1_ms - app_pbro_ms >= 2000u) {
                app_pending_part = 1u;                 /* load a single part */
                app_pending_slot = app_pbro_slot;
                ui_part_chooser_begin(ui_part(), 0);
                ui_popup_hide();
                app_pbro_open = 0;
            }
        } else {
            if (pe != 0) {
                if (!app_browser_open) {
                    app_browser_open = 1;
                    app_browser_slot = cur_slot;
                }
                if (pe > 0)
                    app_browser_slot = (app_browser_slot + 1u) % PRESET_MULTI_SLOTS;
                else
                    app_browser_slot = (app_browser_slot + PRESET_MULTI_SLOTS - 1u) % PRESET_MULTI_SLOTS;
                app_browser_ms = fm1_ms;
                {
                    char name[PRESET_NAME_LEN];
                    uint8_t ps[SYNTH_N_PARTS];
                    int32_t lv[SYNTH_N_PARTS], dl[SYNTH_N_PARTS], ch[SYNTH_N_PARTS];
                    int32_t lo[SYNTH_N_PARTS], hi[SYNTH_N_PARTS];
                    const uint8_t *rec =
                        multi_bank + app_browser_slot * MP_RECORD(SYNTH_N_PARTS);
                    if (rec[0] != PRESET_EMPTY &&
                        preset_multi_unpack(rec, SYNTH_N_PARTS, name, ps, lv, dl, ch, lo, hi))
                        ui_popup_show(app_browser_slot, name);
                    else
                        ui_popup_show(app_browser_slot, 0);
                }
            }
            if (app_browser_open && fm1_ms - app_browser_ms >= 2000u) {
                if (app_browser_slot != cur_slot) {
                    apply_multi(app_browser_slot);
                    cur_slot = app_browser_slot;
                }
                ui_popup_hide();
                app_browser_open = 0;
            }
        }
    }

    synth_midi_poll(&midi_ctx);
    synth_sysex_poll(&sysex_ctx);
    ui_sync();

    /* the SysEx settings write reached `settings`: persist it once silent */
    if (memcmp(settings, saved_settings, ST_RECORD)) {
        set_dirty = 1;
        t_change = fm1_ms;
    }

#if FM1_CPU1_USED
    lit_base = base;
    app_lit = dsp_status.lit;                    /* published by the render job */
#else
    app_lit = fourop_fm_dsp_lit(base);
#endif
    for (k = 0; k < 27u; k++)
        fm1_led_key(KEY_LED(k), app_lit >> k & 1u);
    fm1_led_key(BTN_OCT_DOWN, app_oct < 0);
    fm1_led_key(BTN_OCT_UP, app_oct > 0);

    idle_ok = 1;
    ui_redraw(fm1_ms);
    idle_ok = 0;

    if (quiet_seam() && fm1_ms - t_change > 2000u) {
        if (bank_dirty) {                          /* silent-only saves (the store erases) */
            preset_part_bank_save(part_bank, SYNTH_N_PARAMS);
            bank_dirty = 0;
        }
        if (multi_dirty) {
            preset_multi_bank_save(multi_bank, SYNTH_N_PARAMS, SYNTH_N_PARTS);
            multi_dirty = 0;
        }
        if (set_dirty) {
            preset_settings_save(settings);
            memcpy(saved_settings, settings, ST_RECORD);
            set_dirty = 0;
        }
    }
}

static void app_main(void)
{
    app_init();
    for (;;)
        app_step();
}
