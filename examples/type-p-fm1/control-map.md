# Control map (UI plan), type-p-fm1

> The UI interview, translated into `panel.json`. The control surface is the
> **real M-VAVE FM-1** (not an idealized one): a smooth `MASTER` volume pot, three
> dedicated left encoders (`SELECT`/`ALGORITHM`/`PRESETS`), four page-slot encoders
> (`KNOB1–4`), fourteen buttons, and a 27-key keybed. The operator editor uses a
> **page-slot** model: `KNOB1–4` edit the four on-screen params, `SELECT` cycles
> sub-pages, `SEL` selects the operator.

## 1. Surface inventory

- **Board / revision:** FM-1 (`--board fm1`).
- **Controls and their kinds:** 27 keys (momentary note, F3–G5). `MASTER` = a
  smooth analog pot (volume, platform-owned, never a page slot). `SELECT`,
  `ALGORITHM`, `PRESETS`, `KNOB1–4` = detented encoders. `OCT− OCT+ FX SEL ENV LFO
  EDIT GLO HOME SAVE ARP SEQ PLAY REC` = momentary buttons.
- **Knob kinds:** dedicated (`ALGORITHM`, `PRESETS`) vs page-slot (`KNOB1–4`).
  `MASTER` is volume.
- **Silkscreen labels:** `ALGORITHM`, `PRESETS`, `ENV`, `LFO`, `FX`, `GLO`, `EDIT`,
  `HOME`, `SAVE`, `SEL`, `OCT−/OCT+`, the firmware means what they say.
- **Display / fonts / LEDs available:** 240×240 LCD. The abstract widget set
  (`label`, `value`, `bar`, `param_row`, `param_column`, `list`, `grid`, the
  op-relative `op_row`, the `envelope` graph, and the `status` readout). Per-key
  and per-button LEDs.
- **Controls explicitly unmapped (and why):** `MASTER` (platform volume).
  `PRESETS` (the 128+64 preset store is reached via the browser encoder, SysEx,
  and the boot-time multi-slot apply). `SAVE` (opens the save chooser, single
  part / multi-patch + slot, not a direct param write). `ARP SEQ PLAY REC`
  (no sequencer/transport).
- **Firmware-level controls (app glue, not panel params):** `OCT−`/`OCT+` shift
  the keybed base note a whole octave (`lit_base`, clamped ±2) in `app.c`.

## 2. Player model

- **Performance gesture:** one hand on keys, one on `KNOB1–4` (the page params).
  `ALGORITHM` is the always-on headline control.
- **Menu depth tolerance:** four contexts, one `switch`/`pop_home` (depth 2, the
  three modes are siblings, not a stack).
- **Keys as shortcuts:** in `EDIT`, the operator is selected with `SEL` (the keys
  doubling as operator/mute shortcuts is the device-level idiom, outside the
  patch).
- **What must stay playable during any interaction:** held notes, redraw is
  rate-bounded, never in the audio callback.

## 3. Contexts (modes) and their bindings

### Always-on (global, resolved last)

| Source | Target / action | Behavior | Note |
| --- | --- | --- | --- |
| KEY | note_on | | keys play notes |
| ENC_ALGORITHM | algorithm | relative | the headline control |
| BTN_EDIT | switch `op` | | enter the operator editor |
| BTN_FX | switch `fx` | | the output chain |
| BTN_GLO | switch `glo` | | the global modulation |
| BTN_HOME | pop_home | | back home |

### Context: `home`

- **Pages:** `main`, `status` (ALG n) + `param_row`s for the four perform knobs
  `cutoff · res · fold · feedback`.
- **Bindings:** ENC_KNOB1–4 → `slot` 0–3.

### Context: `op` (the operator editor)

