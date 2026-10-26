/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The RIB starter panel, hand-written (the panel generator, P2-9 increment 2,
 * replaces this with gen/panel.h). A single `home` context: the app name, the last
 * note, the octave/channel status, and the keyboard (a UI_CUSTOM canvas widget). */
#pragma once
#include "ui.h"

enum { P_OCTAVE = 0, P_CHANNEL, P_NOTE, N_PARAMS };

static const ui_widget HOME_W[] = {
    /* type           row col span param       text                 unit fmt items n */
    { UI_LABEL,        1, 0, 2,  UI_NO_PARAM, "RIB",               0,   0,  0,    0 },
    { UI_LABEL,        3, 0, 1,  UI_NO_PARAM, "a sine to build on", 0,  0,  0,    0 },
    { UI_VALUE,        5, 0, 2,  P_NOTE,      0,                   0,   0,  0,    0 },
    { UI_PARAM_ROW,    8, 0, 1,  P_OCTAVE,    "OCT",               0,   0,  0,    0 },
    { UI_PARAM_ROW,    9, 0, 1,  P_CHANNEL,   "MIDI",              0,   0,  0,    0 },
    { UI_CUSTOM,      11, 0, 3,  UI_NO_PARAM, 0,                   0,   0,  0,    0 },
};

static const ui_page HOME_PAGES[] = {
    { "home", HOME_W, (uint8_t)(sizeof HOME_W / sizeof HOME_W[0]) },
};

static const ui_binding HOME_BIND[] = {
    /* kind            source             target    action arg behavior curve */
    { UI_BIND_PARAM,    UI_SRC_BTN_OCT_DOWN, P_OCTAVE,  0,  0, UI_REL, 0 },
    { UI_BIND_PARAM,    UI_SRC_BTN_OCT_UP,   P_OCTAVE,  0,  0, UI_REL, 0 },
    { UI_BIND_PARAM,    UI_SRC_ENC_PRESETS,  P_CHANNEL, 0,  0, UI_REL, 0 },
};

static const ui_context CTX[] = {
    /* pages       n_pages bindings  n_bindings on_enter on_exit */
    { HOME_PAGES, 1,      HOME_BIND, 3,         0,        0 },
};

static const ui_binding GLOBAL_BIND[] = {
    /* kind            source    target action          arg behavior curve */
    { UI_BIND_ACTION,  UI_SRC_KEY, 0,   UI_ACT_NOTE_ON, 0,  UI_ABS,   0 },
};

static const ui_tables PANEL = {
    /* name  home ctx  n_ctx global       n_global n_params n_widgets */
    "rib", 0, CTX, 1,    GLOBAL_BIND, 1,       N_PARAMS,
    (uint16_t)(sizeof HOME_W / sizeof HOME_W[0]),
};
