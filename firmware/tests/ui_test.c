/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The UI kit's host acceptance test (docs/roadmap.md §12.6): the home/edit/step/fx
 * panel, the KEY -> note_on (global) override by KEY -> set_step (step), a relative
 * param write, page-slot resolution (a `status` widget is not a slot), the operator
 * select wrap, and `switch` (EDIT/FX are siblings, not a stack). */
#include <stdio.h>
#include <stdint.h>

/* ---- the canvas (gfx.c) with a stubbed LCD (the widget renderers draw here) ---- */
static void lcd_sync(void) {}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{ (void)x; (void)y; (void)w; (void)h; (void)c; }
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *px)
{ (void)x; (void)y; (void)w; (void)h; (void)px; }
#include "gfx.c"

/* ---- the scope core (ui.c's UI_SCOPE/UI_SPECTRO renderers call it) ---- */
#include "scope.h"
int16_t scope_at(uint32_t i) { (void)i; return 0; }
int16_t scope_at_ch(uint32_t ch, uint32_t i) { (void)ch; (void)i; return 0; }
void scope_spectrum(uint16_t *mag, uint32_t nbins)
{
    uint32_t b;
    for (b = 0; b < nbins; b++)
        mag[b] = 0;
}
void scope_spectrum_ch(uint32_t ch, uint16_t *mag, uint32_t nbins)
{
    scope_spectrum(mag, nbins);
    (void)ch;
}
uint32_t scope_seq(void) { return 0; }

#include "ui.h"
#include "accept.h"
#include "ui.c"

/* action hooks: record calls for the assertions */
static int n_note_on, n_set_step, n_panic, n_save, n_init_patch, n_init_part;
void ui_act_note_on(uint8_t note, uint8_t vel) { (void)note; (void)vel; n_note_on++; }
void ui_act_note_off(uint8_t note) { (void)note; }
void ui_act_set_step(uint8_t step) { (void)step; n_set_step++; }
void ui_act_save(void) { n_save++; }
void ui_act_panic(void) { n_panic++; }
void ui_act_play(void) {}
void ui_act_stop(void) {}
void ui_act_init_patch(void) { n_init_patch++; }
void ui_act_init_part(void) { n_init_part++; }
void ui_act_name(uint8_t which) { (void)which; }
void ui_draw_custom(const ui_widget *w) { (void)w; }

static int failures;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

static int ui_streq(const char *a, const char *b)
{
    while (*a && *b && *a == *b) { a++; b++; }
    return *a == *b;
}

