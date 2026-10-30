/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The UI runtime (docs/roadmap.md §12.6). Included into the app after gfx.c, so the
 * canvas (cv_*, FONT_S/FONT_L) and the palette colors (C_*) are in scope. */
#include "ui.h"

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

static const ui_context *ui_ctx(void) { return &ui_t->ctx[ui_stack[ui_sp]]; }
static const ui_page *ui_cur_page(void) { return &ui_ctx()->pages[ui_pagei[ui_sp]]; }

static void ui_reset_page(void)
{
    uint32_t i;
    for (i = 0; i < UI_MAX_WIDGETS; i++)
        ui_last[i] = 0x7FFFFFFF;                 /* sentinel: everything redraws */
    ui_cursor = 0;
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
 * (~3% per detent, so 0 stays reachable). The result is clamped to [min, max]. */
static void ui_step_param(uint16_t p, int32_t delta)
{
    const ui_param_disp *d = (ui_t->disp && p < ui_t->n_params) ? &ui_t->disp[p] : 0;
    int32_t v = p < ui_t->n_params ? ui_param_v[p] : 0;
    if (!delta)
        return;
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

/* the widget types a page-slot encoder can edit (the param-bearing widgets) */
static int ui_is_param_slot(uint8_t type)
{
    return type == UI_VALUE || type == UI_BAR || type == UI_PARAM_ROW ||
           type == UI_PARAM_COLUMN || type == UI_OP_ROW;
}

static uint16_t ui_slot_param(uint8_t slot)
{
    const ui_page *p = ui_cur_page();
    uint32_t i, n = 0;
    for (i = 0; i < p->n; i++) {
        if (ui_is_param_slot(p->w[i].type)) {
            if (n == slot)
                return ui_widget_param(&p->w[i]);
            n++;
        }
    }
    return UI_NO_PARAM;
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
    case UI_ACT_OP_MUTE:
        if (ui_t->mute && ui_selected_op < 4u) {
            uint16_t p = ui_t->mute[ui_selected_op];
            if (p < ui_t->n_params)
                ui_param_v[p] = ui_param_v[p] ? 0 : 1;
        }
        break;
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
        uint16_t p = ui_slot_param(b->arg);
        if (p < ui_t->n_params) {
            if (b->behavior == UI_REL)
                ui_step_param(p, value);
            else {
                ui_param_v[p] = value;
                ui_clamp_param(p);
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

/* the param id a widget reads: UI_OP_ROW/UI_ENVELOPE resolve through the operator */
static uint16_t ui_widget_param(const ui_widget *w)
{
    if ((w->type == UI_OP_ROW || w->type == UI_ENVELOPE) && ui_t->op_param
        && w->param < ui_t->n_op_param)
        return ui_t->op_param[(uint32_t)ui_selected_op * ui_t->n_op_param + w->param];
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
        ui_itoa_dec((int32_t)(((int64_t)v * 1200) >> 15), 2, out);
        ui_strcat(out, "st");
        break;
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
 * envelope params (r1..r4, l1..l3) from the `env` group. Stage length = 65536/rate
 * (the one-pole time constant, clamped); a short flat sustain segment. No cursor. */
static void ui_draw_envelope(const ui_widget *w)
{
    uint32_t x, y, wd, ht, i, cx;
    uint32_t len[5], total = 0, p0;
    int32_t lvl[5], px[6], py[6];

    ui_region(w, &x, &y, &wd, &ht);
    if (!ui_t->env || ui_selected_op >= ui_t->n_op)
        return;
    p0 = (uint32_t)ui_selected_op * 7u;
    for (i = 0; i < 3; i++) {                       /* r1..r3: attack, decay1, decay2 */
        uint16_t p = ui_t->env[p0 + i];
        int32_t r = p < ui_t->n_params ? ui_param_v[p] : 0;
        uint32_t t = r <= 0 ? 60u : (uint32_t)(65536u / (uint32_t)r);
        len[i] = t < 2u ? 2u : (t > 60u ? 60u : t);
        total += len[i];
    }
    len[3] = 8u;                                    /* sustain: a short flat hold */
    total += len[3];
    {
        uint16_t p = ui_t->env[p0 + 3];             /* r4: the release rate */
        int32_t r = p < ui_t->n_params ? ui_param_v[p] : 0;
        uint32_t t = r <= 0 ? 60u : (uint32_t)(65536u / (uint32_t)r);
        len[4] = t < 2u ? 2u : (t > 60u ? 60u : t);
        total += len[4];
    }
    if (!total)
        total = 1u;
    for (i = 0; i < 3; i++) {
        uint16_t p = ui_t->env[p0 + 4u + i];
        lvl[i] = p < ui_t->n_params ? ui_param_v[p] : 0;
    }
    lvl[3] = lvl[2];
    lvl[4] = 0;
    for (i = 0; i < 5; i++) {
        if (lvl[i] < 0) lvl[i] = 0;
        if (lvl[i] > 32767) lvl[i] = 32767;
    }
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

/* the oscilloscope: the selected channel's snapshot, downsampled to the widget
 * width, drawn as a line with a mid-line. `w->param` is the scope channel
 * (0 = the final mix, 1.. = the per-op/per-part taps). Time-varying — redraws
 * whenever the snapshot advances (scope_seq), which the ISR bumps every block. */
static void ui_draw_scope(const ui_widget *w)
{
    uint32_t ch = (uint32_t)w->param, x, y, wd, ht, i;
    int32_t mid, lx, ly;
    ui_region(w, &x, &y, &wd, &ht);
    if (wd < 2u)
        return;
    cv_begin(wd, ht, C_BLACK);
    mid = (int32_t)ht / 2;
    cv_line(0, mid, (int32_t)wd - 1, mid, C_DIM);
    lx = 0;
    ly = mid - (scope_at_ch(ch, 0u) * (int32_t)ht) / 65536;
    for (i = 1; i < wd; i++) {
        int32_t s = scope_at_ch(ch, i * SCOPE_N / wd);
        int32_t px = (int32_t)i, py = mid - (s * (int32_t)ht) / 65536;
        cv_line(lx, ly, px, py, C_HI);
        lx = px;
        ly = py;
    }
    cv_blit(x, y);
}

/* the spectrogram: SCOPE_BINS linearly-spaced Goertzel bars (power-normalized),
 * log-free and integer — the ear hears power, and the harmonic series is visible.
 * `w->param` is the scope channel. */
static void ui_draw_spectro(const ui_widget *w)
{
    uint32_t x, y, wd, ht, i;
    uint16_t mag[SCOPE_BINS];
    uint32_t bw;
    ui_region(w, &x, &y, &wd, &ht);
    scope_spectrum_ch((uint32_t)w->param, mag, SCOPE_BINS);
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
        uint16_t p = ui_t->mute[ui_selected_op];
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

static void ui_draw_widget(const ui_widget *w)
{
    switch (w->type) {
    case UI_LABEL: ui_draw_label(w); break;
    case UI_VALUE:
    case UI_PARAM_ROW:
    case UI_OP_ROW: ui_draw_value(w); break;
    case UI_BAR: ui_draw_bar(w); break;
    case UI_PARAM_COLUMN: ui_draw_list(w); break;   /* stacked name/value rows */
    case UI_LIST: ui_draw_list(w); break;
    case UI_GRID: ui_draw_grid(w); break;
    case UI_ENVELOPE: ui_draw_envelope(w); break;
    case UI_SCOPE: ui_draw_scope(w); break;
    case UI_SPECTRO: ui_draw_spectro(w); break;
    case UI_STATUS: ui_draw_status(w); break;
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
    case UI_LIST:
    case UI_GRID: return ui_cursor;
    case UI_ENVELOPE: {                             /* redraw when any of the 7 change */
        int32_t sum = 0;
        uint32_t i, p0 = (uint32_t)ui_selected_op * 7u;
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
            uint16_t p = ui_t->mute[ui_selected_op];
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

void ui_redraw(uint32_t now_ms)
{
    static uint32_t last_draw;
    const ui_page *p = ui_cur_page();
    uint32_t i;
    if (now_ms - last_draw < UI_REDRAW_MS)
        return;
    last_draw = now_ms;
    for (i = 0; i < p->n; i++) {
        int32_t v = ui_widget_value(&p->w[i], i);
        if (v != ui_last[i]) {                     /* redraw only what changed */
            ui_last[i] = v;
            ui_draw_widget(&p->w[i]);
        }
    }
}

/* the safe-failure screen: drawn independently, never through the widget engine */
void ui_safe_fail(const char *msg)
{
    lcd_fill(0, 0, 240, 240, C_BLACK);
    draw_text_box(0, 100, 240, &FONT_S, "umetate: stopped", C_WHITE, 1);
    draw_text_box(0, 132, 240, &FONT_S, msg, C_GRAY, 1);
    lcd_sync();
}
