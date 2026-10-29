# Control map (UI plan) — fourop-fm

> The UI interview, translated into `panel.json`. The control surface is the
> **real M-VAVE FM-1** (not an idealized one): a smooth `MASTER` volume pot, three
> dedicated left encoders (`SELECT`/`ALGORITHM`/`PRESETS`), four page-slot encoders
> (`KNOB1–4`), fourteen buttons, and a 27-key keybed. The operator editor uses a
> **page-slot** model: `KNOB1–4` edit the four on-screen params, `SELECT` cycles
> sub-pages, `SEL` selects the operator.

## 1. Surface inventory

- **Board / revision:** FM-1 (`--board fm1`).
- **Controls and their kinds:** 27 keys (momentary note, F3–G5); `MASTER` = a
  smooth analog pot (volume, platform-owned — never a page slot); `SELECT`,
  `ALGORITHM`, `PRESETS`, `KNOB1–4` = detented encoders; `OCT− OCT+ FX SEL ENV LFO
  EDIT GLO HOME SAVE ARP SEQ PLAY REC` = momentary buttons.
- **Knob kinds:** dedicated (`ALGORITHM`, `PRESETS`) vs page-slot (`KNOB1–4`);
  `MASTER` is volume.
- **Silkscreen labels:** `ALGORITHM`, `PRESETS`, `ENV`, `LFO`, `FX`, `GLO`, `EDIT`,
  `HOME`, `SAVE`, `SEL`, `OCT−/OCT+` — the firmware means what they say.
- **Display / fonts / LEDs available:** 240×240 LCD; the abstract widget set
  (`label`, `value`, `bar`, `param_row`, `param_column`, `list`, `grid`, the
  op-relative `op_row`, the `envelope` graph, and the `status` readout); per-key
  and per-button LEDs.
- **Controls explicitly unmapped (and why):** `MASTER` (platform volume);
  `PRESETS` (the 32+32 preset store is reached via SysEx and the boot-time
  multi-slot apply, not yet bound to the encoder); `SAVE` (writes part 0's
  timbre to part-patch slot 0 via `ui_act_save` — no panel binding yet);
  `OCT−/OCT+` (octave is firmware-level, not a patch param); `ARP SEQ PLAY REC`
  (no sequencer/transport).

## 2. Player model

- **Performance gesture:** one hand on keys, one on `KNOB1–4` (the page params);
  `ALGORITHM` is the always-on headline control.
- **Menu depth tolerance:** four contexts, one `push`/`pop_home` (depth 2).
- **Keys as shortcuts:** in `EDIT`, the operator is selected with `SEL` (the keys
  doubling as operator/mute shortcuts is the device-level idiom, outside the
  patch).
- **What must stay playable during any interaction:** held notes — redraw is
  rate-bounded, never in the audio callback.

## 3. Contexts (modes) and their bindings

### Always-on (global, resolved last)

| Source | Target / action | Behavior | Note |
| --- | --- | --- | --- |
| KEY | note_on | | keys play notes |
| ENC_ALGORITHM | algorithm | relative | the headline control |
| BTN_EDIT | push `op` | | enter the operator editor |
| BTN_FX | push `fx` | | the output chain |
| BTN_GLO | push `glo` | | the global modulation |
| BTN_HOME | pop_home | | back home |

### Context: `home`

- **Pages:** `main` — `status` (ALG n) + `param_row`s for the four perform knobs
  `cutoff · res · fold · feedback`.
- **Bindings:** ENC_KNOB1–4 → `slot` 0–3.

### Context: `op` (the operator editor)

| Sub-page (`SELECT` cycles) | the 4 params (slots 0–3) |
| --- | --- |
| pitch | ratio · level · feedback · waveform |
| env-rates | r1 (attack) · r2 (decay1) · r3 (decay2) · r4 (release) |
| env-levels | l1 · l2 · l3 · (—) |
| trem | trem_rate · trem_depth · (—) · (—) |
| mute | op1_mute · op2_mute · op3_mute · op4_mute |

- **Bindings:** ENC_KNOB1–4 → `slot` 0–3; ENC_SELECT → `next_page`; BTN_SEL →
  `op_next` (select operator 1 → 2 → 3 → 4).
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

- **Pages:** `fx` — `cutoff · res · fold`.
- **Bindings:** ENC_KNOB1–4 → `slot` 0–3.

### Context: `glo` (the global modulation)

- **Pages:** `mod` — `pitch_rate · pitch_depth · penv_base · penv_rate` (vibrato +
  the pitch envelope).
- **Bindings:** ENC_KNOB1–4 → `slot` 0–3.

## 4. Global bindings (always-on, resolved last)

See §3 "Always-on" — the encoders/buttons that resolve before any context.

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

- **Context transitions:** boot → `home`; `BTN_EDIT` pushes `op`; `BTN_FX` pushes
  `fx`; `BTN_GLO` pushes `glo`; `BTN_HOME` pops home.
- **The full context stack, worst case:** `[home, op]` — depth 2.
- **The selected operator** is a flat 0..3 counter (`op_next`), shared across
  contexts; the `mute` page toggles `opN_mute` directly.
- **Per-control meaning:** `ALGORITHM` is always the algorithm; `KNOB1–4` are the
  current page's four params; `SELECT` cycles sub-pages (in `op`); `SEL` cycles
  the operator.
- **Unresolved / ambiguous bindings:** none.

## 9. Acceptance

- **Host UI tests:** `test_generate.py` resolves `panel.json` against the patch's
  `param_ids`; the generated `panel.h` compiles against `ui.h`.
- **Device checks:** held notes during redraw; visible safe-failure screen —
  `blocked` (device ~10 days out).