int main(void)
{
    ui_init(&PANEL);
    CHECK(ui_top() == 0, "boots into home (context 0)");

    /* home: the global KEY -> note_on */
    ui_handle(UI_SRC_KEY, 60);
    CHECK(n_note_on == 1 && n_set_step == 0, "home KEY -> note_on");

    /* page-slot resolution: the `status` widget (P_alg) is NOT slot 0 — the first
     * param_row (P_cutoff) is. A write to slot 0 must leave the algorithm alone
     * and move the cutoff (a per-param step, not a raw +1). */
    {
        int32_t alg0 = ui_params()[P_alg], cut0 = ui_params()[P_cutoff], fold0 = ui_params()[P_fold];
        ui_handle(UI_SRC_ENC_KNOB1, 5);                /* slot 0 = cutoff, not algorithm */
        CHECK(ui_params()[P_alg] == alg0, "status widget is not a page slot");
        CHECK(ui_params()[P_cutoff] != cut0, "slot 0 is the first param_row (cutoff moved)");
        ui_handle(UI_SRC_ENC_KNOB3, 3);                /* slot 2 = fold */
        CHECK(ui_params()[P_fold] != fold0, "slot 2 is the third param_row (fold moved)");
    }

    /* BTN_SEQ -> push step (context 2) */
    ui_handle(UI_SRC_BTN_SEQ, 1);
    CHECK(ui_top() == 2, "BTN_SEQ pushes step");

    /* step: the context KEY -> set_step overrides the global note_on */
    ui_handle(UI_SRC_KEY, 62);
    CHECK(n_note_on == 1, "step KEY does not note_on");
    CHECK(n_set_step == 1, "step KEY -> set_step");

    /* BTN_HOME -> pop_home */
    ui_handle(UI_SRC_BTN_HOME, 1);
    CHECK(ui_top() == 0, "BTN_HOME pops home");

    /* item 56: HOME on HOME advances to the next home page (wrapping) */
    ui_handle(UI_SRC_BTN_HOME, 1);
    CHECK(ui_top() == 0 && ui_pageno() == 1, "HOME on HOME advances the home page");
    ui_handle(UI_SRC_BTN_HOME, 1);
    CHECK(ui_top() == 0 && ui_pageno() == 0, "HOME on HOME wraps at the last home page");

    /* home again: KEY -> note_on */
    ui_handle(UI_SRC_KEY, 64);
    CHECK(n_note_on == 2, "home KEY -> note_on again");

    /* BTN_EDIT -> switch edit (context 1); ENC_PRESETS -> cutoff (a relative write) */
    ui_handle(UI_SRC_BTN_EDIT, 1);
    CHECK(ui_top() == 1, "BTN_EDIT switches to edit");
    {
        int32_t before = ui_params()[P_cutoff];
        ui_handle(UI_SRC_ENC_PRESETS, 3);              /* a relative write moves the param */
        CHECK(ui_params()[P_cutoff] != before, "relative ENC writes cutoff");
        ui_handle(UI_SRC_ENC_PRESETS, -9999);          /* and clamps, never runs away */
        CHECK(ui_params()[P_cutoff] == 0, "relative ENC clamps cutoff at its min");
    }

    /* the operator select wraps: mute op1, SEL -> op2, mute op2, SEL -> wraps to op1 */
    {
        int32_t o1 = ui_params()[P_op1_level], o2 = ui_params()[P_op2_level];
        ui_handle(UI_SRC_BTN_ENV, 1);                  /* op_next is at op1 (0): mute op1 */
        CHECK(ui_params()[P_op1_level] != o1, "op_mute toggles the selected operator (op1)");
        ui_handle(UI_SRC_BTN_SEL, 1);                  /* op1 -> op2 */
        ui_handle(UI_SRC_BTN_ENV, 1);                  /* mute op2 */
        CHECK(ui_params()[P_op2_level] != o2, "op_mute toggles the selected operator (op2)");
        ui_handle(UI_SRC_BTN_SEL, 1);                  /* op2 -> op1 (wrap) */
        ui_handle(UI_SRC_BTN_ENV, 1);                  /* mute op1 again */
        CHECK(ui_params()[P_op1_level] == o1, "op_next wraps 2 -> 1");
    }

    /* EDIT/FX are siblings: FX from edit goes straight to fx, EDIT back to edit */
    ui_handle(UI_SRC_BTN_FX, 1);
    CHECK(ui_top() == 3, "BTN_FX switches edit -> fx");
    ui_handle(UI_SRC_BTN_EDIT, 1);
    CHECK(ui_top() == 1, "BTN_EDIT switches fx -> edit (no HOME in between)");
    ui_handle(UI_SRC_BTN_HOME, 1);
    CHECK(ui_top() == 0, "BTN_HOME pops home from edit");

    /* item 21: the menu's own button advances to the next page (wrapping) */
    ui_handle(UI_SRC_BTN_EDIT, 1);
    CHECK(ui_top() == 1 && ui_pageno() == 0, "switch opens edit at page 0");
    ui_handle(UI_SRC_BTN_EDIT, 1);
    CHECK(ui_pageno() == 1, "the menu button advances to the next page");
    ui_handle(UI_SRC_BTN_EDIT, 1);
    CHECK(ui_pageno() == 0, "the menu button wraps at the last page");
    ui_handle(UI_SRC_BTN_HOME, 1);
    CHECK(ui_top() == 0, "BTN_HOME pops home after the page walk");

    /* an unbound source is a no-op */
    ui_handle(UI_SRC_BTN_REC, 1);
    CHECK(n_note_on == 2 && n_set_step == 1, "unbound source is ignored");

    /* the per-param display scale: ratio -> "N.NN", onoff -> words, off_pct -> "off",
       pct -> 0..100, pct_inv -> inverted, hz -> Hz, semi -> semitones */
    {
        char s[24];
        ui_params()[P_ratio] = 65536;   ui_param_fmt(P_ratio, 0, s, sizeof s);
        CHECK(ui_streq(s, "1.00"), "ratio 65536 formats as 1.00");
        ui_params()[P_ratio] = 32768;   ui_param_fmt(P_ratio, 0, s, sizeof s);
        CHECK(ui_streq(s, "0.50"), "ratio 32768 formats as 0.50");
        ui_params()[P_ratio] = 131072;  ui_param_fmt(P_ratio, 0, s, sizeof s);
        CHECK(ui_streq(s, "2.00"), "ratio 131072 formats as 2.00");
        ui_params()[P_mute] = 1;        ui_param_fmt(P_mute, 0, s, sizeof s);
        CHECK(ui_streq(s, "off"), "mute 1 (muted) formats as off");
        ui_params()[P_mute] = 0;        ui_param_fmt(P_mute, 0, s, sizeof s);
        CHECK(ui_streq(s, "on"), "mute 0 (not muted) formats as on");
        ui_params()[P_cutoff] = 0;      ui_param_fmt(P_cutoff, 0, s, sizeof s);
        CHECK(ui_streq(s, "off"), "cutoff 0 formats as off");
        ui_params()[P_fold] = 16384;    ui_param_fmt(P_fold, 0, s, sizeof s);
        CHECK(ui_streq(s, "50%"), "fold 16384/32767 formats as 50%");
        ui_params()[P_res] = 0;         ui_param_fmt(P_res, 0, s, sizeof s);
        CHECK(ui_streq(s, "100%"), "res (inverted) 0 formats as 100%");
        ui_params()[P_semi] = 2731;     ui_param_fmt(P_semi, 0, s, sizeof s);
        CHECK(ui_streq(s, "1.00st"), "semi 2731 formats as 1.00st");
        ui_params()[P_semi] = -2731;    ui_param_fmt(P_semi, 0, s, sizeof s);
        CHECK(ui_streq(s, "-1.00st"), "semi -2731 formats as -1.00st (sign-symmetric)");
        ui_params()[P_hz] = 97392;      ui_param_fmt(P_hz, 0, s, sizeof s);
        CHECK(ui_streq(s, "1.0Hz"), "hz 97392 formats as 1.0Hz");
    }

    /* a log-curve param steps multiplicatively, a linear one by a fraction; both
       clamp to [min, max] — a relative detent never runs off the end */
    ui_params()[P_fold] = 30000;
    ui_handle(UI_SRC_ENC_KNOB3, 9999);                /* slot 2 = fold (linear) */
    CHECK(ui_params()[P_fold] == 32767, "a linear step clamps at max");
    ui_params()[P_fold] = 0;
    ui_handle(UI_SRC_ENC_KNOB3, -9999);
    CHECK(ui_params()[P_fold] == 0, "a linear step clamps at min");

    /* a landmark param steps one landmark per detent, so no sparse entry is
       skipped (0.50 -> 1.00 -> 2.00, not 0.50 -> 2.00). */
    ui_params()[P_ratio] = 32768;
    ui_handle(UI_SRC_ENC_KNOB4, 1);
    CHECK(ui_params()[P_ratio] == 65536, "landmark step moves to the next ratio");
    ui_handle(UI_SRC_ENC_KNOB4, 1);
    CHECK(ui_params()[P_ratio] == 131072, "landmark step does not skip the last ratio");
    ui_handle(UI_SRC_ENC_KNOB4, -1);
    CHECK(ui_params()[P_ratio] == 65536, "landmark step moves back one ratio");
    ui_params()[P_ratio] = 1;  /* below the first landmark (e.g. a stale load) */
    ui_handle(UI_SRC_ENC_KNOB4, 1);
    CHECK(ui_params()[P_ratio] == 32768, "a step from below lands on the first landmark");
    ui_params()[P_ratio] = 131072;
    ui_handle(UI_SRC_ENC_KNOB4, 9999);
    CHECK(ui_params()[P_ratio] == 131072, "landmark stepping clamps at the last entry");

    /* an on/off param hard-clamps at its ends (no infinite 0<->1 wrap): scrolling
       past 1 stays 1, past 0 stays 0. */
    ui_params()[P_mute] = 1;
    ui_handle(UI_SRC_ENC_PRESETS, 9999);
    CHECK(ui_params()[P_mute] == 1, "an on/off param clamps at its max (no wrap)");
    ui_handle(UI_SRC_ENC_PRESETS, -9999);
    CHECK(ui_params()[P_mute] == 0, "an on/off param clamps at its min");

    /* the active part starts at 0; part_next is a no-op with one part */
    CHECK(ui_part() == 0, "ui_part starts at 0");

    /* part mute toggle + query (the header's part ON/OFF) */
    CHECK(ui_part_muted(0u) == 0, "part 0 starts unmuted");
    ui_part_mute_toggle(0u);
    CHECK(ui_part_muted(0u) == 1, "part mute toggle mutes part 0");
    ui_part_mute_toggle(0u);
    CHECK(ui_part_muted(0u) == 0, "part mute toggle unmutes part 0");

    /* the preset-browser popup shows + hides without crashing */
    ui_popup_show(7u, "MYSOUND");
    ui_popup_hide();

    /* the name strings + the name editor (char wheel + cursor + backspace) */
    {
        ui_name_set(0u, "ABC");
        CHECK(ui_streq(ui_name_get(0u), "ABC"), "name set/get round-trips");
        ui_name_editor_begin(0u);
        CHECK(ui_name_editing() == 0u, "name editor opens on the part name");
        ui_name_editor_move(1u);                 /* cursor -> 'B' */
        ui_name_editor_char(1u);                 /* 'B' -> 'C' (charset next) */
        ui_name_editor_char(-1u);                /* 'C' -> 'B' (back) */
        ui_name_editor_backspace();              /* delete 'B': "AC" */
        ui_name_editor_cancel();                 /* restore "ABC" */
        CHECK(ui_streq(ui_name_get(0u), "ABC"), "name editor cancel restores the name");
        ui_name_editor_begin(0u);
        ui_name_editor_char(1u);                 /* 'A' -> 'B': "BBC" */
        ui_name_editor_commit();                 /* keep "BBC" */
        CHECK(ui_streq(ui_name_get(0u), "BBC"), "name editor commit keeps the edit");
        CHECK(ui_name_editing() == 0xFFu, "name editor closed after commit");
    }

    /* the save chooser (kind toggle + slot wrap + commit/cancel) */
    {
        ui_save_begin(0u, 5u, 3u);
        CHECK(ui_save_open() == 1 && ui_save_kind() == 0u && ui_save_slot() == 5u,
              "save chooser opens on the single part + its slot");
        ui_save_kind_move(1u);                   /* -> multi-patch */
        CHECK(ui_save_kind() == 1u && ui_save_slot() == 3u,
              "save chooser kind toggles to multi-patch");
        ui_save_slot_move(1u);                   /* slot 3 -> 4 */
        ui_save_slot_move(-1u);                  /* back to 3 */
        CHECK(ui_save_slot() == 3u, "save chooser slot steps + wraps back");
        ui_save_kind_move(1u);                   /* back to single part */
        CHECK(ui_save_kind() == 0u, "save chooser kind toggles back");
        ui_save_cancel();
        CHECK(ui_save_open() == 0, "save chooser cancel closes");
        ui_save_begin(1u, 5u, 3u);
        ui_save_commit();
        CHECK(ui_save_open() == 0, "save chooser commit closes");
    }

    /* the save-mode chooser (step 2 of a multi-patch save: discard/new/mutate) */
    {
        ui_save_mode_begin();
        CHECK(ui_save_mode_open() == 1 && ui_save_mode() == 0u,
              "save-mode chooser opens on discard");
        ui_save_mode_move(1u);                   /* -> save-as-new */
        CHECK(ui_save_mode() == 1u, "save-mode chooser advances to save-as-new");
        ui_save_mode_move(1u);                   /* -> mutate */
        CHECK(ui_save_mode() == 2u, "save-mode chooser advances to mutate");
        ui_save_mode_move(1u);                   /* wraps -> discard */
        CHECK(ui_save_mode() == 0u, "save-mode chooser wraps to discard");
        ui_save_mode_move(-1u);                  /* -> mutate */
        CHECK(ui_save_mode() == 2u, "save-mode chooser wraps backwards");
        ui_save_mode_commit();
        CHECK(ui_save_mode_open() == 0, "save-mode chooser commit closes");
        ui_save_mode_begin();
        ui_save_mode_cancel();
        CHECK(ui_save_mode_open() == 0, "save-mode chooser cancel closes");
    }

    /* the "which single part" chooser: toggle + commit/cancel */
    {
        ui_part_chooser_begin(0u, 0);
        CHECK(ui_part_chooser_open() == 1 && ui_part_chooser_part() == 0u,
              "part chooser opens on the active part");
        ui_part_chooser_move(1u);                   /* -> part 2 */
        CHECK(ui_part_chooser_part() == 1u, "part chooser toggles to part 2");
        ui_part_chooser_move(1u);                   /* -> part 1 (toggle back) */
        CHECK(ui_part_chooser_part() == 0u, "part chooser toggles back to part 1");
        ui_part_chooser_commit();
        CHECK(ui_part_chooser_open() == 0, "part chooser commit closes");
        ui_part_chooser_begin(1u, 0);
        ui_part_chooser_cancel();
        CHECK(ui_part_chooser_open() == 0, "part chooser cancel closes");
    }

    if (failures) {
        printf("%d UI failures\n", failures);
        return 1;
    }
    printf("ok: UI kit acceptance (home/edit/step/fx, KEY override, slot, op wrap, switch)\n");
    return 0;
}
