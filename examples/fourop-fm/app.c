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

/* ---- the preset store's writable memory (the banks + the settings record) */
static uint8_t part_bank[PP_BANK(SYNTH_N_PARAMS)];
static uint8_t multi_bank[MP_BANK(SYNTH_N_PARTS)];
static uint8_t settings[ST_RECORD], saved_settings[ST_RECORD];
static uint32_t idle_ok, bank_dirty, set_dirty, t_change;

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
void ui_act_save(void)
{
    /* save part 0's timbre as part-patch slot 0 (persisted once the engine is silent) */
    int32_t params[SYNTH_PARAM_MAX];
    uint32_t i;
    for (i = 0; i < SYNTH_N_PARAMS; i++)
        params[i] = fourop_fm_dsp_get_param(i);
    preset_part_pack(part_bank, "saved", params, SYNTH_N_PARAMS);
    bank_dirty = 1;
    t_change = fm1_ms;
}
void ui_draw_custom(const ui_widget *w) { (void)w; }   /* no custom widgets in this panel */

/* ---- MIDI: the framework handlers, from the main loop and while the screen draws */
static void app_idle(void)
{
    if (idle_ok)
        synth_midi_poll(&midi_ctx);
}

#define KEY0 53u   /* key 0 = F3 */

static void app_main(void)
{
    uint32_t prev = 0, k, lit = 0;
    uint8_t held[27] = {0};
    int32_t bc, mt;
    uint32_t last_scl_ms = 0, scl_pending = 0, scl_pending_ms = 0;

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
    preset_part_bank_load(part_bank, SYNTH_N_PARAMS);   /* an unreadable slot: 0xFF = empty */
    preset_multi_bank_load(multi_bank, SYNTH_N_PARTS);
    if (preset_settings_load(settings) || !preset_settings_unpack(settings, &bc, &mt))
        bc = 0, mt = 0;
    if (bc >= 0 && bc <= 15)
        set_param_seam(SYNTH_ROUTING_BASE + 0u * SYNTH_N_PARTS + 0u, bc);  /* part 0's channel */
    /* master_tune has no pitch-tune param in this patch; it rides along for later */
    (void)mt;
    memcpy(saved_settings, settings, ST_RECORD);
    synth_preset_apply(&runtime_ctx, 0u);              /* multi slot 0: a valid record applies */

    ui_init(&PANEL);
    ui_sync();                                         /* the engine's defaults reach the screen */

    for (;;) {
        uint32_t keys, down, up, b, rel;
        int32_t e, ch0;
        platform_poll();

        keys = fm1_in.notes;
        down = keys & ~prev;
        up = prev & ~keys;
        prev = keys;
        {
            uint32_t now = fm1_ms;
            uint32_t scl = fm1_in.buttons & (1u << BTN_SEL);
            ch0 = fourop_fm_dsp_get_param(SYNTH_ROUTING_BASE + 0u * SYNTH_N_PARTS + 0u);
            if (ch0 < 0 || ch0 > 15)
                ch0 = 0;
            for (k = 0; k < 27u; k++) {                /* the keys: play + echo, or SCL chords */
                if (down >> k & 1u) {
                    if (scl) {
                        ui_op_mute_active();           /* SCL + key: mute the active op, no note */
                        held[k] = 0u;
                    } else {
                        held[k] = (uint8_t)(KEY0 + k);
                        ui_handle(UI_SRC_KEY, held[k]);
                        midi_send(0x90u | (uint32_t)ch0, held[k], 100);
                    }
                }
                if (up >> k & 1u && held[k]) {
                    ui_act_note_off(held[k]);
                    midi_send(0x80u | (uint32_t)ch0, held[k], 0);
                    held[k] = 0u;
                }
            }

            b = fm1_input_edges(&rel);
            if (b & (1u << BTN_EDIT)) ui_handle(UI_SRC_BTN_EDIT, -1);
            if (b & (1u << BTN_HOME)) ui_handle(UI_SRC_BTN_HOME, -1);
            if (b & (1u << BTN_ENV)) ui_handle(UI_SRC_BTN_ENV, -1);
            if (b & (1u << BTN_LFO)) ui_handle(UI_SRC_BTN_LFO, -1);
            if (b & (1u << BTN_FX)) ui_handle(UI_SRC_BTN_FX, -1);
            if (b & (1u << BTN_GLO)) ui_handle(UI_SRC_BTN_GLO, -1);

            /* SCL: a tap advances the operator (deferred so a second tap within the
             * window is a part switch instead); a double-tap switches the part. */
            if (b & (1u << BTN_SEL)) {
                if (now - last_scl_ms < 300u) {
                    ui_part_next();
                    scl_pending = 0;
                } else {
                    scl_pending = 1;
                    scl_pending_ms = now;
                }
                last_scl_ms = now;
            }

            /* ARP/SEQ/PLAY/REC: plain = operator mutes 1-4; SCL+ARP/PLAY = part 1
             * mute, SCL+SEQ/REC = part 2 mute. */
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

            /* the deferred single-tap (no second tap within the window) */
            if (scl_pending && now - scl_pending_ms >= 300u) {
                ui_handle(UI_SRC_BTN_SEL, -1);
                scl_pending = 0;
            }
        }
        if ((e = fm1_enc_take(ENC_ALGORITHM)) != 0) ui_handle(UI_SRC_ENC_ALGORITHM, e);
        if ((e = fm1_enc_take(ENC_SELECT)) != 0) ui_handle(UI_SRC_ENC_SELECT, e);
        if ((e = fm1_enc_take(ENC_KNOB1)) != 0) ui_handle(UI_SRC_ENC_KNOB1, e);
        if ((e = fm1_enc_take(ENC_KNOB2)) != 0) ui_handle(UI_SRC_ENC_KNOB2, e);
        if ((e = fm1_enc_take(ENC_KNOB3)) != 0) ui_handle(UI_SRC_ENC_KNOB3, e);
        if ((e = fm1_enc_take(ENC_KNOB4)) != 0) ui_handle(UI_SRC_ENC_KNOB4, e);

        synth_midi_poll(&midi_ctx);
        synth_sysex_poll(&sysex_ctx);
        ui_sync();

        /* the SysEx settings write reached `settings`: persist it once silent */
        if (memcmp(settings, saved_settings, ST_RECORD)) {
            set_dirty = 1;
            t_change = fm1_ms;
        }

#if FM1_CPU1_USED
        lit = dsp_status.lit;                    /* published by the render job */
#else
        lit = fourop_fm_dsp_lit(KEY0);
#endif
        for (k = 0; k < 27u; k++)
            fm1_led_key(KEY_LED(k), lit >> k & 1u);

        idle_ok = 1;
        ui_redraw(fm1_ms);
        idle_ok = 0;

        if (quiet_seam() && fm1_ms - t_change > 2000u) {
            if (bank_dirty) {                          /* silent-only saves (the store erases) */
                preset_part_bank_save(part_bank, SYNTH_N_PARAMS);
                bank_dirty = 0;
            }
            if (set_dirty) {
                preset_settings_save(settings);
                memcpy(saved_settings, settings, ST_RECORD);
                set_dirty = 0;
            }
        }
    }
}
