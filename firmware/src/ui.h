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
    UI_SCOPE,          /* the oscilloscope: the last render block's waveform */
    UI_SPECTRO,        /* the spectrogram: Goertzel magnitude bars */
    UI_STATUS,         /* a status readout (algorithm + selected operator + mute) */
    UI_SUBHEADER,      /* a page's param-group title: "OP N <suffix>" / "PART N <suffix>" */
    UI_NAME,           /* a name row (label + the name string), a page slot -> the editor */
    UI_CUSTOM,         /* the cv_* canvas escape hatch: ui_draw_custom() draws it */
};

/* ---- the per-param display scale (the value's on-screen form) ---- */
enum {
    UI_DISP_RAW = 0,   /* the signed integer as-is */
    UI_DISP_RATIO,     /* a Q16 frequency multiplier -> "1.00" (65536 = base pitch) */
    UI_DISP_PCT,       /* [min,max] -> "N%" */
    UI_DISP_PCT_INV,   /* [min,max] -> "N%" inverted (100% = min; e.g. damping) */
    UI_DISP_ONOFF,     /* 0/1 -> "off"/"on" */
    UI_DISP_ONOFF_INV, /* 0/1 -> "on"/"off" (a mute: 0 = not muted = on) */
    UI_DISP_OFF_PCT,   /* <= 0 -> "off", else "N%" of [0,max] (e.g. a filter) */
    UI_DISP_HZ,        /* a Q32 rate -> "N.N Hz" */
    UI_DISP_SEMI,      /* a bipolar Q15 -> "+/-N.N st" (32768 = +1 octave) */
};

/* ---- binding kinds ---- */
enum { UI_BIND_PARAM = 0, UI_BIND_ACTION, UI_BIND_PAGE_SLOT };

/* ---- binding behaviors ---- */
enum { UI_ABS = 0, UI_REL, UI_MOMENTARY, UI_LATCH, UI_TOGGLE };

/* ---- actions (the arg is a context/page/step id, as the verb needs) ---- */
enum {
    UI_ACT_NOTE_ON = 0, UI_ACT_NOTE_OFF, UI_ACT_SET_STEP, UI_ACT_PUSH, UI_ACT_POP,
    UI_ACT_SWITCH, UI_ACT_POP_HOME, UI_ACT_NEXT_PAGE, UI_ACT_PREV_PAGE, UI_ACT_SET_PAGE,
    UI_ACT_PAGE, UI_ACT_BANK_NEXT, UI_ACT_BANK_PREV, UI_ACT_TOGGLE, UI_ACT_LATCH, UI_ACT_SAVE,
    UI_ACT_LOAD, UI_ACT_PANIC, UI_ACT_PLAY, UI_ACT_STOP,
    UI_ACT_OP_NEXT, UI_ACT_OP_PREV, UI_ACT_OP_MUTE,   /* the selected-operator group */
    UI_ACT_OP_MUTE_N,                                  /* mute operator `arg` (0..3) */
    UI_ACT_PART_NEXT, UI_ACT_PART_MUTE,                /* cycle / mute the active part */
    UI_ACT_INIT_PATCH, UI_ACT_INIT_PART,               /* the INIT PATCH/PART reset */
};

/* ---- the fixed input-source vocabulary (the generator maps panel strings to these) ---- */
enum {
    UI_SRC_KEY = 0,                              /* note key: value = MIDI note */
    UI_SRC_BTN_OCT_DOWN, UI_SRC_BTN_OCT_UP,      /* the FM-1's octave buttons */
    UI_SRC_ENC_PRESETS,                          /* the FM-1's preset encoder */
    UI_SRC_ENC_ALGORITHM,                        /* the FM-1's algorithm encoder */
    UI_SRC_ADC_MASTER,                           /* the FM-1's master knob (a smooth pot) */
    UI_SRC_ENC_SELECT,                           /* the FM-1's select encoder */
    UI_SRC_ENC_KNOB1, UI_SRC_ENC_KNOB2, UI_SRC_ENC_KNOB3, UI_SRC_ENC_KNOB4,
    UI_SRC_ENC_KNOB5, UI_SRC_ENC_KNOB6, UI_SRC_ENC_KNOB7,
    UI_SRC_BTN_EDIT, UI_SRC_BTN_HOME, UI_SRC_BTN_PLAY, UI_SRC_BTN_STOP, UI_SRC_BTN_REC,
    UI_SRC_BTN_SAVE, UI_SRC_BTN_SEQ,
    UI_SRC_BTN_FX, UI_SRC_BTN_SEL, UI_SRC_BTN_ENV, UI_SRC_BTN_LFO,
    UI_SRC_BTN_GLO, UI_SRC_BTN_ARP,
    UI_SRC_PAD_BASE,                             /* + 0..15 */
    UI_SRC_FADER_BASE,                           /* + 0..3 */
    UI_SRC_WHEEL_BASE,                           /* + 0..1 */
    UI_SRC_CC_BASE = 0x100,                      /* cc:N  -> + N */
    UI_SRC_NOTE_BASE = 0x200,                    /* note:N -> + N */
};

#define UI_NO_PARAM 0xFFFFu
#define UI_PARAM_MAX 256u   /* the ui_params[] cap; the generator errors beyond it */

