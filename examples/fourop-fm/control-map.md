# Control map (UI plan) — fourop-fm

> The UI interview, translated into `panel.json`. The operator editor uses a
> **4-param page** model: the rightmost four encoders (`ENC_KNOB4–7`) edit the four
> on-screen params, `ENC_SELECT` cycles sub-pages, buttons navigate, and
> `BTN_OCT_UP`/`BTN_OCT_DOWN` select the operator.

## 1. Surface inventory

- **Board / revision:** FM-1: keys, ENC_KNOB1–7, ENC_SELECT, ENC_PRESETS,
  BTN_OCT_DOWN/UP, BTN_EDIT, BTN_HOME, BTN_PLAY/STOP/REC/SAVE/SEQ, FM1_ADC_MASTER.
- **Controls and their kinds:** keys = momentary note; encoders = relative
  (param); BTN_EDIT/HOME/OCT/STOP = momentary navigation/mute; MASTER = pot.
- **Display / fonts / LEDs available:** 240×240 LCD; the abstract widget set
  (`label`, `value`, `bar`, `param_row`, `param_column`, `list`, `grid`, the
  op-relative `op_row`, the `envelope` graph, and the `status` readout).
- **Controls explicitly unmapped (and why):** BTN_PLAY/REC/SAVE/SEQ,
  ENC_PRESETS, FM1_ADC_MASTER — no sequencer, patches, or master volume here.

## 2. Player model

- **Performance gesture:** one hand on keys, one on ENC_KNOB4–7 (the page params);
  the left three (ENC_KNOB1–3) are always-on algorithm/cutoff/res.
- **Menu depth tolerance:** two contexts, one `push`/`pop_home`.
- **What must stay playable during any interaction:** held notes — redraw is
  rate-bounded, never in the audio callback.

## 3. Contexts (modes) and their bindings

### Always-on (global, resolved last)

| Source | Target / action | Behavior | Note |
| --- | --- | --- | --- |
| KEY | note_on | | keys play notes |
| ENC_KNOB1 | algorithm | relative | the headline control |
| ENC_KNOB2 | cutoff | relative | filter cutoff |
| ENC_KNOB3 | res | relative | filter damping |
| BTN_EDIT | push `op` | | enter the operator editor |
| BTN_HOME | pop_home | | back home |
| BTN_OCT_UP | op_next | | select operator 1 → 2 → 3 → 4 |
| BTN_OCT_DOWN | op_prev | | select operator 4 → 3 → 2 → 1 |
| BTN_STOP | op_mute | | toggle the selected operator's mute |

### Context: `home`

- **Pages:** `main` — label "4OP FM", then `param_row`s for fold / master /
  pitch_rate / pitch_depth; `pitch` — the global pitch envelope (the "pitch
  blip": `penv_base` + `penv_rate`).
- **Bindings:** ENC_KNOB4–7 → `slot` 0–3 (the page's four params); ENC_SELECT →
  `next_page`.

### Context: `op` (the operator editor)

| Sub-page (`ENC_SELECT` cycles) | the 4 params (slots 0–3) |
| --- | --- |
| pitch | ratio · feedback · waveform · level |
| env-rates | r1 (attack) · r2 (decay1) · r3 (decay2) · r4 (release) |
| env-levels | l1 · l2 · l3 · (—) |
| trem | trem_rate · trem_depth · (—) · (—) |

- **Bindings:** ENC_KNOB4–7 → `slot` 0–3; ENC_SELECT → `next_page`.
- Each sub-page opens with a `status` readout (`ALG <n> · OP <n>/4 · MUTE`), so
  the algorithm, selected operator, and its mute state stay visible while
  editing.
- The pages are **operator-relative** (`operators: [op1..op4]`): each widget's
  `op1.<param>` resolves through the selected operator (`op_row`). The
  `envelope` widget declares its 7 params explicitly (`r1..r4, l1..l3`) and
  draws the selected operator's curve.

## 4. Global bindings (always-on, resolved last)

See §3 "Always-on" — the encoders/buttons that resolve before any context.

## 5. Display pages

| Context / page | Widgets | Update rule |
| --- | --- | --- |
| home / main | label + 4 `param_row` | redraw on change, ~30 Hz |
| home / pitch | label + 2 `param_row` | redraw on change, ~30 Hz |
| op / pitch | `status` + 4 `op_row` | redraw on change, ~30 Hz |
| op / env-rates | `status` + 4 `op_row` + `envelope` | redraw on change, ~30 Hz |
| op / env-levels | `status` + 3 `op_row` + `envelope` | redraw on change, ~30 Hz |
| op / trem | `status` + 2 `op_row` | redraw on change, ~30 Hz |

## 6. LED / pad feedback

(No LED feedback in this dogfood.)

## 7. Boot screen

- **Needed?** No.

## 8. Control flow (the state machine)

- **Context transitions:** boot → `home`; `BTN_EDIT` pushes `op`; `BTN_HOME` pops
  home.
- **The full context stack, worst case:** `[home, op]` — depth 2.
- **The selected operator** is a flat 0..3 counter (`op_next`/`op_prev`), shared
  across contexts; `op_mute` toggles `opN_mute` for the selected one.
- **Per-control meaning:** ENC_KNOB1–3 are always algorithm/cutoff/res; ENC_KNOB4–7
  are the current page's four params; ENC_SELECT cycles sub-pages (in `home` and
  `op`); BTN_STOP mutes the selected operator.
- **Unresolved / ambiguous bindings:** none.

## 9. Acceptance

- **Host UI tests:** `test_generate.py` resolves `panel.json` against the patch's
  `param_ids`; the generated `panel.h` compiles against `ui.h`.
- **Device checks:** held notes during redraw; visible safe-failure screen —
  `blocked` (device ~10 days out).
