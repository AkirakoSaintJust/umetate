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
static int32_t ui_param_v[64];
static uint8_t ui_stack[UI_MAX_DEPTH], ui_sp;   /* context ids; top = active */
static uint8_t ui_pagei[UI_MAX_DEPTH];          /* the page within each context */
static int32_t ui_last[UI_MAX_WIDGETS];         /* last-drawn value per widget slot */
static int32_t ui_custom_v[UI_MAX_WIDGETS];     /* UI_CUSTOM widgets' dirty values (app-set) */
static int32_t ui_cursor;                        /* list/grid selection */

static const ui_context *ui_ctx(void) { return &ui_t->ctx[ui_stack[ui_sp]]; }
static const ui_page *ui_cur_page(void) { return &ui_ctx()->pages[ui_pagei[ui_sp]]; }

static void ui_reset_page(void)
{
    uint32_t i;
    for (i = 0; i < UI_MAX_WIDGETS; i++)
        ui_last[i] = 0x7FFFFFFF;                 /* sentinel: everything redraws */
    ui_cursor = 0;
}

void ui_init(const ui_tables *t)
{
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

/* linear/log value scaling (log is a 6-octave approximation, deferred to a table) */
static int32_t ui_scale(int32_t v, uint8_t curve)
{
    (void)curve;                                 /* linear identity for now */
    return v;
}

static void ui_do_action(uint8_t action, uint8_t arg)
{
    switch (action) {
    case UI_ACT_NOTE_ON: break;                  /* handled by ui_handle (needs value) */
    case UI_ACT_NOTE_OFF: break;
    case UI_ACT_SET_STEP: ui_act_set_step(arg); break;
    case UI_ACT_PUSH: ui_push(arg); break;
    case UI_ACT_POP: ui_pop(); break;
    case UI_ACT_POP_HOME: ui_pop_home(); break;
    case UI_ACT_NEXT_PAGE:
        if (ui_pagei[ui_sp] + 1u < ui_ctx()->n_pages) { ui_pagei[ui_sp]++; ui_reset_page(); }
        break;
    case UI_ACT_PREV_PAGE:
        if (ui_pagei[ui_sp]) { ui_pagei[ui_sp]--; ui_reset_page(); }
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
                ui_param_v[b->target] += ui_scale(value, b->curve);
            else
                ui_param_v[b->target] = ui_scale(value, b->curve);
        }
    } else if (b->action == UI_ACT_NOTE_ON && value >= 0)
        ui_act_note_on((uint8_t)value, 100u);
    else if (b->action == UI_ACT_NOTE_OFF && value >= 0)
        ui_act_note_off((uint8_t)value);
    else if (b->action == UI_ACT_SET_STEP && value >= 0)
        ui_act_set_step((uint8_t)value);
    else
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

/* format a param value into `out`: fmt is a printf-style hint; only "%d" (or empty)
 * and a trailing unit are supported. */
static void ui_format(const ui_widget *w, char *out, uint32_t n)
{
    int32_t v = w->param < ui_t->n_params ? ui_param_v[w->param] : 0;
    out[0] = 0;
    if (w->text)
        ui_strcat(out, w->text);
    if (w->text && (w->fmt || w->unit))
        ui_strcat(out, " ");
    if (w->fmt && w->fmt[0] == '%' && w->fmt[1] == 's' && w->text == 0) {
        /* "%s": the param is a raw string (unsupported here; show the int) */
    }
    ui_itoa(v, out + ui_strlen(out));
    if (w->unit) {
        ui_strcat(out, " ");
        ui_strcat(out, w->unit);
    }
    (void)n;
}

static void ui_draw_value(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    char s[32];
    ui_region(w, &x, &y, &wd, &ht);
    ui_format(w, s, sizeof s);
    draw_text_box(x, y, wd, &FONT_S, s, C_HI, 0);
}

static void ui_draw_bar(const ui_widget *w)
{
    uint32_t x, y, wd, ht;
    int32_t v = w->param < ui_t->n_params ? ui_param_v[w->param] : 0;
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

static void ui_draw_widget(const ui_widget *w)
{
    switch (w->type) {
    case UI_LABEL: ui_draw_label(w); break;
    case UI_VALUE:
    case UI_PARAM_ROW: ui_draw_value(w); break;
    case UI_BAR: ui_draw_bar(w); break;
    case UI_PARAM_COLUMN: ui_draw_list(w); break;   /* stacked name/value rows */
    case UI_LIST: ui_draw_list(w); break;
    case UI_GRID: ui_draw_grid(w); break;
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
    case UI_LIST:
    case UI_GRID: return ui_cursor;
    default:                                       /* VALUE/BAR/PARAM_ROW/COLUMN */
        return w->param < ui_t->n_params ? ui_param_v[w->param] : 0;
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
