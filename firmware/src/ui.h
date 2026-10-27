/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The shipped UI kit (docs/roadmap.md §12.6): a context-stack runtime that renders
 * a panel described by generated tables (gen/panel.h). Pure C, runs on CPU0 in
 * app_main (never in the audio callback), renders through gfx.c's canvas.
 *
 * The tables are `const` (XIP); the only mutable runtime state is the context/page
 * stack, the shared param values, the bend slot, and one `ui_dirty[]` entry per
 * widget (its last-drawn value, for the retained-mode dirty check).
 *
 * Layout convention (the 240x240 screen): `row` is a text line (16 px, FONT_S;
 * a 2-line widget uses `span` = 2, e.g. a FONT_L value), `col` is 0 = full width or
 * a column for side-by-side (a col = 120 px), `span` is the height in lines. */
#pragma once
#include <stdint.h>

/* ---- widget types ---- */
enum {
    UI_LABEL = 0,      /* static text (FONT_S, or FONT_L when span >= 2) */
    UI_VALUE,          /* a param value, formatted, with its unit */
    UI_BAR,            /* a horizontal 0..1 bar of a param */
    UI_PARAM_ROW,      /* a param name (text) + its value on one row */
    UI_PARAM_COLUMN,   /* a vertical block of param rows (span lines) */
    UI_LIST,           /* a list of items (the cursor selects) */
    UI_GRID,           /* a grid of cells (span lines tall) */
    UI_OP_ROW,         /* a param row resolved through the selected operator */
    UI_ENVELOPE,       /* the DX rate/level curve (straight-line approximation) */
    UI_CUSTOM,         /* the cv_* canvas escape hatch: ui_draw_custom() draws it */
};

/* ---- binding kinds ---- */
enum { UI_BIND_PARAM = 0, UI_BIND_ACTION, UI_BIND_PAGE_SLOT };

/* ---- binding behaviors ---- */
enum { UI_ABS = 0, UI_REL, UI_MOMENTARY, UI_LATCH, UI_TOGGLE };

/* ---- actions (the arg is a context/page/step id, as the verb needs) ---- */
enum {
    UI_ACT_NOTE_ON = 0, UI_ACT_NOTE_OFF, UI_ACT_SET_STEP, UI_ACT_PUSH, UI_ACT_POP,
    UI_ACT_POP_HOME, UI_ACT_NEXT_PAGE, UI_ACT_PREV_PAGE, UI_ACT_SET_PAGE,
    UI_ACT_BANK_NEXT, UI_ACT_BANK_PREV, UI_ACT_TOGGLE, UI_ACT_LATCH, UI_ACT_SAVE,
    UI_ACT_LOAD, UI_ACT_PANIC, UI_ACT_PLAY, UI_ACT_STOP,
    UI_ACT_OP_NEXT, UI_ACT_OP_PREV, UI_ACT_OP_MUTE,   /* the selected-operator group */
};

/* ---- the fixed input-source vocabulary (the generator maps panel strings to these) ---- */
enum {
    UI_SRC_KEY = 0,                              /* note key: value = MIDI note */
    UI_SRC_BTN_OCT_DOWN, UI_SRC_BTN_OCT_UP,      /* the FM-1's two buttons */
    UI_SRC_ENC_PRESETS,                          /* the FM-1's one encoder */
    UI_SRC_ADC_MASTER,                           /* the FM-1's master knob */
    UI_SRC_ENC_KNOB1, UI_SRC_ENC_KNOB2, UI_SRC_ENC_KNOB3, UI_SRC_ENC_KNOB4,
    UI_SRC_ENC_KNOB5, UI_SRC_ENC_KNOB6, UI_SRC_ENC_KNOB7, UI_SRC_ENC_SELECT,
    UI_SRC_BTN_EDIT, UI_SRC_BTN_HOME, UI_SRC_BTN_PLAY, UI_SRC_BTN_STOP, UI_SRC_BTN_REC,
    UI_SRC_BTN_SAVE, UI_SRC_BTN_SEQ,
    UI_SRC_PAD_BASE,                             /* + 0..15 */
    UI_SRC_FADER_BASE,                           /* + 0..3 */
    UI_SRC_WHEEL_BASE,                           /* + 0..1 */
    UI_SRC_CC_BASE = 0x100,                      /* cc:N  -> + N */
    UI_SRC_NOTE_BASE = 0x200,                    /* note:N -> + N */
};

#define UI_NO_PARAM 0xFFFFu

/* ---- the generated (const, XIP) tables ---- */
typedef struct {
    uint8_t type, row, col, span;
    uint16_t param;                              /* param id (UI_NO_PARAM = none) */
    const char *text, *unit, *fmt;
    const char *const *items;                    /* list/grid items */
    uint8_t n_items;
} ui_widget;

typedef struct { const char *title; const ui_widget *w; uint8_t n; } ui_page;

typedef struct {
    uint8_t kind;                                /* UI_BIND_PARAM | UI_BIND_ACTION */
    uint16_t source;
    uint16_t target;                             /* param id (BIND_PARAM) */
    uint8_t action, arg;
    uint8_t behavior, curve;
} ui_binding;

typedef struct {
    const ui_page *pages; uint8_t n_pages;
    const ui_binding *bindings; uint8_t n_bindings;
    void (*on_enter)(void); void (*on_exit)(void);
} ui_context;

typedef struct {
    const char *name;
    uint8_t home;                                /* the base context id (booted into) */
    const ui_context *ctx; uint8_t n_ctx;
    const ui_binding *global; uint8_t n_global;
    const uint16_t *mute;                        /* the selected-operator mute params (4) */
    const uint16_t *op_param;                    /* n_op * n_op_param operator-relative params */
    uint8_t n_op;                                /* the number of operators (0 = none) */
    uint8_t n_op_param;                          /* op-relative params per operator */
    uint16_t n_params;                           /* ui_params[] size */
    uint16_t n_widgets;                          /* ui_dirty[] size (across all pages) */
} ui_tables;

/* ---- the runtime API ---- */
void ui_init(const ui_tables *t);
void ui_push(uint8_t ctx);
void ui_pop(void);
void ui_pop_home(void);
uint8_t ui_top(void);                            /* the active context id */
void ui_handle(uint16_t source, int32_t value);  /* resolve the source -> param/action */
int32_t *ui_params(void);                        /* the shared param_values[] */
void ui_redraw(uint32_t now_ms);                 /* the retained-mode, rate-bounded redraw */
void ui_custom_set(uint32_t slot, int32_t value); /* drive a UI_CUSTOM widget's dirty value */

/* ---- the app's action hooks (implemented by the app, called by the runtime) ---- */
void ui_act_note_on(uint8_t note, uint8_t vel);
void ui_act_note_off(uint8_t note);
void ui_act_set_step(uint8_t step);
void ui_act_save(void);
void ui_act_panic(void);
void ui_act_play(void);
void ui_act_stop(void);

/* ---- the canvas escape hatch: the app draws a UI_CUSTOM widget (the widget is
 * passed so the app can key off w->param or w->text) ---- */
void ui_draw_custom(const ui_widget *w);

/* ---- the safe-failure screen: drawn independently of the widget engine ---- */
void ui_safe_fail(const char *msg);
