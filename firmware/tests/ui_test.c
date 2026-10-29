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
void scope_spectrum(uint16_t *mag, uint32_t nbins)
{
    uint32_t b;
    for (b = 0; b < nbins; b++)
        mag[b] = 0;
}
uint32_t scope_seq(void) { return 0; }

#include "ui.h"
#include "accept.h"
#include "ui.c"

/* action hooks: record calls for the assertions */
static int n_note_on, n_set_step, n_panic, n_save;
void ui_act_note_on(uint8_t note, uint8_t vel) { (void)note; (void)vel; n_note_on++; }
void ui_act_note_off(uint8_t note) { (void)note; }
void ui_act_set_step(uint8_t step) { (void)step; n_set_step++; }
void ui_act_save(void) { n_save++; }
void ui_act_panic(void) { n_panic++; }
void ui_act_play(void) {}
void ui_act_stop(void) {}
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
        CHECK(ui_streq(s, "on"), "mute 1 formats as on");
        ui_params()[P_mute] = 0;        ui_param_fmt(P_mute, 0, s, sizeof s);
        CHECK(ui_streq(s, "off"), "mute 0 formats as off");
        ui_params()[P_cutoff] = 0;      ui_param_fmt(P_cutoff, 0, s, sizeof s);
        CHECK(ui_streq(s, "off"), "cutoff 0 formats as off");
        ui_params()[P_fold] = 16384;    ui_param_fmt(P_fold, 0, s, sizeof s);
        CHECK(ui_streq(s, "50%"), "fold 16384/32767 formats as 50%");
        ui_params()[P_res] = 0;         ui_param_fmt(P_res, 0, s, sizeof s);
        CHECK(ui_streq(s, "100%"), "res (inverted) 0 formats as 100%");
        ui_params()[P_semi] = 2731;     ui_param_fmt(P_semi, 0, s, sizeof s);
        CHECK(ui_streq(s, "1.00st"), "semi 2731 formats as 1.00st");
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

    if (failures) {
        printf("%d UI failures\n", failures);
        return 1;
    }
    printf("ok: UI kit acceptance (home/edit/step/fx, KEY override, slot, op wrap, switch)\n");
    return 0;
}
