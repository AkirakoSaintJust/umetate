/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The UI runtime (docs/roadmap.md §12.6). Included into the app after gfx.c, so the
 * canvas (cv_*, FONT_S/FONT_L) and the palette colors (C_*) are in scope. */
#include "ui.h"
#include "presets.h"   /* PRESET_PART_SLOTS / PRESET_MULTI_SLOTS (the save chooser's slot ranges) */
#include "math_tables.h"  /* fm1_rate_coeff / fm1_level_gain (the DX rate/level tables) */

#define UI_MAX_DEPTH 8u
#define UI_MAX_WIDGETS 24u
#define UI_ROW_H 16u          /* FONT_S glyph height; one row */
#define UI_COL_W 120u         /* a column (col 0 = full width) */
#define UI_REDRAW_MS 33u      /* ~30 Hz */

/* ---- minimal string helpers (libc.c has only memset/memcpy) ---- */
static uint32_t ui_strlen(const char *s)
{
    const char *p = s;
    while (*p)
        p++;
    return (uint32_t)(p - s);
}

static void ui_strcpy(char *d, const char *s)
{
    while ((*d++ = *s++) != 0)
        ;
}

static void ui_strcat(char *d, const char *s)
{
    ui_strcpy(d + ui_strlen(d), s);
}

static void ui_itoa(int32_t v, char *s)
{
    char tmp[12];
    uint32_t u, i = 0;
    if (v < 0)
        u = (uint32_t)(-(int64_t)v);
    else
        u = (uint32_t)v;
    do {
        tmp[i++] = (char)('0' + u % 10u);
        u /= 10u;
    } while (u);
    if (v < 0)
        tmp[i++] = '-';
    while (i)
        *s++ = tmp[--i];
    *s = 0;
}

/* ---- runtime state (the only mutable state; the tables are const) ---- */
static const ui_tables *ui_t;
static int32_t ui_param_v[UI_PARAM_MAX];
static uint8_t ui_stack[UI_MAX_DEPTH], ui_sp;   /* context ids; top = active */
static uint8_t ui_pagei[UI_MAX_DEPTH];          /* the page within each context */
static int32_t ui_last[UI_MAX_WIDGETS];         /* last-drawn value per widget slot */
static int32_t ui_custom_v[UI_MAX_WIDGETS];     /* UI_CUSTOM widgets' dirty values (app-set) */
static int32_t ui_cursor;                        /* list/grid selection */
static uint8_t ui_selected_op;                   /* the selected operator (0..3) for OP_* */
static uint8_t ui_selected_part;                 /* the active part (0..n_part-1) */
static uint8_t ui_part_mute[4];                  /* part mute flags (up to 4 parts) */
static int32_t ui_header_last = 0x7FFFFFFF;      /* the header's last-drawn value */
static char ui_popup_line[40];                   /* the preset-browser popup text */
static uint8_t ui_popup_on;                      /* 1 = the popup is showing */
static uint8_t ui_popup_alg_on;                  /* 1 = the algorithm-graph popup is showing */
static uint8_t ui_popup_alg_val;                 /* the algorithm the graph popup shows */
static char ui_name[3][UI_NAME_LEN];              /* [0] part 1, [1] part 2, [2] multi-patch */
static char ui_name_saved[UI_NAME_LEN];          /* the pre-edit copy (for cancel) */
static uint8_t ui_name_which, ui_name_cursor, ui_name_on;  /* the name-editor state */
static uint8_t ui_save_on, ui_save_which;        /* the save chooser: open flag + selected row */
static uint16_t ui_save_slots[2];                /* [0] single-part slot, [1] multi-patch slot */
static uint8_t ui_save_mode_on, ui_save_mode_which;  /* step 2: the multi-patch save mode */
static uint8_t ui_part_sel_on, ui_part_sel_which;  /* the "which single part" chooser */

static const ui_context *ui_ctx(void) { return &ui_t->ctx[ui_stack[ui_sp]]; }
static const ui_page *ui_cur_page(void) { return &ui_ctx()->pages[ui_pagei[ui_sp]]; }

static void ui_reset_page(void)
{
    uint32_t i;
    for (i = 0; i < UI_MAX_WIDGETS; i++)
        ui_last[i] = 0x7FFFFFFF;                 /* sentinel: everything redraws */
    ui_cursor = 0;
    ui_header_last = 0x7FFFFFFF;                 /* force the header to redraw too */
    lcd_fill(0, 0, 240, 240, C_BLACK);           /* drop the previous page's stale pixels */
}

void ui_init(const ui_tables *t)
{
    palette_set(0); /* load the default palette — C_LINE..C_HI (gfx.c) would stay black */
    if (t->n_params > UI_PARAM_MAX)
        return; /* a panel beyond the kit's param cap: not rendered (the generator checks too) */
    ui_t = t;
    ui_sp = 0;
    ui_stack[0] = t->home;
    ui_pagei[0] = 0;
    ui_reset_page();
    if (t->ctx[t->home].on_enter)
        t->ctx[t->home].on_enter();
}

void ui_push(uint8_t ctx)
{
    if (ui_sp + 1u < UI_MAX_DEPTH && ctx < ui_t->n_ctx) {
        ui_sp++;
        ui_stack[ui_sp] = ctx;
        ui_pagei[ui_sp] = 0;
        ui_reset_page();
        if (ui_ctx()->on_enter)
            ui_ctx()->on_enter();
    }
}

/* switch to `ctx`, replacing the current non-home mode (EDIT/FX/GLO are siblings,
 * not a stack): pops back to home first, then pushes. From home it is a plain push.
 * Pressing the menu's *own* button again (ctx == top) advances to the next page
 * (wrapping) instead of re-opening at page 0 — item 21. */
void ui_switch(uint8_t ctx)
{
    if (ui_stack[ui_sp] == ctx) {
        if (ui_ctx()->n_pages > 1u) {
            ui_pagei[ui_sp] = (uint8_t)((ui_pagei[ui_sp] + 1u) % ui_ctx()->n_pages);
            ui_reset_page();
        }
        return;
    }
    if (ui_sp)
        ui_pop();                                  /* leave the current mode (home stays) */
    ui_push(ctx);
}

void ui_pop(void)
{
    if (!ui_sp)
        return;
    if (ui_ctx()->on_exit)
        ui_ctx()->on_exit();
    ui_sp--;
    ui_reset_page();
}

void ui_pop_home(void)
{
    while (ui_sp) {
        if (ui_ctx()->on_exit)
            ui_ctx()->on_exit();
        ui_sp--;
    }
    ui_reset_page();
}

uint8_t ui_top(void) { return ui_stack[ui_sp]; }

uint8_t ui_pageno(void) { return ui_pagei[ui_sp]; }

int32_t *ui_params(void) { return ui_param_v; }

uint8_t ui_part(void) { return ui_selected_part; }

void ui_part_mute_toggle(uint8_t part)
{
    if (part < ui_t->n_part)
        ui_part_mute[part] = ui_part_mute[part] ? 0u : 1u;
}

uint8_t ui_part_muted(uint8_t part)
{
    return part < ui_t->n_part && ui_part_mute[part];
}

void ui_part_next(void)
{
    if (ui_t->n_part > 1u)
        ui_selected_part = (uint8_t)((ui_selected_part + 1u) % ui_t->n_part);
}

void ui_part_set(uint8_t part)
{
    if (part < ui_t->n_part)
        ui_selected_part = part;
}

void ui_op_set(uint8_t op)
{
    if (op < ui_t->n_op)
        ui_selected_op = op;
}

void ui_part_mute_set(uint8_t part, uint8_t muted)
{
    if (part < ui_t->n_part)
        ui_part_mute[part] = muted ? 1u : 0u;
}

/* the mute param id for operator `op` of the active part (the table is part-major:
 * n_part * 4 entries). */
static uint16_t ui_mute_param(uint32_t op)
{
    return ui_t->mute[(uint32_t)ui_selected_part * 4u + op];
}

void ui_op_mute_active(void)
{
    if (ui_t->mute && ui_selected_op < 4u) {
        uint16_t p = ui_mute_param(ui_selected_op);
        if (p < ui_t->n_params)
            ui_param_v[p] = ui_param_v[p] ? 0 : 1;
    }
}

/* resolve a source to its binding: the top context's bindings first, then global */
static const ui_binding *ui_resolve(uint16_t source)
{
    const ui_context *c = ui_ctx();
    uint32_t i;
    for (i = 0; i < c->n_bindings; i++)
        if (c->bindings[i].source == source)
            return &c->bindings[i];
    for (i = 0; i < ui_t->n_global; i++)
        if (ui_t->global[i].source == source)
            return &ui_t->global[i];
    return 0;
}

/* clamp a param's value to its [min, max] (the display scale's range, which the
 * DSP's set_param also enforces). A value must never sit outside its range — the
 * display forms assume it (an on/off that slid negative would read "on"). */
