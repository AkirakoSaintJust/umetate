# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate scaffold` — generate a node/macro/patch/synth skeleton (§12.7.4).

`--template T` copies a shipped example (e.g. `type-p-fm1`) instead of the empty
skeleton. A generated `patch` is verified to build (generate + host compile); a
generated `synth` is a complete minimal firmware (patch + panel + app glue) that
`umetate build --synth` composes into sound out of the box.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ._ir import to_c_identifier
from ._panel import generate_panel
from ._schema import PanelManifest, Patch, as_panel, as_patch
from .generate import generate, param_ids, param_meta

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = _ROOT / "examples"
_FW = _ROOT / "firmware"

_NODE_C = """/* TODO: the per-sample body (${in.*} ${out.*} ${state.*} ${param.*}). */
int32_t ${out.audio} = ${in.in};
"""


def _minimal_patch(name: str) -> Patch:
    return {
        "name": name,
        "voices": 4,
        "voice": {
            "nodes": [
                {"id": "ph", "type": "phasor"},
                {"id": "osc", "type": "osc"},
                {"id": "env", "type": "env"},
                {"id": "vca", "type": "vca"},
            ],
            "wires": [
                {"from": "ph.phase", "to": "osc.phase"},
                {"from": "osc.audio", "to": "vca.audio"},
                {"from": "env.cv", "to": "vca.cv"},
            ],
            "voice_out": "vca.audio",
        },
        "global": {"nodes": [], "wires": []},
    }


def _minimal_panel(name: str) -> PanelManifest:
    return {
        "name": name,
        "home": "home",
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [{"type": "label", "row": 1, "text": name}],
                    }
                ]
            }
        },
    }


def _write(directory: Path, name: str, data: object) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# -----------------------------------------------------------------------------
# `umetate scaffold synth` — a complete, minimal full firmware (the two-tier gap:
# patch-level `scaffold patch` stops at a generator dogfood; `synth` adds the app
# glue so `umetate build --synth <dir>` produces sound out of the box).
# -----------------------------------------------------------------------------


def _minimal_synth_patch(name: str) -> Patch:
    """A minimal single-part synth: phasor -> osc -> vca with an AR envelope, and
    four params (waveform / level / attack / release) exposed to the panel + CC."""
    patch = _minimal_patch(name)
    patch["model"] = 64
    patch["cc"] = ["waveform", "level", "attack", "release"]
    patch["init"] = {
        "waveform": 0,
        "level": 32767,
        "attack": 3000,
        "release": 5000,
    }
    patch["params"] = {
        "waveform": {
            "target": "osc.waveform",
            "min": 0,
            "max": 11,
            "curve": "linear",
            "display": "wave",
        },
        "level": {
            "target": "vca.level",
            "min": 0,
            "max": 32767,
            "curve": "linear",
            "display": "pct",
        },
        "attack": {"target": "env.attack", "min": 0, "max": 65535, "curve": "linear"},
        "release": {"target": "env.release", "min": 0, "max": 65535, "curve": "linear"},
    }
    return patch


def _minimal_synth_panel(name: str) -> PanelManifest:
    """A single HOME page with the four params on KNOB1-4 + the global KEY/HOME
    bindings (so the keybed plays notes and HOME pops home)."""
    return {
        "name": name,
        "home": "home",
        "parts": 1,
        "global": [
            {"source": "KEY", "action": "note_on"},
            {"source": "BTN_HOME", "action": "pop_home"},
        ],
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "main",
                        "widgets": [
                            {
                                "type": "subheader",
                                "row": 2,
                                "text": name.upper(),
                                "plain": True,
                            },
                            {
                                "type": "param_row",
                                "row": 3,
                                "param": "waveform",
                                "text": "WAVE",
                            },
                            {
                                "type": "param_row",
                                "row": 4,
                                "param": "level",
                                "text": "LEVEL",
                            },
                            {
                                "type": "param_row",
                                "row": 5,
                                "param": "attack",
                                "text": "ATTACK",
                            },
                            {
                                "type": "param_row",
                                "row": 6,
                                "param": "release",
                                "text": "RELEASE",
                            },
                        ],
                    }
                ],
                "bindings": [
                    {"source": "ENC_KNOB1", "slot": 0, "behavior": "relative"},
                    {"source": "ENC_KNOB2", "slot": 1, "behavior": "relative"},
                    {"source": "ENC_KNOB3", "slot": 2, "behavior": "relative"},
                    {"source": "ENC_KNOB4", "slot": 3, "behavior": "relative"},
                ],
            }
        },
    }


