# Control map (UI plan) — fourop-fm

> The UI interview, translated into `panel.json`. One context owns both its view
> and its control meaning; bindings name only parameters from `synth-brief.md`
> §2.2.

## 1. Surface inventory

- **Board / revision:** FM-1 (SMK-37 class): keys, ENC_KNOB1–7, ENC_SELECT,
  ENC_PRESETS, BTN_OCT_DOWN/UP, BTN_EDIT, BTN_HOME, BTN_PLAY/STOP/REC/SAVE/SEQ,
  FM1_ADC_MASTER.
- **Controls and their kinds:** keys = momentary note; encoders = relative
  (param); BTN_EDIT/HOME = momentary navigation; MASTER = absolute pot.
- **Display / fonts / LEDs available:** 240×240 LCD; the abstract widget set
  (`label`, `value`, `bar`, `param_row`, `param_column`, `list`, `grid`).
- **Controls explicitly unmapped (and why):** BTN_PLAY/STOP/REC/SAVE/SEQ,
  ENC_PRESETS, BTN_OCT_DOWN/UP, FM1_ADC_MASTER — no sequencer, patches, octave
  shift, or master volume in this dogfood.

## 2. Player model

- **Performance gesture:** one hand on keys, one on ENC_KNOB1 (algorithm).
- **Menu depth tolerance:** two contexts, no nesting beyond `push`/`pop_home`.
- **What must stay playable during any interaction:** held notes — redraw is
  rate-bounded, never in the audio callback.

## 3. Contexts (modes) and their bindings

### Context: `home`

| Source | Target param / action | Behavior / curve | Note |
| --- | --- | --- | --- |
| KEY | note_on | | keys play notes (global) |
| ENC_KNOB1 | algorithm | relative | the headline control |
| ENC_KNOB2 | cutoff | relative | filter cutoff (log) |
| ENC_KNOB3 | res | relative | filter damping |
| ENC_KNOB4 | fold | relative | wavefolder depth |
| ENC_KNOB5 | master | relative | output level |
| ENC_KNOB6 | feedback | relative | op1 self-modulation |
| ENC_KNOB7 | attack | relative | op1 envelope attack |
| ENC_SELECT | release | relative | op1 envelope release |
| BTN_EDIT | push `op` | | enter operator edit |
| BTN_HOME | pop_home | | (no-op at home) |

- **Pages:** `home` — label "4OP FM", then `param_row`s for algorithm/cutoff/res/
  fold/master/feedback/attack/release.
- **on-enter:** — **on-exit:** —

### Context: `op`

| Source | Target param / action | Behavior / curve | Note |
| --- | --- | --- | --- |
| ENC_KNOB1 | op1_level | relative | |
| ENC_KNOB2 | op1_waveform | relative | 0–7 |
| ENC_KNOB3 | op2_level | relative | |
| ENC_KNOB4 | op2_waveform | relative | |
| ENC_KNOB5 | op3_level | relative | |
| ENC_KNOB6 | op3_waveform | relative | |
| ENC_KNOB7 | op4_level | relative | |
| ENC_SELECT | op4_waveform | relative | |
| BTN_HOME | pop_home | | back to home |

- **Pages:** `op` — label "OPERATORS", then `param_row`s for op1–4 level/waveform.
- **on-enter:** — **on-exit:** —

## 4. Global bindings (always-on, resolved last)

| Source | Target / action | Behavior / curve |
| --- | --- | --- |
| KEY | note_on | |
| BTN_EDIT | push `op` | |
| BTN_HOME | pop_home | |

## 5. Display pages

| Page | Widgets | Update rule |
| --- | --- | --- |
| home | label + 8 `param_row` | redraw on change, ~30 Hz |
| op | label + 8 `param_row` | redraw on change, ~30 Hz |

## 6. LED / pad feedback

| State | LED / pad | Meaning |
| --- | --- | --- |

(No LED feedback in this dogfood.)

## 7. Boot screen

- **Needed?** No (boot is fast; no boot screen declared).

## 8. Control flow (the state machine)

- **Context transitions:** boot → `home`; `BTN_EDIT` pushes `op`; `BTN_HOME`
  pops to home (`pop_home`).
- **The full context stack, worst case:** `[home, op]` — depth 2, unwinds via
  `pop_home`.
- **Per-control meaning across contexts:** ENC_KNOB1–7/ENC_SELECT are home params
  in `home` and operator params in `op`; KEY is always note_on; BTN_HOME always
  pops home.
- **Unresolved / ambiguous bindings:** none.

## 9. Acceptance

- **Host UI tests:** `test_generate.py` resolves `panel.json` against the patch's
  `param_ids` (every widget/binding names a real set_param id).
- **Device checks:** held notes during redraw; visible safe-failure screen —
  `blocked` (device ~10 days out).