static void ui_clamp_param(uint16_t p)
{
    const ui_param_disp *d = (ui_t->disp && p < ui_t->n_params) ? &ui_t->disp[p] : 0;
    int32_t v = p < ui_t->n_params ? ui_param_v[p] : 0;
    if (!d)
        return;
    if (v < d->min)
        v = d->min;
    if (v > d->max)
        v = d->max;
    ui_param_v[p] = v;
}

/* step a param by `delta` detents per its display scale: linear params move by a
 * fraction of the range (128 detents full-scale), log params move multiplicatively
 * (~3% per detent, so 0 stays reachable). The result is clamped to [min, max].
 * A quantized param (`quantize` + a sorted landmark table) moves one landmark per
 * detent instead, so sparse ladders (the coarse ratios) never skip an entry. */
static void ui_step_param(uint16_t p, int32_t delta)
{
    const ui_param_disp *d = (ui_t->disp && p < ui_t->n_params) ? &ui_t->disp[p] : 0;
    int32_t v = p < ui_t->n_params ? ui_param_v[p] : 0;
    if (!delta)
        return;
    /* --- landmark quantization: one detent = the next/previous landmark --- */
    if (d && d->quantize && d->lm_count && d->landmarks) {
        int32_t step = delta;
        if (step > (int32_t)d->lm_count)
            step = (int32_t)d->lm_count;
        if (step < -(int32_t)d->lm_count)
            step = -(int32_t)d->lm_count;
        while (step > 0) {
            int32_t next = d->landmarks[d->lm_count - 1];
            uint8_t i;
            for (i = 0; i < d->lm_count; i++) {
                if (d->landmarks[i] > v) {
                    next = d->landmarks[i];
                    break;
                }
            }
            if (next <= v)
                break;
            v = next;
            step--;
        }
        while (step < 0) {
            int32_t prev = d->landmarks[0];
            uint8_t i;
            for (i = d->lm_count; i > 0; i--) {
                if (d->landmarks[i - 1] < v) {
                    prev = d->landmarks[i - 1];
                    break;
                }
            }
            if (prev >= v)
                break;
            v = prev;
            step++;
        }
        ui_param_v[p] = v;
        ui_clamp_param(p);
        return;
    }
    if (d && d->curve) {
        if (v == 0)
            v = delta > 0 ? 1 : -1;
        else {
            int32_t s = v >> 5;
            v += (s ? s : 1) * delta;
        }
    } else {
        int32_t step = d ? (d->max - d->min) / 128 : 1;
        if (step < 1)
            step = 1;
        v += delta * step;
    }
    ui_param_v[p] = v;
    ui_clamp_param(p);
}

/* the param of the current page's Nth param-bearing widget (UI_BIND_PAGE_SLOT) */
static uint16_t ui_widget_param(const ui_widget *w); /* defined below */

/* the widget types a page-slot encoder can edit (the param-bearing widgets + the
 * name row, which opens the name editor instead of stepping a value) */
static int ui_is_param_slot(uint8_t type)
{
    return type == UI_VALUE || type == UI_BAR || type == UI_PARAM_ROW ||
           type == UI_PARAM_COLUMN || type == UI_OP_ROW || type == UI_PART_ROW ||
           type == UI_NAME;
}

/* the param id of the current page's Nth param-bearing widget (UI_BIND_PAGE_SLOT);
 * a name widget returns UI_NO_PARAM (it is not a numeric param). */
static uint16_t ui_slot_param(uint8_t slot)
{
    const ui_page *p = ui_cur_page();
    uint32_t i, n = 0;
    for (i = 0; i < p->n; i++) {
        if (ui_is_param_slot(p->w[i].type)) {
            if (n == slot)
                return p->w[i].type == UI_NAME ? UI_NO_PARAM : ui_widget_param(&p->w[i]);
            n++;
        }
    }
    return UI_NO_PARAM;
}

/* the name index (0/1) of the current page's Nth slot when it is a name widget,
 * else 0xFF. */
static uint8_t ui_slot_name(uint8_t slot)
{
    const ui_page *p = ui_cur_page();
    uint32_t i, n = 0;
    for (i = 0; i < p->n; i++) {
        if (ui_is_param_slot(p->w[i].type)) {
            if (n == slot)
                return p->w[i].type == UI_NAME ? (uint8_t)p->w[i].param : 0xFFu;
            n++;
        }
    }
    return 0xFFu;
}

static void ui_do_action(uint8_t action, uint8_t arg)
{
    switch (action) {
    case UI_ACT_NOTE_ON: break;                  /* handled by ui_handle (needs value) */
    case UI_ACT_NOTE_OFF: break;
    case UI_ACT_SET_STEP: ui_act_set_step(arg); break;
    case UI_ACT_PUSH: ui_push(arg); break;
    case UI_ACT_POP: ui_pop(); break;
    case UI_ACT_SWITCH: ui_switch(arg); break;     /* replace the current mode (siblings) */
    case UI_ACT_POP_HOME: ui_pop_home(); break;
    case UI_ACT_NEXT_PAGE:
        if (ui_ctx()->n_pages > 1u)
            ui_pagei[ui_sp] = (uint8_t)((ui_pagei[ui_sp] + 1u) % ui_ctx()->n_pages);
        ui_reset_page();
        break;
    case UI_ACT_PREV_PAGE:
        if (ui_ctx()->n_pages > 1u)
            ui_pagei[ui_sp] = ui_pagei[ui_sp]
                ? (uint8_t)(ui_pagei[ui_sp] - 1u)
                : (uint8_t)(ui_ctx()->n_pages - 1u);
        ui_reset_page();
        break;
    case UI_ACT_SET_PAGE:
        if (arg < ui_ctx()->n_pages) { ui_pagei[ui_sp] = arg; ui_reset_page(); }
        break;
    case UI_ACT_SAVE: ui_act_save(); break;
    case UI_ACT_PANIC: ui_act_panic(); break;
    case UI_ACT_PLAY: ui_act_play(); break;
    case UI_ACT_STOP: ui_act_stop(); break;
    case UI_ACT_TOGGLE:
        if (arg < ui_t->n_params)
            ui_param_v[arg] = ui_param_v[arg] ? 0 : 1;
        break;
    case UI_ACT_OP_NEXT:
        if (ui_t->n_op > 1u)
            ui_selected_op = (uint8_t)((ui_selected_op + 1u) % ui_t->n_op);
        break;
    case UI_ACT_OP_PREV:
        if (ui_t->n_op > 1u)
            ui_selected_op = ui_selected_op ? (uint8_t)(ui_selected_op - 1u)
                                            : (uint8_t)(ui_t->n_op - 1u);
        break;
    case UI_ACT_OP_MUTE: {
        /* mute the *selected* operator (the SEL + key chord; arg is ignored) */
        if (ui_t->mute && ui_selected_op < 4u) {
            uint16_t p = ui_mute_param(ui_selected_op);
            if (p < ui_t->n_params)
                ui_param_v[p] = ui_param_v[p] ? 0 : 1;
        }
        break;
    }
    case UI_ACT_OP_MUTE_N: {
        /* mute operator `arg` (ARP/SEQ/PLAY/REC -> 0..3) */
        if (ui_t->mute && arg < ui_t->n_op && arg < 4u) {
            uint16_t p = ui_mute_param(arg);
            if (p < ui_t->n_params)
                ui_param_v[p] = ui_param_v[p] ? 0 : 1;
        }
        break;
    }
    case UI_ACT_PART_NEXT:
        if (ui_t->n_part > 1u)
            ui_selected_part = (uint8_t)((ui_selected_part + 1u) % ui_t->n_part);
        break;
    case UI_ACT_PART_MUTE:
        if (arg < ui_t->n_part)
            ui_part_mute[arg] = ui_part_mute[arg] ? 0u : 1u;
        break;
    case UI_ACT_INIT_PATCH: ui_act_init_patch(); break;
    case UI_ACT_INIT_PART: ui_act_init_part(); break;
    default: break;                              /* BANK_*, LOAD, LATCH: no-op for now */
    }
}

/* a resolved input event: write a param or run an action (KEY -> note_on/off) */
void ui_handle(uint16_t source, int32_t value)
{
    const ui_binding *b = ui_resolve(source);
    if (!b)
        return;
    if (b->kind == UI_BIND_PARAM) {
        if (b->target < ui_t->n_params) {
            if (b->behavior == UI_REL)
                ui_step_param(b->target, value);
            else {
                ui_param_v[b->target] = value;
                ui_clamp_param(b->target);
            }
        }
    } else if (b->kind == UI_BIND_PAGE_SLOT) {
        uint8_t nm = ui_slot_name(b->arg);
        if (nm != 0xFFu) {
            ui_act_name(nm);                        /* a name row: open its editor */
        } else {
            uint16_t p = ui_slot_param(b->arg);
            if (p < ui_t->n_params) {
                if (b->behavior == UI_REL)
                    ui_step_param(p, value);
                else {
                    ui_param_v[p] = value;
                    ui_clamp_param(p);
                }
            }
        }
    } else if (b->action == UI_ACT_NOTE_ON && value >= 0)
        ui_act_note_on((uint8_t)value, 100u);
    else if (b->action == UI_ACT_NOTE_OFF && value >= 0)
        ui_act_note_off((uint8_t)value);
    else if (b->action == UI_ACT_SET_STEP && value >= 0)
        ui_act_set_step((uint8_t)value);
    else if (b->action == UI_ACT_PAGE) {
        if (ui_ctx()->n_pages > 1u) {
            ui_pagei[ui_sp] = (uint8_t)((ui_pagei[ui_sp] + (value >= 0 ? 1 : -1) + ui_ctx()->n_pages)
                                        % ui_ctx()->n_pages);
            ui_reset_page();
        }
    } else
        ui_do_action(b->action, b->arg);
}