| Sub-page (`SELECT` cycles) | the 4 params (slots 0–3) |
| --- | --- |
| pitch | ratio · level · feedback · waveform |
| env-rates | r1 (attack) · r2 (decay1) · r3 (decay2) · r4 (release) |
| env-levels | l1 · l2 · l3 · (, ) |
| trem | trem_rate · trem_depth · (, ) · (, ) |
| mute | op1_mute · op2_mute · op3_mute · op4_mute |

- **Bindings:** ENC_KNOB1–4 → `slot` 0–3. ENC_SELECT → `next_page`. BTN_SEL →
  `op_next` (select operator 1 → 2 → 3 → 4 → 1, wrapping).
- Each sub-page opens with a `status` readout (`ALG <n> · OP <n>/4 · MUTE`), so
  the algorithm, selected operator, and its mute state stay visible while
  editing.
- The pages are **operator-relative** (`operators: [op1..op4]`): each widget's
  `op1.<param>` resolves through the selected operator (`op_row`). The
  `envelope` widget declares its 7 params explicitly (`r1..r4, l1..l3`) and
  draws the selected operator's curve.
- **Mute** is a sub-page: the four knobs toggle op1–4 directly (no long-press
  primitive needed).

### Context: `fx` (the output chain)

- **Pages:** `fx`, `cutoff · res · fold`.
- **Bindings:** ENC_KNOB1–4 → `slot` 0–3.

### Context: `glo` (the global modulation)

- **Pages:** `mod`, `pitch_rate · pitch_depth` (vibrato). `env`, `p-env-rates`
  (`penv_on · penv_r1 · penv_r2 · penv_r3`) + `p-env-levels`
  (`penv_r4 · penv_l1 · penv_l2 · penv_l3`), the per-note pitch envelope.
- **Bindings:** ENC_KNOB1–4 → `slot` 0–3.

## 4. Global bindings (always-on, resolved last)

See §3 "Always-on", the encoders/buttons that resolve before any context.

## 5. Display pages

| Context / page | Widgets | Update rule |
| --- | --- | --- |
| home / main | `status` + 4 `param_row` | redraw on change, ~30 Hz |
| op / pitch | `status` + 4 `op_row` | redraw on change, ~30 Hz |
| op / env-rates | `status` + 4 `op_row` + `envelope` | redraw on change, ~30 Hz |
| op / env-levels | `status` + 3 `op_row` + `envelope` | redraw on change, ~30 Hz |
| op / trem | `status` + 2 `op_row` | redraw on change, ~30 Hz |
| op / mute | `status` + 4 `param_row` | redraw on change, ~30 Hz |
| fx / fx | label + 3 `param_row` | redraw on change, ~30 Hz |
| glo / mod | label + 4 `param_row` | redraw on change, ~30 Hz |

## 6. LED / pad feedback

- `OCT−`/`OCT+` lit when shifted below/above zero (firmware-level, reserved here).
- The selected operator's key glows in `EDIT` (device-level).
- Sounding keys light.

## 7. Boot screen

- **Needed?** No.

## 8. Control flow (the state machine)

- **Context transitions:** boot → `home`. `BTN_EDIT` switches to `op`. `BTN_FX`
  switches to `fx`. `BTN_GLO` switches to `glo`. `BTN_HOME` pops home. Switching
  replaces the current mode (they are siblings), so `fx` → `EDIT` goes straight to
  the operator editor.
- **The full context stack, worst case:** `[home, op]`, depth 2.
- **The selected operator** is a flat 0..3 counter (`op_next`), shared across
  contexts. The `mute` page toggles `opN_mute` directly.
- **Per-control meaning:** `ALGORITHM` is always the algorithm. `KNOB1–4` are the
  current page's four params. `SELECT` cycles sub-pages (in `op`). `SEL` cycles
  the operator.
- **Unresolved / ambiguous bindings:** none.

## 9. Acceptance

- **Host UI tests:** `test_generate.py` resolves `panel.json` against the patch's
  `param_ids`. The generated `panel.h` compiles against `ui.h`.
- **Device checks:** held notes during redraw. Visible safe-failure screen,
  `blocked` (device ~10 days out).
