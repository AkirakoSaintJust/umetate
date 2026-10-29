/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* Hand-maintained UI-kit test fixture (docs/roadmap.md §12.6). Exercises the
 * context stack + the operator-relative machinery against a minimal four-context
 * panel: home (a `status` + three `param_row`s), edit (an op row + operator
 * select/mute), step (KEY -> set_step), and fx (switch target). Do not edit
 * casually: ui_test.c asserts against these exact ids. */
#pragma once
#include "ui.h"

enum { P_alg = 0, P_cutoff, P_res, P_fold, P_op1_level, P_op2_level, P_ratio, P_mute, P_hz, P_semi, N_PARAMS = 10 };

/* the per-param display scale for the test params */
static const ui_param_disp DISP_TBL[N_PARAMS] = {
    { UI_DISP_RAW, 0, 0, 0 },        /* P_alg: 0..0 placeholder (0..7 in real use) */
    { UI_DISP_OFF_PCT, 1, 0, 65535 },/* P_cutoff: "off" at 0, else % */
    { UI_DISP_PCT_INV, 0, 0, 65535 },/* P_res: 100% at min */
    { UI_DISP_PCT, 0, 0, 32767 },    /* P_fold */
    { UI_DISP_PCT, 0, 0, 32767 },    /* P_op1_level */
    { UI_DISP_PCT, 0, 0, 32767 },    /* P_op2_level */
    { UI_DISP_RATIO, 0, 32768, 1048576 }, /* P_ratio */
    { UI_DISP_ONOFF, 0, 0, 1 },      /* P_mute */
    { UI_DISP_HZ, 1, 0, 20000000 },  /* P_hz */
    { UI_DISP_SEMI, 0, -32768, 32767 }, /* P_semi */
};

static const ui_widget W_0_0[] = {
    { UI_STATUS, 1, 0, 2, P_alg, 0, 0, 0, 0, 0 },
    { UI_PARAM_ROW, 4, 0, 1, P_cutoff, "CUTOFF", 0, 0, 0, 0 },
    { UI_PARAM_ROW, 5, 0, 1, P_res, "RES", 0, 0, 0, 0 },
    { UI_PARAM_ROW, 6, 0, 1, P_fold, "FOLD", 0, 0, 0, 0 },
};
static const ui_page PG_0[] = {
    { "", W_0_0, (uint8_t)(sizeof W_0_0 / sizeof W_0_0[0]) },
};
static const ui_widget W_1_0[] = {
    { UI_STATUS, 1, 0, 2, P_alg, 0, 0, 0, 0, 0 },
    { UI_OP_ROW, 4, 0, 1, 0, "LEVEL", 0, 0, 0, 0 },
};
static const ui_page PG_1[] = {
    { "", W_1_0, (uint8_t)(sizeof W_1_0 / sizeof W_1_0[0]) },
};
static const ui_widget W_2_0[] = {
    { UI_LABEL, 1, 0, 1, UI_NO_PARAM, "STEP", 0, 0, 0, 0 },
};
static const ui_page PG_2[] = {
    { "", W_2_0, (uint8_t)(sizeof W_2_0 / sizeof W_2_0[0]) },
};
static const ui_widget W_3_0[] = {
    { UI_LABEL, 1, 0, 1, UI_NO_PARAM, "FX", 0, 0, 0, 0 },
};
static const ui_page PG_3[] = {
    { "", W_3_0, (uint8_t)(sizeof W_3_0 / sizeof W_3_0[0]) },
};

static const ui_binding BIND_0[] = {
    { UI_BIND_PAGE_SLOT, UI_SRC_ENC_KNOB1, 0, 0, 0, UI_REL, 0 },
    { UI_BIND_PAGE_SLOT, UI_SRC_ENC_KNOB2, 0, 0, 1, UI_REL, 0 },
    { UI_BIND_PAGE_SLOT, UI_SRC_ENC_KNOB3, 0, 0, 2, UI_REL, 0 },
};
static const ui_binding BIND_1[] = {
    { UI_BIND_PARAM, UI_SRC_ENC_PRESETS, P_cutoff, 0, 0, UI_REL, 0 },
    { UI_BIND_ACTION, UI_SRC_BTN_SEL, 0, UI_ACT_OP_NEXT, 0, UI_ABS, 0 },
    { UI_BIND_ACTION, UI_SRC_BTN_ENV, 0, UI_ACT_OP_MUTE, 0, UI_ABS, 0 },
};
static const ui_binding BIND_2[] = {
    { UI_BIND_ACTION, UI_SRC_KEY, 0, UI_ACT_SET_STEP, 0, UI_ABS, 0 },
};
static const ui_binding BIND_3[] = {
};
static const ui_binding GLOBAL_BIND[] = {
    { UI_BIND_ACTION, UI_SRC_KEY, 0, UI_ACT_NOTE_ON, 0, UI_ABS, 0 },
    { UI_BIND_ACTION, UI_SRC_BTN_SEQ, 0, UI_ACT_PUSH, 2, UI_ABS, 0 },
    { UI_BIND_ACTION, UI_SRC_BTN_EDIT, 0, UI_ACT_SWITCH, 1, UI_ABS, 0 },
    { UI_BIND_ACTION, UI_SRC_BTN_FX, 0, UI_ACT_SWITCH, 3, UI_ABS, 0 },
    { UI_BIND_ACTION, UI_SRC_BTN_HOME, 0, UI_ACT_POP_HOME, 0, UI_ABS, 0 },
};

static const ui_context CTX[] = {
    { PG_0, 1, BIND_0, 3, 0, 0 },
    { PG_1, 1, BIND_1, 3, 0, 0 },
    { PG_2, 1, BIND_2, 1, 0, 0 },
    { PG_3, 1, BIND_3, 0, 0, 0 },
};

static const uint16_t MUTE_TBL[4] = { P_op1_level, P_op2_level, 0xFFFF, 0xFFFF };
static const uint16_t OP_PARAM[2] = { P_op1_level, P_op2_level };

static const ui_tables PANEL = {
    "accept", 0, CTX, 4, GLOBAL_BIND, 5, MUTE_TBL, OP_PARAM, 2, 1, 0, DISP_TBL, N_PARAMS, 8,
};