/* ---- the widget renderers (each draws its own region into the canvas, then blits) ---- */

static void ui_region(const ui_widget *w, uint32_t *x, uint32_t *y, uint32_t *wd, uint32_t *ht)
{
    *x = (uint32_t)w->col * UI_COL_W;
    *y = (uint32_t)w->row * UI_ROW_H;
    *wd = *x ? UI_COL_W : 240u;
    *ht = (uint32_t)(w->span ? w->span : 1u) * UI_ROW_H;
}

static void ui_draw_label(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    const felucca_font_t *f = w->span >= 2u ? &FONT_L : &FONT_S;
    ui_region(w, &x, &y, &wd, &ht);
    draw_text_box(x, y, wd, f, w->text, C_GRAY, 0);   /* labels + page titles: the green base text */
}

/* the param id a widget reads: UI_OP_ROW/UI_ENVELOPE resolve through the selected
 * operator *and* the active part; UI_PART_ROW resolves through the active part. */
static uint16_t ui_widget_param(const ui_widget *w)
{
    if (w->type == UI_PART_ROW && ui_t->part_param && w->param < ui_t->n_part_param)
        return ui_t->part_param[(uint32_t)ui_selected_part * ui_t->n_part_param + w->param];
    if ((w->type == UI_OP_ROW || w->type == UI_ENVELOPE) && ui_t->op_param
        && w->param < ui_t->n_op_param)
        return ui_t->op_param[(uint32_t)ui_selected_part * ui_t->n_op * ui_t->n_op_param
                              + (uint32_t)ui_selected_op * ui_t->n_op_param + w->param];
    return w->param;
}

/* a fixed-point decimal: `scaled` is value * 10^dec, printed as "N.NN…" with the
 * fraction zero-padded to `dec` digits (e.g. scaled=125, dec=2 -> "1.25"). Signed. */
static void ui_itoa_dec(int32_t scaled, uint8_t dec, char *out)
{
    int neg = scaled < 0;
    uint32_t u = neg ? (uint32_t)(-(int64_t)scaled) : (uint32_t)scaled;
    uint32_t div = 1, i, whole, frac, scale, len;
    for (i = 0; i < dec; i++)
        div *= 10u;
    whole = u / div;
    frac = u % div;
    out[0] = 0;
    if (neg)
        ui_strcat(out, "-");
    ui_itoa((int32_t)whole, out + ui_strlen(out));
    ui_strcat(out, ".");
    len = ui_strlen(out);
    scale = div;
    for (i = 0; i < dec; i++) {
        scale /= 10u;
        out[len++] = (char)('0' + (frac / scale) % 10u);
    }
    out[len] = 0;
}

/* format a param's value into `out` per its display scale (`unit` is used only for
 * the raw form). The app's status readouts and the host test use this too. */
