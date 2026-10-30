/* SPDX-License-Identifier: GPL-3.0-only */
/* RIB's shipped demo app: a sine wave on the keys, and that is all. This file is
 * included by rib.c (the frozen framework); it is the reference for the app half of
 * the contract — the app provides `app_audio`, `app_main`, `app_idle`, the `ui_act_*`
 * hooks and `ui_draw_custom`; the framework provides the platform, the UI kit, and
 * the synth services (synth_midi/synth_sysex/synth_runtime). A synth project swaps
 * this file for its own `app.c` (the `umetate build --synth` composition). */
#include "rib_dsp.h"
#include "panel.h"

/* ---- audio callback; the kernel is a distinct translation unit */
static void app_audio(int32_t *out, uint32_t n)
{
#if FM1_CPU1_USED
    if (fm1_c1_on && fm1_cpu1_run(rib_render_block, (uint32_t)(uintptr_t)out) && fm1_cpu1_wait() == 0)
        return;
    rib_render_block((uint32_t)(uintptr_t)out);  /* single-core, or core 1 gave up */
#else
    rib_dsp_render(out, n);
#endif
}

/* ---- notes (the UI action hooks route here) */
static uint32_t last_note = 255;
static void play(uint32_t note, uint32_t vel)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_ON, 0xFFu, (uint16_t)note, (uint16_t)vel);
        last_note = note;
        return;
    }
#endif
    rib_dsp_note_on(note, vel);
    last_note = note;
}
static void stop(uint32_t note)
{
#if FM1_CPU1_USED
    if (fm1_c1_on) {
        dsp_cmd_push(UMETATE_DSP_CMD_NOTE_OFF, 0xFFu, (uint16_t)note, 0);
        return;
    }
#endif
    rib_dsp_note_off(note);
}
static int quiet(void)
{
#if FM1_CPU1_USED
    return (int)dsp_status.quiet;
#else
    return rib_dsp_quiet();
#endif
}

/* ---- the screen: the keyboard is drawn directly (the instrument; the UI kit renders the panel's widgets) */
#define C_ACC RGB(180, 140, 255)                /* lilac, as the logo */
#define C_KEY RGB(210, 210, 210)
#define C_OFF RGB(90, 90, 90)
#define KEY0 53u                                /* key 0 = F3 */
static int black(uint32_t note) { return (0x54Au >> (note % 12u)) & 1u; }

static void draw_keys(uint32_t lit)             /* bit k: key k sounds */
{
    uint32_t k, w = 0;
    cv_begin(240, 48, C_BLACK);
    for (k = 0; k < 27u; k++)                   /* 16 white keys of 14 px from x = 8 */
        if (!black(KEY0 + k)) {
            cv_rect(8 + (int32_t)w * 14, 0, 13, 48, lit >> k & 1u ? C_ACC : C_KEY);
            w++;
        }
    for (k = 0, w = 0; k < 27u; k++)            /* the black ones on the line between two white */
        if (black(KEY0 + k))
            cv_rect(8 + (int32_t)w * 14 - 5, 0, 9, 30, lit >> k & 1u ? C_ACC : C_BLACK);
        else
            w++;
    cv_blit(0, 152);
}

/* ---- the app's action hooks (called by ui.c) */
void ui_act_note_on(uint8_t note, uint8_t vel) { play(note, vel); }
void ui_act_note_off(uint8_t note) { stop(note); }
void ui_act_set_step(uint8_t step) { (void)step; }
void ui_act_panic(void) { rib_dsp_all_off(); }
void ui_act_play(void) { }
void ui_act_stop(void) { }
void ui_act_save(void) { }
void ui_act_init_patch(void) { }
void ui_act_init_part(void) { }
void ui_act_name(uint8_t which) { (void)which; }
void ui_draw_custom(const ui_widget *w) { (void)w; }   /* no custom widgets in the demo panel */

