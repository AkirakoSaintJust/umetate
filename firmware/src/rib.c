/* SPDX-License-Identifier: GPL-3.0-only */
/* RIB: the frozen framework every umetate firmware composes on. This file provides the
 * platform and the synth services; the *app* is included at the bottom — either the shipped
 * demo (`rib_app.c`: a sine wave on the keys) or a synth project's `app.c` (the
 * `umetate build --synth` composition, `-DUMETATE_SYNTH_APP=1`, resolved from gen/).
 *
 * The app half of the contract (docs/roadmap §6.11.4): the app defines `app_audio` (the
 * audio ISR), `app_main` (the never-returning main loop; must call platform_poll() often),
 * `app_idle` (runs while the screen's DMA draws), the `ui_act_*` hooks and `ui_draw_custom`.
 *
 * The framework half: platform.c (updates, the USB rescue, MIDI in/out, USB audio, keys,
 * knobs, LEDs, the screen, flash storage), the UI kit (ui.c), and the synth services —
 * synth_sysex.c (the SysEx envelope + five commands, fed from usb.c), synth_midi.c (note/
 * CC/sustain/panic/bend), synth_runtime.c (preset apply), over presets.c (the record store).
 * Everything below the app include is done; you should not need to touch this file. */
#include "synth_sysex.h"                       /* before platform.c: usb.c feeds synth_sysex_feed */
#include "synth_midi.h"
#include "synth_runtime.h"
#include "scope.h"
static void app_idle(void);
#define LCD_IDLE app_idle                       /* while the screen's DMA runs: MIDI in (platform.c) */
#include "scope.c"                              /* the scope/spectrogram core (before platform.c: the ISR hooks scope_push) */
#include "platform.c"
#if BOARD_SMK37
#include "smk_wheel.h"
#endif
#include "fm1_ipc.h"
#include "dsp_ipc.c"                            /* the shared dual-core transport (§12.1) */
#include "ui.h"
#include "presets.c"
#include "synth_sysex.c"
#include "synth_midi.c"
#include "synth_runtime.c"

#ifdef UMETATE_SYNTH_APP
#include "app.c"                                /* a synth project's glue (gen/app.c) */
#else
#include "rib_app.c"                            /* the shipped demo app (a sine on the keys) */
#endif

#include "ui.c"