void ui_param_fmt(uint16_t p, const char *unit, char *out, uint32_t n)
{
    int32_t v = p < ui_t->n_params ? ui_param_v[p] : 0;
    const ui_param_disp *d = (ui_t->disp && p < ui_t->n_params) ? &ui_t->disp[p] : 0;
    out[0] = 0;
    if (!d || d->kind == UI_DISP_RAW) {
        ui_itoa(v, out);
        if (unit) {
            ui_strcat(out, " ");
            ui_strcat(out, unit);
        }
        return;
    }
    switch (d->kind) {
    case UI_DISP_RATIO:                            /* Q16 -> "N.NN" (65536 = 1.00) */
        ui_itoa_dec((int32_t)(((int64_t)v * 100) >> 16), 2, out);
        break;
    case UI_DISP_PCT:
    case UI_DISP_PCT_INV: {
        int32_t rng = d->max - d->min;
        int32_t pct = rng ? (int32_t)((int64_t)(v - d->min) * 100 / rng) : 0;
        if (d->kind == UI_DISP_PCT_INV)
            pct = 100 - pct;
        if (pct < 0) pct = 0; else if (pct > 100) pct = 100;
        ui_itoa(pct, out);
        ui_strcat(out, "%");
        break;
    }
    case UI_DISP_ONOFF:
        ui_strcat(out, v > 0 ? "on" : "off");
        break;
    case UI_DISP_ONOFF_INV:
        ui_strcat(out, v > 0 ? "off" : "on");
        break;
    case UI_DISP_OFF_PCT: {
        if (v <= 0) {
            ui_strcat(out, "off");
        } else {
            int32_t pct = d->max ? (int32_t)((int64_t)v * 100 / d->max) : 0;
            if (pct < 0) pct = 0; else if (pct > 100) pct = 100;
            ui_itoa(pct, out);
            ui_strcat(out, "%");
        }
        break;
    }
    case UI_DISP_HZ:                               /* a Q32 rate -> Hz, one decimal */
        ui_itoa_dec((int32_t)(((int64_t)v * 441000) >> 32), 1, out);
        ui_strcat(out, "Hz");
        break;
    case UI_DISP_SEMI:                             /* bipolar Q15 -> signed semitones */
        ui_itoa_dec((int32_t)(((int64_t)v * 1200) / 32768), 2, out);
        ui_strcat(out, "st");
        break;
    case UI_DISP_CENT: {                           /* int cents -> "+/-Nc" */
        if (v > 0)
            ui_strcat(out, "+");
        ui_itoa(v, out);
        ui_strcat(out, "c");
        break;
    }
    case UI_DISP_WAVE: {                           /* a 0..11 waveform -> its name */
        static const char *const names[12] = {
            "sine", "tri", "half sine", "half tri", "2x sine", "2x tri",
            "2x half sine", "2x half tri", "rect sine", "pulse", "square", "saw"};
        uint32_t i = v >= 0 && v < 12 ? (uint32_t)v : 0u;
        ui_strcat(out, names[i]);
        break;
    }
    case UI_DISP_FILTER: {                         /* a 0..2 svf type -> its name */
        static const char *const names[3] = {"lpf", "bpf", "hpf"};
        uint32_t i = v >= 0 && v < 3 ? (uint32_t)v : 0u;
        ui_strcat(out, names[i]);
        break;
    }
    case UI_DISP_FOLD:                             /* a wavefolder type -> its name */
        ui_strcat(out, "sine");
        break;
    case UI_DISP_MODE: {                           /* a 0..2 voice mode -> its name */
        static const char *const names[3] = {"poly", "mono", "unison"};
        uint32_t i = v >= 0 && v < 3 ? (uint32_t)v : 0u;
        ui_strcat(out, names[i]);
        break;
    }
    case UI_DISP_PRIORITY: {                       /* a 0..2 note priority -> its name */
        static const char *const names[3] = {"last", "highest", "lowest"};
        uint32_t i = v >= 0 && v < 3 ? (uint32_t)v : 0u;
        ui_strcat(out, names[i]);
        break;
    }
    case UI_DISP_NOTE: {                           /* a 0..127 MIDI note -> "N C#4" */
        static const char *const names[12] = {
            "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
        int32_t n = v < 0 ? 0 : v > 127 ? 127 : v;
        char t[12];
        ui_itoa(n, out);                           /* the MIDI note number */
        ui_strcat(out, " ");
        ui_strcat(out, names[n % 12]);             /* the note name */
        ui_itoa((int32_t)(n / 12 - 1), t);         /* the octave (-1..9) */
        ui_strcat(out, t);
        break;
    }
    case UI_DISP_PORTA: {                          /* a Q16 glide rate -> "off"/"N ms" */
        if (v <= 0) {
            ui_strcat(out, "off");
        } else {
            /* one-octave glide time: 32768/rate blocks x 32 frames / 44.1 kHz */
            int32_t ms = 23777 / v;
            if (ms < 1)
                ms = 1;
            ui_itoa(ms, out);
            ui_strcat(out, "ms");
        }
        break;
    }
    default:
        ui_itoa(v, out);
        break;
    }
    (void)n;
}

/* format a param's value + unit into `out` (the right-hand column) */
static void ui_value_str(const ui_widget *w, char *out, uint32_t n)
{
    ui_param_fmt(ui_widget_param(w), w->unit, out, n);
}

/* format a param row's label + value + unit into `out` (for the bar's label) */
static void ui_format(const ui_widget *w, char *out, uint32_t n)
{
    uint32_t used;
    out[0] = 0;
    if (w->text) {
        ui_strcat(out, w->text);
        ui_strcat(out, " ");                      /* a gap between the name and its value */
    }
    used = ui_strlen(out);
    ui_value_str(w, out + used, n > used ? n - used : 1);
}

/* a param row: the label in white, the value + unit right-aligned in the value
 * colour — the value is what changes, so it is the bright/high-contrast element
 * and the label is the quiet white reference (the C_TEXT/C_HI roles). */
static void ui_draw_value(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    char val[24];
    ui_region(w, &x, &y, &wd, &ht);
    ui_value_str(w, val, sizeof val);
    cv_begin(wd, ht, C_BLACK);
    {
        int32_t vx = (int32_t)wd - text_w(&FONT_S, val);
        if (vx < 0)
            vx = 0;
        if (w->text)
            cv_text(0, 0, &FONT_S, w->text, C_TEXT);   /* the name: white */
        cv_text(vx, 0, &FONT_S, val, C_HI);            /* the value: bright */
    }
    cv_blit(x, y);
}

/* a name row: the label (text, dim) + the name string (bright). `w->param` is the
 * name index (0 = part, 1 = patch). Twisting its page slot opens the editor. */
static void ui_draw_name_row(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    const char *name = ui_name_get(w->param < 3u ? w->param : 0u);
    ui_region(w, &x, &y, &wd, &ht);
    cv_begin(wd, ht, C_BLACK);
    {
        int32_t vx = (int32_t)wd - text_w(&FONT_S, name);
        if (vx < 0)
            vx = 0;
        if (w->text)
            cv_text(0, 0, &FONT_S, w->text, C_TEXT);  /* the label: white */
        cv_text(vx, 0, &FONT_S, name, C_HI);          /* the name: bright */
    }
    cv_blit(x, y);
}

static void ui_draw_bar(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    int32_t v = ui_widget_param(w) < ui_t->n_params ? ui_param_v[ui_widget_param(w)] : 0;
    int32_t frac;
    uint32_t bw;
    char s[32];
    ui_region(w, &x, &y, &wd, &ht);
    ui_format(w, s, sizeof s);
    cv_begin(wd, ht, C_BLACK);
    cv_text(0, 0, &FONT_S, s, C_GRAY);
    frac = v > 32767 ? 32767 : (v < 0 ? 0 : v);
    bw = (uint32_t)frac * (wd - 40u) / 32767u;
    if (bw)
        cv_rect(40, 4, (int32_t)bw, (int32_t)ht - 8, C_HI);
    cv_blit(x, y);
}

static void ui_draw_list(const ui_widget *w)
{
    uint32_t x, y, wd, ht, i;
    uint32_t rows = w->span ? w->span : 1u;
    ui_region(w, &x, &y, &wd, &ht);
    cv_begin(wd, ht, C_BLACK);
    for (i = 0; i < rows && i < w->n_items; i++)
        cv_text(0, (int32_t)(i * UI_ROW_H), &FONT_S, w->items[i],
                i == (uint32_t)ui_cursor ? C_WHITE : C_GRAY);
    cv_blit(x, y);
}

static void ui_draw_grid(const ui_widget *w)
{
    uint32_t x, y, wd, ht, i;
    uint32_t rows = w->span ? w->span : 1u;
    ui_region(w, &x, &y, &wd, &ht);
    cv_begin(wd, ht, C_BLACK);
    for (i = 0; i < rows * 4u && i < w->n_items; i++) {
        uint32_t gx = (i % 4u) * (wd / 4u), gy = (i / 4u) * (ht / rows);
        cv_rect((int32_t)gx, (int32_t)gy, (int32_t)(wd / 4u) - 2, (int32_t)(ht / rows) - 2,
                i == (uint32_t)ui_cursor ? C_WHITE : C_DIM);
    }
    cv_blit(x, y);
}

/* the DX rate/level envelope as straight line segments: the selected operator's 7
 * envelope params (r1..r4, l1..l3) from the `env` group. Stage length = log2 of
 * the one-pole time constant (so the exponential rate curve is shown on a log
 * scale — a linear length would make every slow rate identical); the level height
 * = fm1_level_gain[level] (0.25 dB/step: 99 = max, 0 = silence). No cursor. */
static void ui_draw_envelope(const ui_widget *w)
{
    uint32_t x, y, wd, ht, i, cx;
    uint32_t len[5], total = 0, p0;
    int32_t lvl[5], px[6], py[6];

    ui_region(w, &x, &y, &wd, &ht);
    if (!ui_t->env || ui_selected_op >= ui_t->n_op)
        return;
    p0 = ((uint32_t)ui_selected_part * ui_t->n_op + (uint32_t)ui_selected_op) * 7u;
    for (i = 0; i < 3; i++) {                       /* r1..r3: attack, decay1, decay2 */
        uint16_t p = ui_t->env[p0 + i];
        int32_t r = p < ui_t->n_params ? ui_param_v[p] : 0;
        int32_t c = fm1_rate_coeff[r < 0 ? 0 : (r > 99 ? 99 : r)];
        uint32_t lg = 0;                            /* floor(log2(coeff)) */
        while (c > 1) { c >>= 1; lg++; }
        len[i] = lg < 16u ? 16u - lg : 1u;          /* log2(65536/coeff), min 1 */
        total += len[i];
    }
    len[3] = 8u;                                    /* sustain: a short flat hold */
    total += len[3];
    {
        uint16_t p = ui_t->env[p0 + 3];             /* r4: the release rate */
        int32_t r = p < ui_t->n_params ? ui_param_v[p] : 0;
        int32_t c = fm1_rate_coeff[r < 0 ? 0 : (r > 99 ? 99 : r)];
        uint32_t lg = 0;
        while (c > 1) { c >>= 1; lg++; }
        len[4] = lg < 16u ? 16u - lg : 1u;
        total += len[4];
    }
    if (!total)
        total = 1u;
    for (i = 0; i < 3; i++) {
        uint16_t p = ui_t->env[p0 + 4u + i];
        int32_t l = p < ui_t->n_params ? ui_param_v[p] : 0;
        lvl[i] = fm1_level_gain[l < 0 ? 0 : (l > 99 ? 99 : l)];
    }
    lvl[3] = lvl[2];
    lvl[4] = 0;
    px[0] = 0;
    py[0] = (int32_t)ht;
    cx = 0;
    for (i = 0; i < 5; i++) {
        cx += (len[i] * wd) / total;
        px[i + 1] = (int32_t)cx;
        py[i + 1] = (int32_t)ht - (lvl[i] * (int32_t)ht) / 32768;
    }
    cv_begin(wd, ht, C_BLACK);
    for (i = 0; i < 5; i++)
        cv_line(px[i], py[i], px[i + 1], py[i + 1], C_AMB);   /* the envelope curve: the graph highlight */
    cv_blit(x, y);
}

/* the scope channel a widget selects: `w->param` = the op index (0..3 -> "op N of
 * the active part", resolved to 1 + N*n_part + part), 0x40 -> the *active*
 * operator of the active part, or 0x80|part -> "part N mix"
 * (resolved to 1 + n_op*n_part + part). */
static uint32_t ui_scope_channel(const ui_widget *w)
{
    uint32_t p = (uint32_t)w->param;
    if (p == 0x40u)
        return 1u + (uint32_t)ui_selected_op * (uint32_t)ui_t->n_part
               + (uint32_t)ui_selected_part;
    if (p & 0x80u)
        return 1u + (uint32_t)ui_t->n_op * (uint32_t)ui_t->n_part + (p & 0x7Fu);
    return 1u + p * (uint32_t)ui_t->n_part + (uint32_t)ui_selected_part;
}

/* the oscilloscope: the selected channel's snapshot, downsampled to the widget
 * width, drawn as a line with a mid-line. Time-varying — redraws whenever the
 * snapshot advances (scope_seq), which the ISR bumps every block. The tap is
 * ×4 (the operator's −12 dB total-level headroom) so a full-level operator fills
 * the height. */
/* a scope sample -> the vertical pixel: a quarter-sine soft-clip (the existing
 * fm1_sin_q15 table). `shift` sets the knee — a sample of 2^(shift+8) fills the
 * widget and anything louder saturates at the edge, so the trace clips instead of
 * overshooting. The expansive low end keeps normal levels readable (a level-75
 * operator spans most of the widget). */
static int32_t ui_scope_y(int32_t s, int32_t ht, uint32_t shift)
{
    uint32_t a = s < 0 ? (uint32_t)(-(int64_t)s) : (uint32_t)s;
    uint32_t idx = a >> shift;
    int32_t y;
    if (idx >= 256u)
        idx = 255u;
    y = (int32_t)fm1_sin_q15[idx];
    if (s < 0)
        y = -y;
    return (int32_t)ht / 2 - (y * (int32_t)ht) / 65536;
}

static void ui_draw_scope(const ui_widget *w)
{
    uint32_t ch = ui_scope_channel(w), x, y, wd, ht, i;
    /* the part mix (route.car) is ~4x hotter than a single operator: a 2x knee
     * (shift 6 vs 5) keeps it at half the on-screen height. */
    uint32_t shift = (w->param & 0x80u) ? 6u : 5u;
    int32_t mid, lx, ly;
    ui_region(w, &x, &y, &wd, &ht);
    if (wd < 2u)
        return;
    cv_begin(wd, ht, C_BLACK);
    mid = (int32_t)ht / 2;
    cv_line(0, mid, (int32_t)wd - 1, mid, C_DIM);
    lx = 0;
    ly = ui_scope_y(scope_at_ch(ch, 0u), (int32_t)ht, shift);
    for (i = 1; i < wd; i++) {
        int32_t s = scope_at_ch(ch, i * SCOPE_N / wd);
        int32_t px = (int32_t)i, py = ui_scope_y(s, (int32_t)ht, shift);
        cv_line(lx, ly, px, py, C_AMB);              /* the waveform: the graph highlight */
        lx = px;
        ly = py;
    }
    cv_blit(x, y);
}

/* the spectrogram: SCOPE_BINS linearly-spaced Goertzel bars (power-normalized),
 * log-free and integer — the ear hears power, and the harmonic series is visible. */
static void ui_draw_spectro(const ui_widget *w)
{
    uint32_t x, y, wd, ht, i;
    uint16_t mag[SCOPE_BINS];
    uint32_t bw;
    ui_region(w, &x, &y, &wd, &ht);
    scope_spectrum_ch(ui_scope_channel(w), mag, SCOPE_BINS);
    bw = wd / SCOPE_BINS;
    if (bw < 1u)
        bw = 1u;
    cv_begin(wd, ht, C_BLACK);
    for (i = 0; i < SCOPE_BINS; i++) {
        int32_t bh = (int32_t)((mag[i] * (int32_t)ht) / 32767u);
        cv_rect((int32_t)(i * bw), (int32_t)ht - bh, (int32_t)bw, bh, C_AMB);   /* the bars: the graph highlight */
    }
    cv_blit(x, y);
}

/* the status readout: ALG <n>  OP <n>/<m>  [MUTE] (the widget's `param` is the
 * algorithm param; the operator + mute come from ui_selected_op + the mute table). */
static void ui_draw_status(const ui_widget *w)
{
    char s[32], t[12];
    uint32_t x, y, wd, ht;
    int32_t alg = w->param < ui_t->n_params ? ui_param_v[w->param] : 0;
    int muted = 0;
    ui_region(w, &x, &y, &wd, &ht);
    if (ui_t->mute && ui_selected_op < 4u) {
        uint16_t p = ui_mute_param(ui_selected_op);
        if (p < ui_t->n_params)
            muted = ui_param_v[p] != 0;
    }
    ui_strcpy(s, "ALG ");
    ui_itoa(alg, t);
    ui_strcat(s, t);
    ui_strcat(s, "  OP ");
    t[0] = (char)('1' + ui_selected_op);
    t[1] = '/';
    t[2] = (char)('0' + ui_t->n_op);
    t[3] = 0;
    ui_strcat(s, t);
    /* the mute flag is drawn in the warning colour (its text also says MUTE, so it
     * is not conveyed by colour alone). Clear the full 2-line region, not just the
     * font height, so a previous page's header is fully erased. */
    cv_begin(wd, ht, C_BLACK);
    {
        int32_t end = cv_text(0, 0, &FONT_S, s, C_GRAY);
        if (muted)
            cv_text(end, 0, &FONT_S, "  MUTE", C_WARN);
    }
    cv_blit(x, y);
}

/* the 8 standard 4-op FM algorithms (ymfm s_algorithm_ops, with alg 3 replaced —
 * see umetate/_tables.py `_ROUTING`): ALGO_MOD[alg][i] is the bitmask of operators
 * that phase-modulate operator i; ALGO_CAR[alg] is the carrier bitmask. */
static const uint8_t ALGO_MOD[8][4] = {
    {0, 1, 2, 4},   /* 0: 1->2->3->4 */
    {0, 0, 3, 4},   /* 1: (1+2)->3->4 */
    {0, 0, 2, 5},   /* 2: 1->4, 2->3->4 */
    {0, 1, 1, 6},   /* 3: 1->2, 1->3, 2+3->4 */
    {0, 1, 0, 4},   /* 4: (1->2)+(3->4) */
    {0, 1, 1, 1},   /* 5: 1->2/3/4 */
    {0, 1, 0, 0},   /* 6: (1->2)+3+4 */
    {0, 0, 0, 0},   /* 7: all four carriers */
};
static const uint8_t ALGO_CAR[8] = {8, 8, 8, 8, 10, 14, 14, 15};
/* the block centre per operator per algorithm (pixels; the widget is 240 wide).
 * `int16_t`: several x-centres exceed 127, so `int8_t` would wrap them negative
 * and draw the blocks off-screen to the left. */
static const int16_t ALGO_X[8][4] = {
    {108, 108, 108, 108},  /* 0: vertical chain */
    {44, 172, 108, 108},   /* 1: 1,2 on top -> 3 -> 4 */
    {44, 172, 108, 108},   /* 2: 2 on top; 1,3 middle -> 4 */
    {108, 44, 172, 108},   /* 3: 1 on top -> 2,3 -> 4 */
    {44, 44, 172, 172},    /* 4: 1->2 and 3->4 */
    {108, 44, 108, 172},   /* 5: 1 on top -> 2,3,4 */
    {44, 44, 108, 172},    /* 6: 1->2, +3, +4 */
    {210, 150, 90, 30},    /* 7: 4,3,2,1 in a row */
};
static const int16_t ALGO_Y[8][4] = {
    {10, 46, 82, 118},     /* 0 */
    {10, 10, 46, 82},      /* 1 */
    {46, 10, 46, 82},      /* 2 */
    {10, 46, 46, 82},      /* 3 */
    {10, 46, 10, 46},      /* 4 */
    {10, 46, 46, 46},      /* 5 */
    {10, 46, 46, 46},      /* 6 */
    {10, 10, 10, 10},      /* 7 */
};

/* draw the algorithm graph (modulation arrows + carrier outputs in purple,
 * operator blocks in pink/white) into the current canvas, at origin (ox, oy). */
static void algo_graph(int32_t alg, int32_t ox, int32_t oy)
{
    uint32_t i, j;
    char s[2];
    if (alg < 0)
        alg = 0;
    else if (alg > 7)
        alg = 7;
    for (i = 0; i < 4u; i++)                           /* modulation arrows */
        for (j = 0; j < 4u; j++)
            if (ALGO_MOD[alg][i] & (1u << j))
                cv_line(ox + ALGO_X[alg][j], oy + ALGO_Y[alg][j],
                        ox + ALGO_X[alg][i], oy + ALGO_Y[alg][i], C_AMB);
    for (i = 0; i < 4u; i++)                           /* carrier -> output */
        if ((ALGO_CAR[alg] >> i) & 1u) {
            int32_t cx = ox + ALGO_X[alg][i], cy = oy + ALGO_Y[alg][i] + 7;
            cv_line(cx, cy, cx, cy + 8, C_AMB);        /* a short shaft down */
            cv_line(cx - 3, cy + 5, cx, cy + 8, C_AMB);  /* arrowhead */
            cv_line(cx + 3, cy + 5, cx, cy + 8, C_AMB);
        }
    for (i = 0; i < 4u; i++) {                         /* the operator blocks */
        int32_t bx = ox + ALGO_X[alg][i] - 20, by = oy + ALGO_Y[alg][i] - 7;
        cv_rect(bx, by, 40, 14, (ALGO_CAR[alg] >> i) & 1u ? C_HI : C_TEXT);
        s[0] = (char)('1' + i);
        s[1] = 0;
        cv_text(bx + 15, by, &FONT_S, s, C_BLACK);
    }
}

/* the algorithm graph widget (the widget's `param` is the algorithm param). */
static void ui_draw_algo(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    ui_region(w, &x, &y, &wd, &ht);
    cv_begin(wd, ht, C_BLACK);
    algo_graph(w->param < ui_t->n_params ? ui_param_v[w->param] : 0, 0, 0);
    cv_blit(x, y);
}

/* build the subheader prefix for `mode` into `s` (empty = no prefix): 0 = "OP N",
 * 1 = "PART N", 2 = "OP", 3 = "PART", 4 = plain, 5 = "PART n OP". N is the active
 * operator/part — dynamic, so the header title re-renders on a part/op switch. */
static void ui_prefix_str(uint8_t mode, char *s)
{
    char t[4];
    s[0] = 0;
    switch (mode) {
    case 1u:                                       /* PART N */
        ui_strcpy(s, "PART ");
        t[0] = (char)('1' + ui_selected_part);
        t[1] = 0;
        ui_strcat(s, t);
        break;
    case 2u: ui_strcpy(s, "OP "); break;           /* OP (no number) */
    case 3u: ui_strcpy(s, "PART "); break;         /* PART (no number) */
    case 5u:                                       /* PART n OP */
        ui_strcpy(s, "PART ");
        t[0] = (char)('1' + ui_selected_part);
        t[1] = 0;
        ui_strcat(s, t);
        ui_strcat(s, " OP");
        break;
    case 0u:                                       /* OP N */
        ui_strcpy(s, "OP ");
        t[0] = (char)('1' + ui_selected_op);
        t[1] = 0;
        ui_strcat(s, t);
        break;
    default: break;                                /* 4 = plain (no prefix) */
    }
}

/* the page's subheader (param = the prefix mode); `text` is the param-group name. */
static void ui_draw_subheader(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    char s[24];
    ui_region(w, &x, &y, &wd, &ht);
    ui_prefix_str((uint8_t)w->param, s);
    if (w->text) {
        if (s[0])
            ui_strcat(s, " ");
        ui_strcat(s, w->text);
    }
    cv_begin(wd, ht, C_BLACK);
    cv_text(0, 0, &FONT_S, s, C_GRAY);              /* the page title: green base text */
    cv_blit(x, y);
}

/* the always-visible header (rows 0-1, full width): the active part + operator,
 * the algorithm, the menu name, the page N/M, and every part's + operator's
 * mute/active state. Drawn every redraw; its value folds all of those into one
 * word (distinct bit fields, no overlap). */
static int32_t ui_header_value(void)
{
    int32_t v = (int32_t)ui_selected_part | ((int32_t)ui_selected_op << 2)
              | ((int32_t)ui_stack[ui_sp] << 5) | ((int32_t)ui_pagei[ui_sp] << 8);
    uint32_t i;
    if (ui_t->alg < ui_t->n_params)
        v |= (ui_param_v[ui_t->alg] & 0x3F) << 11;
    for (i = 0; i < 4u && i < ui_t->n_op; i++) {
        uint16_t p = ui_t->mute ? ui_mute_param(i) : UI_NO_PARAM;
        if (p < ui_t->n_params && ui_param_v[p])
            v |= 1 << (int32_t)(17u + i);
    }
    for (i = 0; i < 4u && i < ui_t->n_part; i++)
        if (ui_part_mute[i])
            v |= 1 << (int32_t)(21u + i);
    return v;
}

/* one header token at (x, y): `current` = the selected part/operator (light blue),
 * `muted` = red (colour-alone), else the white base text. Returns the next x. */
static int32_t ui_htok(int32_t x, int32_t y, const char *s, int cur, int muted)
{
    uint16_t c = cur ? C_SEL : (muted ? C_DIM : C_TEXT);
    return cv_text(x, y, &FONT_S, s, c);
}

static void ui_draw_header(void)
{
    char s[40], t[12], tok[8];
    uint32_t i;
    int32_t x, alg = ui_t->alg < ui_t->n_params ? ui_param_v[ui_t->alg] : 0;

    cv_begin(240u, 2u * UI_ROW_H, C_BLACK);

    /* row 0 (one line): P1 P2 · op 1 2 3 4 · ALG<alg> · <menu> <page>/<n>. Parts +
     * operators are the white base text (selected = light blue, muted = red); ALG is
     * pink; the menu + page is purple. */
    x = 0;
    for (i = 0; i < ui_t->n_part; i++) {
        tok[0] = 'P';
        tok[1] = (char)('1' + i);
        tok[2] = 0;
        x = ui_htok(x, 0, tok, i == ui_selected_part, ui_part_mute[i]);
        x = ui_htok(x, 0, " ", 0, 0);
    }
    if (ui_t->n_op) {
        x = ui_htok(x, 0, "op ", 0, 0);
        for (i = 0; i < 4u && i < ui_t->n_op; i++) {
            uint16_t p = ui_t->mute ? ui_mute_param(i) : UI_NO_PARAM;
            int muted = p < ui_t->n_params ? ui_param_v[p] != 0 : 0;
            tok[0] = (char)('1' + i);
            tok[1] = 0;
            x = ui_htok(x, 0, tok, i == ui_selected_op, muted);
            x = ui_htok(x, 0, " ", 0, 0);
        }
    }
    if (ui_t->alg < ui_t->n_params) {
        ui_strcpy(s, "ALG");
        ui_itoa(alg, t);
        ui_strcat(s, t);
        ui_strcat(s, " ");
        x = cv_text(x, 0, &FONT_S, s, C_HI);      /* the algorithm: pink */
    }
    s[0] = 0;
    if (ui_ctx()->name)
        ui_strcpy(s, ui_ctx()->name);
    ui_strcat(s, " ");
    ui_itoa((int32_t)ui_pagei[ui_sp] + 1, t);
    ui_strcat(s, t);
    ui_strcat(s, "/");
    ui_itoa((int32_t)ui_ctx()->n_pages, t);
    ui_strcat(s, t);
    cv_text(x, 0, &FONT_S, s, C_AMB);            /* the menu + page: purple */

    /* row 1: the page description (green), with the subheader prefix (PART n OP /
       OP n) when the page declared one */
    {
        char d[40];
        ui_prefix_str(ui_cur_page()->mode, d);
        if (ui_cur_page()->title && ui_cur_page()->title[0]) {
            if (d[0])
                ui_strcat(d, " ");
            ui_strcat(d, ui_cur_page()->title);
        }
        cv_text(0, UI_ROW_H, &FONT_S, d, C_GRAY);
    }

    cv_blit(0, 0);
}

static void ui_draw_widget(const ui_widget *w)
{
    switch (w->type) {
    case UI_LABEL: ui_draw_label(w); break;
    case UI_VALUE:
    case UI_PARAM_ROW:
    case UI_OP_ROW:
    case UI_PART_ROW: ui_draw_value(w); break;
    case UI_BAR: ui_draw_bar(w); break;
    case UI_PARAM_COLUMN: ui_draw_list(w); break;   /* stacked name/value rows */
    case UI_LIST: ui_draw_list(w); break;
    case UI_GRID: ui_draw_grid(w); break;
    case UI_ENVELOPE: ui_draw_envelope(w); break;
    case UI_SCOPE: ui_draw_scope(w); break;
    case UI_SPECTRO: ui_draw_spectro(w); break;
    case UI_STATUS: ui_draw_status(w); break;
    case UI_SUBHEADER: ui_draw_subheader(w); break;
    case UI_NAME: ui_draw_name_row(w); break;
    case UI_ALGO: ui_draw_algo(w); break;
    case UI_CUSTOM: ui_draw_custom(w); break;
    default: break;
    }
}

/* the value a widget's redraw depends on (for the dirty check) */
static int32_t ui_widget_value(const ui_widget *w, uint32_t slot)
{
    switch (w->type) {
    case UI_LABEL: return 0;                      /* static: drawn once per page */
    case UI_CUSTOM: return ui_custom_v[slot];
    case UI_SCOPE:
    case UI_SPECTRO: return (int32_t)scope_seq();  /* redraw on each new snapshot */
    case UI_SUBHEADER:                               /* redraw on the active op/part change */
        if (w->param == 0u)
            return (int32_t)ui_selected_op;
        if (w->param == 1u)
            return (int32_t)ui_selected_part;
        return 0;                                    /* 2/3/4: no number, static */
    case UI_NAME: {                                 /* redraw when the name changes */
        const char *n = ui_name_get(w->param < 3u ? w->param : 0u);
        int32_t h = 0;
        while (*n)
            h += *n++;
        return h;
    }
    case UI_LIST:
    case UI_GRID: return ui_cursor;
    case UI_ENVELOPE: {                             /* redraw when any of the 7 change */
        int32_t sum = 0;
        uint32_t i, p0 = ((uint32_t)ui_selected_part * ui_t->n_op + (uint32_t)ui_selected_op) * 7u;
        if (ui_t->env && ui_selected_op < ui_t->n_op)
            for (i = 0; i < 7; i++) {
                uint16_t p = ui_t->env[p0 + i];
                if (p < ui_t->n_params) sum += ui_param_v[p];
            }
        return sum;
    }
    case UI_STATUS: {                               /* algorithm + operator + mute */
        int32_t alg = w->param < ui_t->n_params ? ui_param_v[w->param] : 0;
        int32_t m = 0;
        if (ui_t->mute && ui_selected_op < 4u) {
            uint16_t p = ui_mute_param(ui_selected_op);
            if (p < ui_t->n_params) m = ui_param_v[p] != 0;
        }
        return alg * 4 + (int32_t)ui_selected_op * 2 + m;
    }
    case UI_ALGO:                                   /* redraw when the algorithm changes */
        return w->param < ui_t->n_params ? ui_param_v[w->param] : 0;
    default:                                       /* VALUE/BAR/PARAM_ROW/COLUMN/OP_ROW */
        return ui_widget_param(w) < ui_t->n_params ? ui_param_v[ui_widget_param(w)] : 0;
    }
}

void ui_custom_set(uint32_t slot, int32_t value)
{
    if (slot < UI_MAX_WIDGETS)
        ui_custom_v[slot] = value;
}

/* the preset-browser popup: a dark band over the page (rows 4-6) with a title +
 * the selected slot/name. Drawn every redraw while active (its text is transient). */
static void ui_draw_popup(void)
{
    cv_begin(240u, 3u * UI_ROW_H, C_POPUP_BG);
    cv_text(6, UI_ROW_H, &FONT_S, ui_popup_line, C_POPUP_TXT);
    cv_blit(0, 4 * UI_ROW_H);
}

/* the algorithm-graph popup: a tall dark band with "ALG n" + the routing graph. */
static void ui_draw_alg_popup(void)
{
    char s[8];
    cv_begin(240u, 13u * UI_ROW_H, C_POPUP_BG);
    ui_strcpy(s, "ALG ");
    ui_itoa((int32_t)ui_popup_alg_val, s + 4);
    cv_text(6, 4, &FONT_S, s, C_POPUP_TXT);
    algo_graph((int32_t)ui_popup_alg_val, 0, 30);   /* the graph, below the title */
    cv_blit(0, 2 * UI_ROW_H);
}

static void ui_popup_set(const char *title, uint32_t slot, const char *name)
{
    char t[12];
    uint8_t was = ui_popup_on;
    ui_popup_on = 1;
    ui_popup_alg_on = 0;                           /* the text and graph popups are exclusive */
    ui_strcpy(ui_popup_line, title);
    ui_itoa((int32_t)slot, t);
    ui_strcat(ui_popup_line, t);
    ui_strcat(ui_popup_line, "  ");
    if (name && name[0])
        ui_strcat(ui_popup_line, name);
    else
        ui_strcat(ui_popup_line, "(empty)");
    if (!was)
        ui_reset_page();                           /* off -> on: clear + redraw under it */
}

void ui_popup_show(uint32_t slot, const char *name) { ui_popup_set("multi-patch ", slot, name); }
void ui_popup_show_part(uint32_t slot, const char *name) { ui_popup_set("single part ", slot, name); }

void ui_popup_alg(uint32_t alg)               /* the algorithm scroll popup (graph) */
{
    uint8_t was = ui_popup_alg_on;
    ui_popup_on = 0;                            /* the text and graph popups are exclusive */
    ui_popup_alg_on = 1;
    ui_popup_alg_val = (uint8_t)(alg & 7u);
    if (!was)
        ui_reset_page();
}

void ui_popup_hide(void)
{
    if (ui_popup_on || ui_popup_alg_on) {
        ui_popup_on = 0;
        ui_popup_alg_on = 0;
        ui_reset_page();                           /* on -> off: redraw the page beneath */
    }
}

/* ---- the name strings + the name editor ---- */

/* the name charset: uppercase + digits + space + a few symbols (no lowercase, so
 * the name renders in both FONT_S and the uppercase-only FONT_L). */
static const char ui_charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -._";
#define UI_CHARSET_N (sizeof(ui_charset) - 1u)

static uint8_t ui_charset_idx(char c)
{
    uint32_t i;
    for (i = 0; i < UI_CHARSET_N; i++)
        if (ui_charset[i] == c)
            return (uint8_t)i;
    return 0;                                      /* unknown -> 'A' */
}

const char *ui_name_get(uint8_t which)
{
    return ui_name[which < 3u ? which : 0u];
}

void ui_name_set(uint8_t which, const char *name)
{
    uint32_t i;
    if (which >= 3u)
        return;
    for (i = 0; i < UI_NAME_LEN - 1u && name[i]; i++)
        ui_name[which][i] = name[i];
    ui_name[which][i] = 0;
}

uint8_t ui_name_editing(void) { return ui_name_on ? ui_name_which : 0xFFu; }

void ui_name_editor_begin(uint8_t which)
{
    uint32_t i;
    if (which >= 3u)
        return;
    ui_name_which = which;
    ui_name_cursor = 0;
    for (i = 0; i < UI_NAME_LEN; i++)
        ui_name_saved[i] = ui_name[which][i];
    if (!ui_name_on)
        ui_reset_page();
    ui_name_on = 1;
}

void ui_name_editor_commit(void)
{
    if (ui_name_on) {
        ui_name_on = 0;
        ui_reset_page();
    }
}

void ui_name_editor_cancel(void)
{
    if (ui_name_on) {
        ui_name_set(ui_name_which, ui_name_saved); /* restore the pre-edit name */
        ui_name_on = 0;
        ui_reset_page();
    }
}

void ui_name_editor_char(int32_t delta)
{
    char c;
    int32_t idx;
    uint32_t i, len = 0;
    if (!ui_name_on)
        return;
    while (ui_name[ui_name_which][len])
        len++;
    c = ui_name[ui_name_which][ui_name_cursor];
    idx = (int32_t)ui_charset_idx(c) + delta;
    idx %= (int32_t)UI_CHARSET_N;
    if (idx < 0)
        idx += (int32_t)UI_CHARSET_N;
    ui_name[ui_name_which][ui_name_cursor] = ui_charset[idx];
    (void)len;
    (void)i;
}

void ui_name_editor_move(int32_t delta)
{
    if (!ui_name_on)
        return;
    if (delta > 0)
        ui_name_cursor = (uint8_t)((ui_name_cursor + 1u) % (UI_NAME_LEN - 1u));
    else
        ui_name_cursor = (uint8_t)((ui_name_cursor + (UI_NAME_LEN - 1u) - 1u) %
                                   (UI_NAME_LEN - 1u));
}

void ui_name_editor_backspace(void)
{
    uint32_t i;
    char *n;
    if (!ui_name_on)
        return;
    n = ui_name[ui_name_which];
    for (i = ui_name_cursor; i < UI_NAME_LEN - 1u; i++)
        n[i] = n[i + 1u];
    n[UI_NAME_LEN - 1u] = 0;                       /* shift left: delete at the cursor */
}

/* the name editor pop-up: title + the name (cursor char in purple) + the legend. */
static void ui_draw_name_editor(void)
{
    static const char *const titles[3] = {
        "single part 1 name", "single part 2 name", "multi-patch name"};
    char s[UI_NAME_LEN + 8];
    const char *title = titles[ui_name_which < 3u ? ui_name_which : 2u];
    uint32_t i;
    cv_begin(240u, 5u * UI_ROW_H, C_POPUP_BG);
    cv_text(6, 2, &FONT_S, title, C_POPUP_TXT);
    /* the name: FONT_L, 15 fixed columns; the cursor char is the accent colour */
    for (i = 0; i < UI_NAME_LEN - 1u; i++) {
        char c = ui_name[ui_name_which][i];
        s[0] = c ? c : ' ';
        s[1] = 0;
        cv_text(6 + (int32_t)i * 16, UI_ROW_H, &FONT_L, s,
                i == ui_name_cursor ? C_AMB : C_HI);
    }
    cv_text(6, 3 * UI_ROW_H, &FONT_S, "K1=char K2=cursor SEL=del SAVE=ok HOME=cancel", C_POPUP_TXT);
    cv_blit(0, 4 * UI_ROW_H);
}

/* ---- the save chooser (the SAVE dialog: single part / multi-patch + slot) ---- */

/* the slot range per kind: 0 = single part (PRESET_PART_SLOTS), 1 = multi-patch */
static uint16_t ui_save_max(uint8_t kind)
{
    return (uint16_t)(kind == 0u ? PRESET_PART_SLOTS : PRESET_MULTI_SLOTS);
}

uint8_t ui_save_open(void) { return ui_save_on; }

void ui_save_begin(uint8_t kind, uint16_t part_slot, uint16_t multi_slot)
{
    ui_save_which = kind < 2u ? kind : 0u;
    ui_save_slots[0] = part_slot < PRESET_PART_SLOTS ? part_slot : 0u;
    ui_save_slots[1] = multi_slot < PRESET_MULTI_SLOTS ? multi_slot : 0u;
    if (!ui_save_on)
        ui_reset_page();
    ui_save_on = 1;
}

uint8_t ui_save_kind(void) { return ui_save_which; }
uint16_t ui_save_slot(void) { return ui_save_slots[ui_save_which]; }

void ui_save_kind_move(int32_t delta)
{
    (void)delta;
    if (!ui_save_on)
        return;
    ui_save_which = ui_save_which == 0u ? 1u : 0u; /* two rows: toggle */
}

void ui_save_slot_move(int32_t delta)
{
    uint16_t max = ui_save_max(ui_save_which);
    int32_t s;
    if (!ui_save_on)
        return;
    s = (int32_t)ui_save_slots[ui_save_which] + delta;
    s %= (int32_t)max;
    if (s < 0)
        s += (int32_t)max;
    ui_save_slots[ui_save_which] = (uint16_t)s;
}

void ui_save_commit(void)
{
    if (ui_save_on) {
        ui_save_on = 0;
        ui_reset_page();
    }
}

void ui_save_cancel(void)
{
    if (ui_save_on) {
        ui_save_on = 0;
        ui_reset_page();
    }
}

/* the save chooser pop-up: title + two rows (the selected in purple) + the legend. */
static void ui_draw_save(void)
{
    static const char *const ui_save_kind_text[2] = {"single part", "multi-patch"};
    char t[12];
    uint32_t i;
    cv_begin(240u, 5u * UI_ROW_H, C_POPUP_BG);
    cv_text(6, 2, &FONT_S, "SAVE", C_POPUP_TXT);
    for (i = 0; i < 2u; i++) {
        char row[32];
        ui_strcpy(row, i == ui_save_which ? "> " : "  ");
        ui_strcat(row, ui_save_kind_text[i]);
        ui_strcat(row, "  slot ");
        ui_itoa((int32_t)ui_save_slots[i], t);
        ui_strcat(row, t);
        cv_text(6, (int32_t)(i + 1u) * UI_ROW_H, &FONT_S, row,
                i == ui_save_which ? C_AMB : C_HI);
    }
    cv_text(6, 3 * UI_ROW_H, &FONT_S, "K1=kind K2=slot SAVE=save HOME=cancel", C_POPUP_TXT);
    cv_blit(0, 4 * UI_ROW_H);
}

/* ---- the save-mode chooser (step 2 of a multi-patch save) ---- */

uint8_t ui_save_mode_open(void) { return ui_save_mode_on; }

void ui_save_mode_begin(void)
{
    ui_save_mode_which = 0u;
    if (!ui_save_mode_on)
        ui_reset_page();
    ui_save_mode_on = 1;
}

uint8_t ui_save_mode(void) { return ui_save_mode_which; }

void ui_save_mode_move(int32_t delta)
{
    if (!ui_save_mode_on)
        return;
    if (delta > 0)
        ui_save_mode_which = ui_save_mode_which == 2u ? 0u : (uint8_t)(ui_save_mode_which + 1u);
    else
        ui_save_mode_which = ui_save_mode_which == 0u ? 2u : (uint8_t)(ui_save_mode_which - 1u);
}

void ui_save_mode_commit(void)
{
    if (ui_save_mode_on) {
        ui_save_mode_on = 0;
        ui_reset_page();
    }
}

void ui_save_mode_cancel(void)
{
    if (ui_save_mode_on) {
        ui_save_mode_on = 0;
        ui_reset_page();                           /* back to the save chooser (still open) */
    }
}

/* the save-mode chooser pop-up: title + three rows (the selected in purple). */
static void ui_draw_save_mode(void)
{
    static const char *const ui_save_mode_text[3] = {
        "discard edits", "save as new part", "mutate in place"};
    uint32_t i;
    cv_begin(240u, 5u * UI_ROW_H, C_POPUP_BG);
    cv_text(6, 2, &FONT_S, "SAVE multi-patch", C_POPUP_TXT);
    for (i = 0; i < 3u; i++) {
        char row[24];
        ui_strcpy(row, i == ui_save_mode_which ? "> " : "  ");
        ui_strcat(row, ui_save_mode_text[i]);
        cv_text(6, (int32_t)(i + 1u) * UI_ROW_H, &FONT_S, row,
                i == ui_save_mode_which ? C_AMB : C_HI);
    }
    cv_text(6, 4 * UI_ROW_H, &FONT_S, "K1=mode SAVE=save HOME=back", C_POPUP_TXT);
    cv_blit(0, 4 * UI_ROW_H);
}

/* ---- the "which single part" chooser (before a part load/save/init) ---- */

uint8_t ui_part_chooser_open(void) { return ui_part_sel_on; }
uint8_t ui_part_chooser_part(void) { return ui_part_sel_which; }

void ui_part_chooser_begin(uint8_t part)
{
    ui_part_sel_which = part < 2u ? part : 0u;
    if (!ui_part_sel_on)
        ui_reset_page();
    ui_part_sel_on = 1;
}

void ui_part_chooser_move(int32_t delta)
{
    (void)delta;
    if (!ui_part_sel_on)
        return;
    ui_part_sel_which = ui_part_sel_which ? 0u : 1u;   /* two parts: toggle */
}

void ui_part_chooser_commit(void)
{
    if (ui_part_sel_on) {
        ui_part_sel_on = 0;
        ui_reset_page();
    }
}

void ui_part_chooser_cancel(void)
{
    if (ui_part_sel_on) {
        ui_part_sel_on = 0;
        ui_reset_page();
    }
}

/* the "which single part" chooser pop-up: title + two rows (selected in purple). */
static void ui_draw_part_chooser(void)
{
    static const char *const ui_part_text[2] = {"PART 1", "PART 2"};
    uint32_t i;
    cv_begin(240u, 4u * UI_ROW_H, C_POPUP_BG);
    cv_text(6, 2, &FONT_S, "WHICH SINGLE PART", C_POPUP_TXT);
    for (i = 0; i < 2u; i++) {
        char row[16];
        ui_strcpy(row, i == ui_part_sel_which ? "> " : "  ");
        ui_strcat(row, ui_part_text[i]);
        cv_text(6, (int32_t)(i + 1u) * UI_ROW_H, &FONT_S, row,
                i == ui_part_sel_which ? C_AMB : C_HI);
    }
    cv_blit(0, 4 * UI_ROW_H);
}

/* draw one legend line (up to `\n` or NUL): `~...~` segments in hot pink, the
 * rest in white. Returns nothing (the pen carries via x). */
static void legend_line(const char *s, int32_t y)
{
    int32_t x = 0;
    int pink = 0;
    while (*s && *s != '\n') {
        if (*s == '~') {
            pink = !pink;
            s++;
            continue;
        }
        const char *e = s;
        char seg[24];
        uint32_t k, n;
        while (*e && *e != '\n' && *e != '~')
            e++;
        n = (uint32_t)(e - s);
        if (n >= sizeof seg)
            n = sizeof seg - 1u;
        for (k = 0; k < n; k++)
            seg[k] = s[k];
        seg[n] = 0;
        x = cv_text(x, y, &FONT_S, seg, pink ? C_HI : C_TEXT);
        s = e;
    }
}

/* the footer legend: a two-line gesture hint at the bottom (rows 13-14), drawn
 * only when the page's widgets leave those rows free. `~...~` = hot pink. */
static void ui_draw_legend(void)
{
    const ui_page *p = ui_cur_page();
    uint32_t i, bottom = 0;
    if (!ui_t->legend || !ui_t->legend[0])
        return;
    for (i = 0; i < p->n; i++) {
        uint32_t b = (uint32_t)p->w[i].row + (uint32_t)(p->w[i].span ? p->w[i].span : 1u);
        if (b > bottom)
            bottom = b;
    }
    if (bottom > 13u)
        return;                     /* the last two rows are in use: skip the legend */
    cv_begin(240u, 2u * UI_ROW_H, C_BLACK);
    legend_line(ui_t->legend, 0);
    {
        const char *nl = ui_t->legend;
        while (*nl && *nl != '\n')
            nl++;
        if (*nl == '\n')
            legend_line(nl + 1, UI_ROW_H);
    }
    cv_blit(0, 13 * UI_ROW_H);
}

void ui_redraw(uint32_t now_ms)
{
    static uint32_t last_draw;
    const ui_page *p = ui_cur_page();
    uint32_t i;
    if (now_ms - last_draw < UI_REDRAW_MS)
        return;
    last_draw = now_ms;
    {
        int32_t hv = ui_header_value();
        if (hv != ui_header_last) {                 /* the header is always visible */
            ui_header_last = hv;
            ui_draw_header();
        }
    }
    for (i = 0; i < p->n; i++) {
        int32_t v = ui_widget_value(&p->w[i], i);
        if (v != ui_last[i]) {                     /* redraw only what changed */
            ui_last[i] = v;
            ui_draw_widget(&p->w[i]);
        }
    }
    ui_draw_legend();
    if (ui_popup_on)
        ui_draw_popup();
    if (ui_popup_alg_on)
        ui_draw_alg_popup();
    if (ui_name_on)
        ui_draw_name_editor();
    if (ui_save_on)
        ui_draw_save();
    if (ui_save_mode_on)
        ui_draw_save_mode();
    if (ui_part_sel_on)
        ui_draw_part_chooser();
}

/* the safe-failure screen: drawn independently, never through the widget engine */
void ui_safe_fail(const char *msg)
{
    lcd_fill(0, 0, 240, 240, C_BLACK);
    draw_text_box(0, 100, 240, &FONT_S, "umetate: stopped", C_WHITE, 1);
    draw_text_box(0, 132, 240, &FONT_S, msg, C_GRAY, 1);
    lcd_sync();
}
