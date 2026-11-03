/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The generic app core (docs/roadmap.md §6.11.4, §12.6): the preset
 * save/load/init/name flow and the modal popup state machine, shared by every
 * synth project. The UI kit (ui.c) already provides the popups (the save chooser,
 * the save-mode chooser, the part chooser, the page-copy chooser, the name editor,
 * the preset browser), all non-destructive with an idle auto-close. This module is
 * the glue that drives them over a project's generated seam + preset banks, so a
 * project's `app.c` only writes its control mapping + its `ui_draw_custom`.
 *
 * A project fills a `synth_app_ctx` once (its generated `<name>_glue_*` seam, the
 * `SYNTH_*` layout, the init table, and the `.pool` bank buffers), then routes:
 *   ui_act_save        -> synth_app_save(ctx)
 *   ui_act_init_patch  -> synth_app_init_patch(ctx)
 *   ui_act_init_part   -> synth_app_init_part(ctx)
 *   ui_act_name        -> ui_name_editor_begin(which)  (a one-liner; not here)
 *   ui_save_slot_name  -> synth_app_slot_name(ctx, kind, slot, out, cap)
 *   ui_preset_apply    -> synth_app_apply(ctx, kind, slot)
 *   app_step           -> if (synth_app_step(ctx)) return-to-the-loop; else its own map
 *   app_step (end)     -> synth_app_tick(ctx, fm1_ms, <name>_glue_quiet()) */
#pragma once
#include <stdint.h>
#include "presets.h"
#include "ui.h"

#define SYNTH_APP_MAX_PARTS 8u
/* every part needs a name slot, and the multi-patch takes the one after them */
_Static_assert(SYNTH_APP_MAX_PARTS <= UI_PART_MAX,
               "synth_app: the part cap must fit ui.h's UI_PART_MAX");

typedef struct {
    /* ---- the engine seam (the generated glue.h / dsp.h) ---- */
    int32_t (*get_param)(uint32_t id);
    int (*set_param)(uint32_t id, int32_t value); /* the glue set_param (returns 0/1) */
    void (*reset)(void);
    /* ---- the generated layout (synth_layout.h) ---- */
    uint32_t n_params;      /* the per-part timbre param count */
    uint32_t n_parts;       /* the part count */
    uint32_t routing_base;  /* part 0's channel param id */
    /* the generated init table, read through a callback so the app core never
     * type-puns the generated `<name>_init_entry` */
    void (*get_init)(uint32_t i, uint16_t *id, int32_t *value);
    uint32_t init_n;
    /* ---- the preset banks (the project's `.pool` buffers) ---- */
    uint8_t *part_bank;     /* PP_BANK(n_params) bytes */
    uint8_t *multi_bank;    /* MP_BANK(n_parts) bytes */
    uint8_t *settings;      /* ST_RECORD bytes */
    /* ---- the runtime state (do not touch) ---- */
    uint8_t part_slot[SYNTH_APP_MAX_PARTS]; /* each part's source single-part slot (0xFF = live) */
    uint16_t cur_slot;                      /* the loaded multi-patch slot */
    uint8_t pending_part;                   /* 0 = none, 1 = load, 2 = save, 3 = init */
    uint16_t pending_slot;                  /* the pending load/save slot */
    uint32_t saved_ms;                      /* the "SAVED/COPIED" linger */
    uint32_t last_input_ms;                 /* the popup idle auto-close */
    uint32_t t_change;                      /* the last save (the silent delay) */
    uint8_t bank_dirty, multi_dirty, set_dirty;
    uint8_t saved_settings[ST_RECORD];
    ui_browser browser;                     /* the framework preset-browse popup */
} synth_app_ctx;

/* Boot: clear the banks, load them from flash, load + apply the settings, apply
 * multi slot 0, and seed the INIT names. Call once from app_init after ui_init. */
void synth_app_boot(synth_app_ctx *ctx);

/* The SAVE action: open the save chooser, pre-filled from the active part's source
 * slot + the current multi-patch slot. */
void synth_app_save(synth_app_ctx *ctx);

/* INIT PATCH (the whole patch) / INIT PART (the active part). */
void synth_app_init_patch(synth_app_ctx *ctx);
void synth_app_init_part(synth_app_ctx *ctx);

/* The browser's apply hook: kind 0 = single part (opens the "which part" chooser),
 * kind 1 = multi-patch (applies straight in). */
void synth_app_apply(synth_app_ctx *ctx, uint8_t kind, uint16_t slot);

/* Fill `out` with the stored name of a slot (kind 0 = single part, 1 = multi-patch),
 * or "" if empty. The save chooser calls it to show what a save would overwrite. */
void synth_app_slot_name(const synth_app_ctx *ctx, uint8_t kind, uint16_t slot,
                         char *out, uint32_t cap);

/* Handle one modal popup (name editor / save-mode / save / part chooser / page-copy)
 * and drain its inputs. Returns 1 when a modal popup consumed the input (the app's
 * own control map must be skipped); 0 otherwise. */
uint8_t synth_app_step(synth_app_ctx *ctx);

/* The PRESETS encoder: open the multi-patch browser, or the single-part browser
 * when `single_part` is set (a project can use its GLO page as the single-part
 * view). A 2 s idle applies the highlighted slot through `ui_preset_apply`. */
void synth_app_browser_step(synth_app_ctx *ctx, int32_t delta, uint32_t now,
                            uint8_t single_part);

/* The per-loop tick: the "SAVED/COPIED" linger, the modal idle auto-close (~3 s),
 * and the silent-only bank persistence. Call once per app_step with `quiet` = the
 * engine's quiet flag. */
void synth_app_tick(synth_app_ctx *ctx, uint32_t now, uint8_t quiet);

/* Note that the app saw input this step (resets the popup idle auto-close timer). */
void synth_app_input(synth_app_ctx *ctx);