_SYNTH_APP_C = """/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* {name}'s app half of the frozen contract: the minimal glue between the generated
 * engine (dsp.h / glue.h), the generated panel, the platform, and the framework's
 * synth services. Included by src/rib.c in `umetate build --synth <dir>`.
 * Extend this file (and patch.json / panel.json) to shape the instrument.
 * The preset save/load/init/name flow and the modal popups are the framework's
 * synth_app.c; this file is the control map + the credits page.
 * (No <string.h>: memset/memcpy/memcmp come from the platform's freestanding
 * libc.c, as in every synth — the pi32v2 toolchain has no libc headers.) */
#include "dsp.h"
#include "glue.h"
#include "cc_map.h"
#include "synth_layout.h"
#include "panel.h"
#include "presets.h"
#include "synth_midi.h"
#include "synth_sysex.h"
#include "synth_runtime.h"
#include "synth_app.h"

/* the preset store's writable memory (flash = persistence; RAM = the working copy
 * reloaded each boot; .pool is the big-buffer region). */
static uint8_t part_bank[PP_BANK(SYNTH_N_PARAMS)] __attribute__((section(".pool")));
static uint8_t multi_bank[MP_BANK(SYNTH_N_PARTS)] __attribute__((section(".pool")));
static uint8_t settings[ST_RECORD];

/* the shared app core: the preset banks + the generated seam, driven by the UI's
 * SAVE/INIT/name/browser actions (synth_app.c). */
static synth_app_ctx app;

/* the engine seam -> the framework services (the transport is generated glue). */
static synth_midi_ctx midi_ctx = {
    {name}_glue_note_on_ch, {name}_glue_note_off, {name}_glue_all_off,
    {name}_glue_set_param, {name}_glue_bend,
    cc_to_param, param_min, param_max,
};
static synth_sysex_ctx sysex_ctx = {
    SYNTH_MODEL, SYNTH_N_PARAMS, SYNTH_N_PARTS, {name}_glue_get_param,
    part_bank, multi_bank, settings,
};

/* the generated init table, read through a callback (no type-punning) */
static void {name}_get_init(uint32_t i, uint16_t *id, int32_t *value)
{
    *id = {name}_init[i].id;
    *value = {name}_init[i].value;
}

/* the app's action hooks (called by ui.c); the generic bodies are synth_app_* */
void ui_act_note_on(uint8_t note, uint8_t vel) { {name}_glue_note_on(note, vel); }
void ui_act_note_off(uint8_t note) { {name}_glue_note_off(note); }
void ui_act_set_step(uint8_t step) { (void)step; }
void ui_act_panic(void) { {name}_glue_all_off(); }
void ui_act_play(void) { }
void ui_act_stop(void) { }
void ui_act_save(void) { synth_app_save(&app); }
void ui_act_init_patch(void) { synth_app_init_patch(&app); }
void ui_act_init_part(void) { synth_app_init_part(&app); }
void ui_act_name(uint8_t which) { ui_name_editor_begin(which); }
void ui_draw_custom(const ui_widget *w) { (void)w; }
void ui_save_slot_name(uint8_t kind, uint16_t slot, char *out, uint32_t cap)
{
    synth_app_slot_name(&app, kind, slot, out, cap);
}
void ui_preset_apply(uint8_t kind, uint16_t slot) { synth_app_apply(&app, kind, slot); }

/* MIDI in: from the main loop, and from app_idle while the screen draws. */
static uint32_t idle_ok;
static void app_idle(void)
{
    if (idle_ok) synth_midi_poll(&midi_ctx);
}

/* the main loop, split for the browser emulator: app_init (setup) + app_step (one
 * millisecond). app_main keeps the frozen contract for the host/target builds. */
#define KEY0 53u  /* key 0 = F3 */
static uint32_t app_prev, app_lit;
static uint8_t app_held[27];
static int32_t app_oct;
static int32_t last_ui[UI_PARAM_MAX];

/* the panel <-> engine mirror: the engine owns the truth. */
static void ui_sync(void)
{
    int32_t *v = ui_params();
    uint32_t i;
    for (i = 0; i < PANEL.n_params; i++) {
        int32_t e = {name}_glue_get_param(i);
        if (v[i] != e) {
            if (last_ui[i] != v[i]) {
                {name}_glue_set_param(i, v[i]);
                e = {name}_glue_get_param(i);
            }
            v[i] = e;
        }
        last_ui[i] = v[i];
    }
}

static void app_init(void)
{
    app_prev = 0;
    app_lit = 0;
    memset(app_held, 0, sizeof app_held);
    app_oct = 0;
    {name}_glue_reset();
#if FM1_CPU1_USED
    {
        fm1_guard_unlock_top();
        fm1_guard_pc_open();
        (void)fm1_cpu1_start();
        fm1_guard_enable(FM1_GUARD_PC);
        fm1_guard_lock_top();
    }
    lit_base = KEY0;
#endif
    app.get_param = {name}_glue_get_param;
    app.set_param = {name}_glue_set_param;
    app.reset = {name}_glue_reset;
    app.n_params = SYNTH_N_PARAMS;
    app.n_parts = SYNTH_N_PARTS;
    app.routing_base = SYNTH_ROUTING_BASE;
    app.get_init = {name}_get_init;
    app.init_n = {name}_INIT_N;
    app.part_bank = part_bank;
    app.multi_bank = multi_bank;
    app.settings = settings;
    ui_init(&PANEL);
    synth_app_boot(&app);
    ui_sync();
}

static void app_step(void)
{
    uint32_t keys, down, up, b, rel, base, k, input_seen;
    int32_t e;

    platform_poll();

    keys = fm1_in.notes;
    down = keys & ~app_prev;
    up = app_prev & ~keys;
    app_prev = keys;
    input_seen = down | up;
    base = (uint32_t)((int32_t)KEY0 + 12 * app_oct);
    if (synth_app_step(&app)) {
        /* a modal popup consumed the control this step (synth_app drained it) */
    } else {
        for (k = 0; k < 27u; k++) {
            uint32_t note = base + k;
            if (down >> k & 1u) {
                app_held[k] = (uint8_t)note;
                ui_handle(UI_SRC_KEY, note);
            }
            if (up >> k & 1u && app_held[k]) {
                ui_act_note_off(app_held[k]);
                app_held[k] = 0u;
            }
        }

        b = fm1_input_edges(&rel);
        if (b & (1u << BTN_HOME)) ui_handle(UI_SRC_BTN_HOME, -1);
        if (b & (1u << BTN_OCT_DOWN)) app_oct = app_oct > -2 ? app_oct - 1 : app_oct;
        if (b & (1u << BTN_OCT_UP)) app_oct = app_oct < 2 ? app_oct + 1 : app_oct;
        input_seen |= b;
    }

    if (ui_popup_active()) {
        /* a modal popup captures all control: drain the page encoders so a twist
           during the popup doesn't fire on the page once it closes. */
        fm1_enc_take(ENC_KNOB1);
        fm1_enc_take(ENC_KNOB2);
        fm1_enc_take(ENC_KNOB3);
        fm1_enc_take(ENC_KNOB4);
        fm1_enc_take(ENC_PRESETS);
    } else {
        if ((e = fm1_enc_take(ENC_KNOB1)) != 0) {
            input_seen = 1;
            ui_handle(UI_SRC_ENC_KNOB1, e);
        }
        if ((e = fm1_enc_take(ENC_KNOB2)) != 0) {
            input_seen = 1;
            ui_handle(UI_SRC_ENC_KNOB2, e);
        }
        if ((e = fm1_enc_take(ENC_KNOB3)) != 0) {
            input_seen = 1;
            ui_handle(UI_SRC_ENC_KNOB3, e);
        }
        if ((e = fm1_enc_take(ENC_KNOB4)) != 0) {
            input_seen = 1;
            ui_handle(UI_SRC_ENC_KNOB4, e);
        }
    }
    {
        int32_t pe = fm1_enc_take(ENC_PRESETS);
        if (pe != 0)
            synth_app_input(&app);
        synth_app_browser_step(&app, pe, fm1_ms, 0u);
    }
    if (input_seen)
        synth_app_input(&app);

    synth_midi_poll(&midi_ctx);
    synth_sysex_poll(&sysex_ctx);
    ui_sync();
    synth_app_tick(&app, fm1_ms, (uint8_t){name}_glue_quiet());

#if FM1_CPU1_USED
    lit_base = base;
    app_lit = dsp_status.lit;
#else
    app_lit = {name}_glue_lit(base);
#endif
    for (k = 0; k < 27u; k++)
        fm1_led_key(KEY_LED(k), app_lit >> k & 1u);
    fm1_led_key(BTN_OCT_DOWN, app_oct < 0);
    fm1_led_key(BTN_OCT_UP, app_oct > 0);

    idle_ok = 1;
    ui_redraw(fm1_ms);
    idle_ok = 0;
}

static void app_main(void)
{
    app_init();
    for (;;)
        app_step();
}
"""