/* ---- MIDI in: from the main loop, and from app_idle while the screen draws (idle_ok) */
static struct { uint8_t oct, ch; } set = {0, 0};   /* what survives a power-off */
static uint32_t idle_ok, midi_src, clk_n, clk_t0, clk_bpm, clk_run, clk_beat_ms;

static void midi_in(void)
{
    uint8_t st, d1, d2;
    int src;
    while ((src = midi_get(&st, &d1, &d2)) != 0) {   /* 1 USB, 2 the TRS jack */
        uint32_t ty = st & 0xF0u;
        if (st == 0xF8u) {                      /* clock: 24 a quarter note */
            if (clk_n % 24u == 0u) {
                if (clk_n) {
                    uint32_t ms = fm1_ms - clk_t0;
                    clk_bpm = ms ? (60000u + ms / 2u) / ms : 0;
                }
                clk_t0 = fm1_ms;
                clk_beat_ms = fm1_ms;
            }
            clk_n++;
            continue;
        }
        if (st == 0xFAu) { clk_run = 1; clk_n = 0; continue; }   /* START */
        if (st == 0xFBu) { clk_run = 1; continue; }              /* CONTINUE */
        if (st == 0xFCu) { clk_run = 0; continue; }              /* STOP */
        if (set.ch && (st & 15u) != set.ch - 1u) continue;      /* not our channel */
        if (ty == 0x90u && d2) { play(d1, d2); midi_src = (uint32_t)src; }
        else if (ty == 0x80u || ty == 0x90u) stop(d1);
    }
}
static void app_idle(void)
{
    if (idle_ok) midi_in();
}

