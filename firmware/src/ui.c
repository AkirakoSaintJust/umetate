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
static char ui_name[2][UI_NAME_LEN];             /* [0] = single-part name, [1] = multi-patch name */
static char ui_name_saved[UI_NAME_LEN];          /* the pre-edit copy (for cancel) */
static uint8_t ui_name_which, ui_name_cursor, ui_name_on;  /* the name-editor state */
static uint8_t ui_save_on, ui_save_which;        /* the save chooser: open flag + selected row */
static uint16_t ui_save_slots[2];                /* [0] single-part slot, [1] multi-patch slot */
static uint8_t ui_save_mode_on, ui_save_mode_which;  /* step 2: the multi-patch save mode */

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
 * not a stack): pops back to home first, then pushes. From home it is a plain push. */
void ui_switch(uint8_t ctx)
{
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
    /* --- on/off wrap: 0 <-> 1 (only for ONOFF/ONOFF_INV display kinds) --- */
    if (d && (d->kind == UI_DISP_ONOFF || d->kind == UI_DISP_ONOFF_INV)) {
        /* wrap any integer into {0,1}: even -> 0, odd -> 1 */
        v = (v % 2 + 2) % 2;
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
        /* mute the *selected* operator (the SCL + key chord; arg is ignored) */
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
    draw_text_box(x, y, wd, f, w->text, w->span >= 2u ? C_HI : C_GRAY, 0);
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
    case UI_DISP_WAVE: {                           /* a 0..11 waveform -> its name */
        static const char *const names[12] = {
            "sine", "tri", "half sine", "half tri", "2x sine", "2x tri",
            "2x half sine", "2x half tri", "rect sine", "pulse", "square", "saw"};
        uint32_t i = v >= 0 && v < 12 ? (uint32_t)v : 0u;
        ui_strcat(out, names[i]);
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

/* a param row: the label in the label colour, the value + unit right-aligned in
 * the value colour — the value is what changes, so it is the bright/high-contrast
 * element and the label is the dim reference (the palette's C_GRAY/C_HI roles). */
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
            cv_text(0, 0, &FONT_S, w->text, C_GRAY);   /* the name: dim */
        cv_text(vx, 0, &FONT_S, val, C_HI);            /* the value: bright */
    }
    cv_blit(x, y);
}

/* a name row: the label (text, dim) + the name string (bright). `w->param` is the
 * name index (0 = part, 1 = patch). Twisting its page slot opens the editor. */
static void ui_draw_name_row(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    const char *name = ui_name_get(w->param < 2u ? w->param : 0u);
    ui_region(w, &x, &y, &wd, &ht);
    cv_begin(wd, ht, C_BLACK);
    {
        int32_t vx = (int32_t)wd - text_w(&FONT_S, name);
        if (vx < 0)
            vx = 0;
        if (w->text)
            cv_text(0, 0, &FONT_S, w->text, C_GRAY);  /* the label: dim */
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
 * envelope params (r1..r4, l1..l3) from the `env` group. Stage length = the
 * one-pole time constant 65536/fm1_rate_coeff[rate] (clamped); the level height =
 * fm1_level_gain[level] (0.25 dB/step: 99 = max, 0 = silence). No cursor. */
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
        uint32_t t = c <= 0 ? 60u : (uint32_t)(65536u / (uint32_t)c);
        len[i] = t < 2u ? 2u : (t > 60u ? 60u : t);
        total += len[i];
    }
    len[3] = 8u;                                    /* sustain: a short flat hold */
    total += len[3];
    {
        uint16_t p = ui_t->env[p0 + 3];             /* r4: the release rate */
        int32_t r = p < ui_t->n_params ? ui_param_v[p] : 0;
        int32_t c = fm1_rate_coeff[r < 0 ? 0 : (r > 99 ? 99 : r)];
        uint32_t t = c <= 0 ? 60u : (uint32_t)(65536u / (uint32_t)c);
        len[4] = t < 2u ? 2u : (t > 60u ? 60u : t);
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
        cv_line(px[i], py[i], px[i + 1], py[i + 1], C_HI);
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
static void ui_draw_scope(const ui_widget *w)
{
    uint32_t ch = ui_scope_channel(w), x, y, wd, ht, i;
    int32_t mid, lx, ly;
    ui_region(w, &x, &y, &wd, &ht);
    if (wd < 2u)
        return;
    cv_begin(wd, ht, C_BLACK);
    mid = (int32_t)ht / 2;
    cv_line(0, mid, (int32_t)wd - 1, mid, C_DIM);
    lx = 0;
    ly = mid - (scope_at_ch(ch, 0u) * (int32_t)ht) / 16384;
    for (i = 1; i < wd; i++) {
        int32_t s = scope_at_ch(ch, i * SCOPE_N / wd);
        int32_t px = (int32_t)i, py = mid - (s * (int32_t)ht) / 16384;
        cv_line(lx, ly, px, py, C_HI);
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
        cv_rect((int32_t)(i * bw), (int32_t)ht - bh, (int32_t)bw, bh, C_HI);
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
        int32_t end = cv_text(0, 0, &FONT_S, s, C_HI);
        if (muted)
            cv_text(end, 0, &FONT_S, "  MUTE", C_WARN);
    }
    cv_blit(x, y);
}

/* the page's subheader (param = the prefix mode): 0 = "OP N <suffix>", 1 =
 * "PART N <suffix>", 2 = "OP <suffix>", 3 = "PART <suffix>", 4 = "<suffix>" (a
 * global page, no prefix). N is the active operator/part; `text` is the
 * param-group name. */
static void ui_draw_subheader(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    char s[24], t[4];
    ui_region(w, &x, &y, &wd, &ht);
    s[0] = 0;
    switch (w->param) {
    case 1u:                                       /* PART N */
        ui_strcpy(s, "PART ");
        t[0] = (char)('1' + ui_selected_part);
        t[1] = 0;
        ui_strcat(s, t);
        break;
    case 2u: ui_strcpy(s, "OP "); break;           /* OP (no number) */
    case 3u: ui_strcpy(s, "PART "); break;         /* PART (no number) */
    case 4u: break;                                /* global: no prefix */
    default:                                       /* OP N */
        ui_strcpy(s, "OP ");
        t[0] = (char)('1' + ui_selected_op);
        t[1] = 0;
        ui_strcat(s, t);
        break;
    }
    if (w->text) {
        if (s[0])
            ui_strcat(s, " ");
        ui_strcat(s, w->text);
    }
    cv_begin(wd, ht, C_BLACK);
    cv_text(0, 0, &FONT_S, s, C_HI);
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

/* one header token at x: `current` = the accent colour (where we are), `muted` =
 * dim with an `x` marker (not colour-alone), else bright. Returns the next x. */
static int32_t ui_htok(int32_t x, const char *s, int cur, int muted)
{
    uint16_t c = cur ? C_WHITE : (muted ? C_DIM : C_HI);
    return cv_text(x, UI_ROW_H, &FONT_S, s, c);
}

static void ui_draw_header(void)
{
    char s[40], t[12], tok[4];
    uint32_t i;
    int32_t x, alg = ui_t->alg < ui_t->n_params ? ui_param_v[ui_t->alg] : 0;

    cv_begin(240u, 2u * UI_ROW_H, C_BLACK);
    /* row 0: P<part> OP<op> ALG<alg>  <menu> <page>/<n> */
    ui_strcpy(s, "P");
    t[0] = (char)('1' + ui_selected_part);
    t[1] = 0;
    ui_strcat(s, t);
    ui_strcat(s, " OP");
    t[0] = (char)('1' + ui_selected_op);
    t[1] = 0;
    ui_strcat(s, t);
    ui_strcat(s, " ALG");
    ui_itoa(alg, t);
    ui_strcat(s, t);
    ui_strcat(s, "  ");
    if (ui_ctx()->name)
        ui_strcat(s, ui_ctx()->name);
    ui_strcat(s, " ");
    ui_itoa((int32_t)ui_pagei[ui_sp] + 1, t);
    ui_strcat(s, t);
    ui_strcat(s, "/");
    ui_itoa((int32_t)ui_ctx()->n_pages, t);
    ui_strcat(s, t);
    cv_text(0, 0, &FONT_S, s, C_HI);

    /* row 1: every part (P1/P2) and operator (1..4), colour-coded — current =
     * accent, muted = dim `x`, active = bright. */
    x = 0;
    for (i = 0; i < ui_t->n_part; i++) {
        tok[0] = 'P';
        tok[1] = (char)('1' + i);
        tok[2] = ui_part_mute[i] ? 'x' : 0;
        tok[3] = 0;
        x = ui_htok(x, tok, i == ui_selected_part, ui_part_mute[i]);
        x = ui_htok(x, " ", 0, 0);
    }
    x = ui_htok(x, "  ", 0, 0);
    for (i = 0; i < 4u && i < ui_t->n_op; i++) {
        uint16_t p = ui_t->mute ? ui_mute_param(i) : UI_NO_PARAM;
        int muted = p < ui_t->n_params ? ui_param_v[p] != 0 : 0;
        tok[0] = (char)('1' + i);
        tok[1] = muted ? 'x' : 0;
        tok[2] = 0;
        x = ui_htok(x, tok, i == ui_selected_op, muted);
        x = ui_htok(x, " ", 0, 0);
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
        const char *n = ui_name_get(w->param < 2u ? w->param : 0u);
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
    default:                                       /* VALUE/BAR/PARAM_ROW/COLUMN/OP_ROW */
        return ui_widget_param(w) < ui_t->n_params ? ui_param_v[ui_widget_param(w)] : 0;
    }
}

void ui_custom_set(uint32_t slot, int32_t value)
{
    if (slot < UI_MAX_WIDGETS)
        ui_custom_v[slot] = value;
}

/* the preset-browser popup: a dim band over the page (rows 4-6) with a title + the
 * selected slot/name. Drawn every redraw while active (its text is transient). */
static void ui_draw_popup(void)
{
    cv_begin(240u, 3u * UI_ROW_H, C_DIM);
    cv_text(6, UI_ROW_H, &FONT_S, ui_popup_line, C_HI);
    cv_blit(0, 4 * UI_ROW_H);
}

static void ui_popup_set(const char *title, uint32_t slot, const char *name)
{
    char t[12];
    uint8_t was = ui_popup_on;
    ui_popup_on = 1;
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

void ui_popup_hide(void)
{
    if (ui_popup_on) {
        ui_popup_on = 0;
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
    return ui_name[which < 2u ? which : 0u];
}

void ui_name_set(uint8_t which, const char *name)
{
    uint32_t i;
    if (which >= 2u)
        return;
    for (i = 0; i < UI_NAME_LEN - 1u && name[i]; i++)
        ui_name[which][i] = name[i];
    ui_name[which][i] = 0;
}

uint8_t ui_name_editing(void) { return ui_name_on ? ui_name_which : 0xFFu; }

void ui_name_editor_begin(uint8_t which)
{
    uint32_t i;
    if (which >= 2u)
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

/* the name editor pop-up: title + the name (cursor char in accent) + the legend. */
static void ui_draw_name_editor(void)
{
    char s[UI_NAME_LEN + 8];
    const char *title = ui_name_which ? "multi-patch name" : "single part name";
    uint32_t i;
    cv_begin(240u, 5u * UI_ROW_H, C_DIM);
    cv_text(6, 2, &FONT_S, title, C_HI);
    /* the name: FONT_L, 15 fixed columns; the cursor char is the accent colour */
    for (i = 0; i < UI_NAME_LEN - 1u; i++) {
        char c = ui_name[ui_name_which][i];
        s[0] = c ? c : ' ';
        s[1] = 0;
        cv_text(6 + (int32_t)i * 16, UI_ROW_H, &FONT_L, s,
                i == ui_name_cursor ? C_WHITE : C_HI);
    }
    cv_text(6, 3 * UI_ROW_H, &FONT_S, "K1=char K2=cursor SCL=del SAVE=ok HOME=cancel", C_DIM);
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

/* the save chooser pop-up: title + two rows (the selected in the accent) + the legend. */
static void ui_draw_save(void)
{
    static const char *const ui_save_kind_text[2] = {"single part", "multi-patch"};
    char t[12];
    uint32_t i;
    cv_begin(240u, 5u * UI_ROW_H, C_DIM);
    cv_text(6, 2, &FONT_S, "SAVE", C_HI);
    for (i = 0; i < 2u; i++) {
        char row[32];
        ui_strcpy(row, i == ui_save_which ? "> " : "  ");
        ui_strcat(row, ui_save_kind_text[i]);
        ui_strcat(row, "  slot ");
        ui_itoa((int32_t)ui_save_slots[i], t);
        ui_strcat(row, t);
        cv_text(6, (int32_t)(i + 1u) * UI_ROW_H, &FONT_S, row,
                i == ui_save_which ? C_WHITE : C_HI);
    }
    cv_text(6, 3 * UI_ROW_H, &FONT_S, "K1=kind K2=slot SAVE=save HOME=cancel", C_DIM);
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

/* the save-mode chooser pop-up: title + three rows (the selected in the accent). */
static void ui_draw_save_mode(void)
{
    static const char *const ui_save_mode_text[3] = {
        "discard edits", "save as new part", "mutate in place"};
    uint32_t i;
    cv_begin(240u, 5u * UI_ROW_H, C_DIM);
    cv_text(6, 2, &FONT_S, "SAVE multi-patch", C_HI);
    for (i = 0; i < 3u; i++) {
        char row[24];
        ui_strcpy(row, i == ui_save_mode_which ? "> " : "  ");
        ui_strcat(row, ui_save_mode_text[i]);
        cv_text(6, (int32_t)(i + 1u) * UI_ROW_H, &FONT_S, row,
                i == ui_save_mode_which ? C_WHITE : C_HI);
    }
    cv_text(6, 4 * UI_ROW_H, &FONT_S, "K1=mode SAVE=save HOME=back", C_DIM);
    cv_blit(0, 4 * UI_ROW_H);
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
    if (ui_popup_on)
        ui_draw_popup();
    if (ui_name_on)
        ui_draw_name_editor();
    if (ui_save_on)
        ui_draw_save();
    if (ui_save_mode_on)
        ui_draw_save_mode();
}

/* the safe-failure screen: drawn independently, never through the widget engine */
void ui_safe_fail(const char *msg)
{
    lcd_fill(0, 0, 240, 240, C_BLACK);
    draw_text_box(0, 100, 240, &FONT_S, "umetate: stopped", C_WHITE, 1);
    draw_text_box(0, 132, 240, &FONT_S, msg, C_GRAY, 1);
    lcd_sync();
}