def _synth(name: str, out: Path) -> int:
    """Write a complete minimal firmware (patch.json + panel.json + app.c)."""
    patch = _minimal_synth_patch(name)
    panel = _minimal_synth_panel(name)
    _write(out, "patch.json", patch)
    _write(out, "panel.json", panel)
    cname = to_c_identifier(name)
    (out / "app.c").write_text(_SYNTH_APP_C.replace("{name}", cname), encoding="utf-8")
    # verify the patch generates + compiles, and the panel resolves against it.
    if not _builds(patch):
        print("scaffold: the generated patch does not build", file=sys.stderr)
        return 1
    try:
        generate_panel(panel, param_ids(patch), param_meta(patch))
    except Exception as exc:  # noqa: BLE001 - a broken scaffold is a scaffold bug
        print(f"scaffold: the generated panel does not resolve: {exc}", file=sys.stderr)
        return 1
    print(
        f"scaffolded synth {out / 'patch.json'} (+ panel.json + app.c); "
        "run `umetate build --synth <dir>` for sound"
    )
    return 0


def _builds(patch: Patch) -> bool:
    """Does the patch generate + compile on the host? True when a local `cc` is
    absent (the check is a host-toolchain nicety, not a gate) — e.g. Windows
    without WSL, where the Docker image holds the toolchain instead."""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src, encoding="utf-8")
        try:
            proc = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-I",
                    str(_FW / "hal"),
                    "-I",
                    str(_FW / "gen"),
                    "-c",
                    "-o",
                    str(d / "dsp.o"),
                    str(d / "dsp.c"),
                ],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return True
        return proc.returncode == 0