/* ---- the generated (const, XIP) tables ---- */
typedef struct {
    uint8_t type, row, col, span;
    uint16_t param;                              /* param id (UI_NO_PARAM = none) */
    const char *text, *unit, *fmt;
    const char *const *items;                    /* list/grid items */
    uint8_t n_items;
} ui_widget;

typedef struct { const char *title; const ui_widget *w; uint8_t n; } ui_page;

/* a param's display scale (per param id; the value's on-screen form + stepping) */
typedef struct {
    uint8_t kind;                                /* UI_DISP_* */
    uint8_t curve;                               /* 0 = linear step, 1 = log step */
    int32_t min, max;                            /* the raw value's [min, max] */
} ui_param_disp;

typedef struct {
    uint8_t kind;                                /* UI_BIND_PARAM | UI_BIND_ACTION */
    uint16_t source;
    uint16_t target;                             /* param id (BIND_PARAM) */
    uint8_t action, arg;
    uint8_t behavior, curve;
} ui_binding;

typedef struct {
    const char *name;                            /* the menu name (the panel.json context key) */
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
    const uint16_t *env;                         /* the envelope group: n_op * 7 params */
    const ui_param_disp *disp;                   /* per-param display scale (n_params) */
    uint16_t alg;                                /* the algorithm param id (the header readout) */
    uint8_t n_part;                              /* the number of parts (the header) */
    uint16_t n_params;                           /* ui_params[] size */
    uint16_t n_widgets;                          /* ui_dirty[] size (across all pages) */
} ui_tables;

/* ---- the runtime API ---- */
void ui_init(const ui_tables *t);
void ui_push(uint8_t ctx);
void ui_pop(void);
void ui_switch(uint8_t ctx);                      /* replace the current mode (siblings) */
void ui_pop_home(void);
uint8_t ui_top(void);                            /* the active context id */
void ui_handle(uint16_t source, int32_t value);  /* resolve the source -> param/action */
int32_t *ui_params(void);                        /* the shared param_values[] */
uint8_t ui_part(void);                           /* the active part (0-based) */
void ui_part_next(void);                         /* cycle the active part (the SCL double-tap) */
void ui_part_set(uint8_t part);                  /* set the active part (INIT) */
void ui_op_set(uint8_t op);                      /* set the active operator (INIT) */
void ui_part_mute_toggle(uint8_t part);          /* mute/unmute a part (the header + chords) */
void ui_part_mute_set(uint8_t part, uint8_t muted); /* set a part's mute (INIT) */
uint8_t ui_part_muted(uint8_t part);             /* 1 = the part is muted */
void ui_op_mute_active(void);                    /* mute/unmute the active operator (SCL + key) */
void ui_popup_show(uint32_t slot, const char *name); /* the multi-patch preset-browser popup */
void ui_popup_show_part(uint32_t slot, const char *name); /* the single-part preset-browser popup */
void ui_popup_hide(void);                        /* clear the popup */

/* ---- the name strings + the name editor (the GLO multi-patch / single-part rows) ---- */
#define UI_NAME_LEN 16u                          /* 15 chars + NUL (the record's name field) */
const char *ui_name_get(uint8_t which);          /* 0 = single part, 1 = multi-patch */
void ui_name_set(uint8_t which, const char *name);
uint8_t ui_name_editing(void);                   /* 0xFF = none, else the name being edited */
void ui_name_editor_begin(uint8_t which);        /* open the editor pre-filled + saved copy */
void ui_name_editor_commit(void);                /* keep the edited name, close */
void ui_name_editor_cancel(void);                /* restore the saved name, close */
void ui_name_editor_char(int32_t delta);         /* scroll the char at the cursor (wrap) */
void ui_name_editor_move(int32_t delta);         /* move the cursor (wrap) */
void ui_name_editor_backspace(void);             /* delete the char at the cursor */

/* ---- the save chooser (the SAVE dialog: single part / multi-patch + slot) ---- */
uint8_t ui_save_open(void);                      /* 1 = the chooser is showing */
void ui_save_begin(uint8_t kind, uint16_t part_slot, uint16_t multi_slot); /* open, pre-filled */
uint8_t ui_save_kind(void);                      /* the selected kind: 0 = single part, 1 = multi-patch */
uint16_t ui_save_slot(void);                     /* the selected kind's slot */
void ui_save_kind_move(int32_t delta);           /* switch the selected row (wrap) */
void ui_save_slot_move(int32_t delta);           /* step the selected row's slot (wrap) */
void ui_save_commit(void);                       /* keep the choice, close */
void ui_save_cancel(void);                       /* discard, close */

void ui_param_fmt(uint16_t p, const char *unit, char *out, uint32_t n); /* format a value */
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
void ui_act_init_patch(void);                  /* INIT PATCH: reset the whole patch */
void ui_act_init_part(void);                   /* INIT PART: reset the active part */
void ui_act_name(uint8_t which);               /* open the name editor for `which` (0/1) */

/* ---- the canvas escape hatch: the app draws a UI_CUSTOM widget (the widget is
 * passed so the app can key off w->param or w->text) ---- */
void ui_draw_custom(const ui_widget *w);

/* ---- the safe-failure screen: drawn independently of the widget engine ---- */
void ui_safe_fail(const char *msg);