static void app_main(void)
{
    uint32_t prev = 0, k, dirty = 0, t_change = 0, lit_drawn = ~0u;
    uint8_t held[27] = {0};                     /* the note each key plays */
#if BOARD_SMK37
    static const uint8_t WHITE[16] = {0, 2, 4, 6, 7, 9, 11, 12, 14, 16, 18, 19, 21, 23, 24, 26};
    uint8_t pad_note[16] = {0}, ext_note[FM1_NKEY] = {0};
    smk_pw_t wheel = {0};
    smk_pad_events = 1;
#endif
    rib_dsp_reset();
#if FM1_CPU1_USED
    {
        fm1_guard_unlock_top();
        fm1_guard_pc_open();
        (void)fm1_cpu1_start();
        fm1_guard_enable(FM1_GUARD_PC);
        fm1_guard_lock_top();
    }
#endif
    if (settings_load(&set, sizeof set) || (int8_t)set.oct < -2 || (int8_t)set.oct > 2 || set.ch > 16u)
        set.oct = 0, set.ch = 0;

    ui_init(&PANEL);
    ui_params()[P_octave] = (int8_t)set.oct;
    ui_params()[P_channel] = set.ch;
    ui_params()[P_note] = -1;

    for (;;) {
        uint32_t keys, down, up, b, rel, lit = 0, out_ch = set.ch ? set.ch - 1u : 0u;
        int32_t oct, e;
        uint32_t base;
        platform_poll();

        keys = fm1_in.notes;
        down = keys & ~prev;
        up = prev & ~keys;
        prev = keys;
        oct = ui_params()[P_octave];
        base = (uint32_t)((int32_t)KEY0 + 12 * oct);
        for (k = 0; k < 27u; k++) {
#if BOARD_SMK37
            uint32_t vel = fm1_in.key_vel[SMK_KEY_F3 + k];
#else
            uint32_t vel = 100;
#endif
            if (down >> k & 1u) { held[k] = (uint8_t)(base + k); ui_handle(UI_SRC_KEY, held[k]); midi_send(0x90u | out_ch, held[k], vel); }
            if (up >> k & 1u) { ui_act_note_off(held[k]); midi_send(0x80u | out_ch, held[k], 0); }
        }
#if BOARD_SMK37
        while ((e = smk_extkey_take()) >= 0) {
            uint32_t key = (uint32_t)e >> 8, vel = (uint32_t)e & 0x7Fu;
            if (key >= FM1_NKEY) continue;
            if (vel) { ext_note[key] = (uint8_t)(base + key - SMK_KEY_F3); ui_handle(UI_SRC_KEY, ext_note[key]); midi_send(0x90u | out_ch, ext_note[key], vel); }
            else if (ext_note[key]) { ui_act_note_off(ext_note[key]); midi_send(0x80u | out_ch, ext_note[key], 0); ext_note[key] = 0; }
        }
        while ((e = smk_pad_take()) >= 0) {
            uint32_t pad = ((uint32_t)e >> 8) & 15u, vel = (uint32_t)e & 0x7Fu;
            uint32_t w = pad < 8u ? pad + 8u : pad - 8u;
            if (vel) { pad_note[pad] = (uint8_t)(base + WHITE[w]); ui_handle(UI_SRC_KEY, pad_note[pad]); midi_send(0x90u | out_ch, pad_note[pad], vel); }
            else if (pad_note[pad]) { ui_act_note_off(pad_note[pad]); midi_send(0x80u | out_ch, pad_note[pad], 0); pad_note[pad] = 0; }
        }
        {
            int32_t bd = smk_pw_bend(&wheel, fm1_in.wheel[0], fm1_ms);
            rib_dsp_set_bend_q16((uint32_t)(65536 + (bd * 3785 >> 12) + (((bd * bd) >> 12) * 109 >> 12)));
        }
#endif

        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_OCT_DOWN)) ui_handle(UI_SRC_BTN_OCT_DOWN, -1);
        if (b & (1u << BTN_OCT_UP)) ui_handle(UI_SRC_BTN_OCT_UP, +1);
        if ((e = fm1_enc_take(ENC_PRESETS)) != 0) ui_handle(UI_SRC_ENC_PRESETS, e);

        /* clamp the octave/channel params, then mirror into the persisted struct */
        {
            int32_t o = ui_params()[P_octave], c = ui_params()[P_channel];
            if (o < -2) o = -2;
            if (o > 2) o = 2;
            if (c < 0) c = 0;
            if (c > 16) c = 16;
            if (o != ui_params()[P_octave] || c != ui_params()[P_channel]) {
                ui_params()[P_octave] = o;
                ui_params()[P_channel] = c;
                set.oct = (uint8_t)(int8_t)o;
                set.ch = (uint8_t)c;
                dirty = 1;
                t_change = fm1_ms;
            }
        }

        midi_in();
        if (clk_bpm && fm1_ms - clk_t0 > 2000u) clk_bpm = 0, clk_run = 0;

        ui_params()[P_note] = (int32_t)last_note;
#if FM1_CPU1_USED
        lit_base = base;
        lit = dsp_status.lit;
#else
        lit = rib_dsp_lit(base);
#endif
        for (k = 0; k < 27u; k++)
            fm1_led_key(KEY_LED(k), lit >> k & 1u);
        fm1_led_key(BTN_OCT_DOWN, oct < 0);
        fm1_led_key(BTN_OCT_UP, oct > 0);
        fm1_led_key(BTN_PLAY, clk_run || (clk_bpm && fm1_ms - clk_beat_ms < 80u));
#if BOARD_SMK37
        for (k = 0; k < 16u; k++) {
            uint32_t w = k < 8u ? k + 8u : k - 8u, on = lit >> WHITE[w] & 1u;
            padled_set(k, on ? 90 : 4, on ? 60 : 2, on ? 128 : 8);
        }
        padled_flush();
#endif

        idle_ok = 1;
        ui_redraw(fm1_ms);
        if (lit != lit_drawn) { lit_drawn = lit; draw_keys(lit); }   /* the keyboard (the instrument) */
        idle_ok = 0;

        if (dirty && quiet() && fm1_ms - t_change > 2000u) {
            settings_save(&set, sizeof set);
            dirty = 0;
        }
    }
}