def _node(name: str, out: Path) -> int:
    _write(
        out,
        "node.json",
        {
            "name": name,
            "summary": "",
            "ins": {"in": "audio"},
            "outs": {"audio": "audio"},
            "params": {},
            "state": {},
        },
    )
    (out / "node.c").write_text(_NODE_C, encoding="utf-8")
    print(f"scaffolded node {out / 'node.json'} (+ node.c)")
    return 0


def _macro(name: str, out: Path) -> int:
    _write(
        out,
        "macro.json",
        {
            "name": name,
            "ins": {},
            "outs": {},
            "params": {},
            "nodes": [],
            "wires": [],
        },
    )
    print(f"scaffolded macro {out / 'macro.json'}")
    return 0


def _patch(name: str, out: Path, template: str | None) -> int:
    if template:
        src = _EXAMPLES / template
        if not (src / "patch.json").exists():
            print(
                f"scaffold: no template {template!r} (looked in {src})",
                file=sys.stderr,
            )
            return 2
        patch = as_patch(json.loads((src / "patch.json").read_text(encoding="utf-8")))
        panel = as_panel(json.loads((src / "panel.json").read_text(encoding="utf-8")))
        patch["name"] = name
        panel["name"] = name
    else:
        patch = _minimal_patch(name)
        panel = _minimal_panel(name)

    _write(out, "patch.json", patch)
    _write(out, "panel.json", panel)
    if _builds(patch):
        print(f"scaffolded patch {out / 'patch.json'} (+ panel.json); it builds")
        return 0
    print("scaffold: the generated patch does not build", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate scaffold", description=__doc__)
    parser.add_argument("kind", choices=("node", "macro", "patch", "synth"))
    parser.add_argument("--name", required=True, help="the node/macro/patch/synth name")
    parser.add_argument("--template", help="a shipped example to copy (patch only)")
    parser.add_argument("--out", type=Path, help="output dir (default: ./<name>)")
    args = parser.parse_args(argv)

    name = str(args.name)
    out: Path = args.out or Path(name)
    template: str | None = args.template
    if args.kind == "node":
        return _node(name, out)
    if args.kind == "macro":
        return _macro(name, out)
    if args.kind == "synth":
        return _synth(name, out)
    return _patch(name, out, template)


if __name__ == "__main__":
    sys.exit(main())
