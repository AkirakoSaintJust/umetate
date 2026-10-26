/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The UI kit's host acceptance test (docs/roadmap.md P2-9): the home/edit/step
 * panel, the KEY -> note_on (global) override by KEY -> set_step (step), and a
 * relative param write through the edit context's binding. */
#include <stdio.h>
#include <stdint.h>

/* ---- the canvas (gfx.c) with a stubbed LCD (the widget renderers draw here) ---- */
static void lcd_sync(void) {}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{ (void)x; (void)y; (void)w; (void)h; (void)c; }
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *px)
{ (void)x; (void)y; (void)w; (void)h; (void)px; }
#include "gfx.c"

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

int main(void)
{
    ui_init(&PANEL);
    CHECK(ui_top() == 0, "boots into home (context 0)");

    /* home: the global KEY -> note_on */
    ui_handle(UI_SRC_KEY, 60);
    CHECK(n_note_on == 1 && n_set_step == 0, "home KEY -> note_on");

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

    /* BTN_EDIT -> push edit (context 1); ENC_PRESETS -> cutoff (+3 then -1) */
    ui_handle(UI_SRC_BTN_EDIT, 1);
    CHECK(ui_top() == 1, "BTN_EDIT pushes edit");
    CHECK(ui_params()[P_cutoff] == 0, "cutoff starts at 0");
    ui_handle(UI_SRC_ENC_PRESETS, 3);
    ui_handle(UI_SRC_ENC_PRESETS, -1);
    CHECK(ui_params()[P_cutoff] == 2, "relative ENC writes cutoff (3-1=2)");

    /* an unbound source is a no-op */
    ui_handle(UI_SRC_BTN_REC, 1);
    CHECK(n_note_on == 2 && n_set_step == 1, "unbound source is ignored");

    if (failures) {
        printf("%d UI failures\n", failures);
        return 1;
    }
    printf("ok: UI kit acceptance (home/edit/step, KEY override, param write)\n");
    return 0;
}
