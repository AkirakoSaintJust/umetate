# Control map (UI plan)

> Fill this in during the UI interview, and it becomes `panel.json`. Delete the
> options you reject. One control map per project. The voice architecture and
> parameter manifest in `synth-brief.md` are upstream, so bind only parameters that
> exist there.
>
> **Do not author the panel until every section below is filled.** The ten-item
> minimum bar is in `skills/umetate-development/SKILL.md` §2, the reasoning and
> design-language reference are in
> `skills/umetate-development/references/ui-design.md`, and the casebook is
> `ui-dossier.md`.

## 1. Surface inventory

- **Board / revision:**
- **Controls and their kinds** (momentary / latch / absolute / relative / pot / pad / fader / wheel / key / MIDI):
- **Knob kinds** (smooth analogue pot = volume vs detented encoder = parameter. Dedicated knob vs page-slot knob):
- **Silkscreen labels** (the printed name of each control, a fixed constraint the design must respect):
- **Display / fonts / LEDs available:**
- **Controls explicitly unmapped (and why):**

## 2. Player model

- **Performance gesture** (one hand on keys, one on …):
- **Menu depth tolerance:**
- **Keys as shortcuts** (does the keybed double as a menu surface, operator select, mute?):
- **What must stay playable during any interaction** (held notes, transport):

## 3. Contexts (modes) and their bindings

> A context owns both its view and its control meaning. For **each** context, fill
> a table like the one below with one row per control or MIDI source that does
> something here, and a row for every on-enter or on-exit side effect.
>
> First draw the **menu tree**, every context (menu), its pages, and the *modes*
> within a page (a page whose widgets change under a hold or shift, or a multi-mode
> page). A fresh reader must be able to draw the screen for every state from this
> section alone.

### Context: `home`

| Source | Target param / action | Behavior / curve | Note |
| --- | --- | --- | --- |
| KEY | note_on | | keys play notes |
| MASTER | master.volume | absolute | global fallthrough |
| | | | |

- **Pages:** (list page ids + their widgets)
- **on-enter:** **on-exit:**

### Context: `___` (add one block per context)

| Source | Target param / action | Behavior / curve | Note |
| --- | --- | --- | --- |

- **Pages:** **on-enter:** **on-exit:**

## 4. Global bindings (always-on, resolved last)

| Source | Target / action | Behavior / curve |
| --- | --- | --- |
| MASTER | master.volume | absolute |
| | | |

## 5. Display pages

| Page | Widgets | Update rule |
| --- | --- | --- |

### 5a. Always-visible header

- **Fields shown on every page** (part, operator, mute state, algorithm, menu,
  page N/M, and anything else that must never hide):
- **Where each field sits** (the header must not reflow between pages):

### 5b. Parameter specification

One row per editable parameter. The range, unit, and curve are the same ones the
stepper and the display use. A value is clamped to this range, so the display and
the value never disagree.

| Param | Display form | User range | Unit | Step / curve | Default | Owner page |
| --- | --- | --- | --- | --- | --- | --- |

### 5c. INIT PATCH and INIT PART

- **INIT PATCH, exact values** (every parameter, not "same as ..."):
- **INIT PART, exact values:**
- **What stays from the previous patch, if anything:**

### 5d. Screen rules

- **Redraw model and rate:**
- **Work kept out of the audio callback:**
- **Page or menu change clear:**
- **Held notes during redraw:**
- **Failure or boot screen:**

## 6. LED / pad feedback

| State | LED / pad | Meaning |
| --- | --- | --- |

## 7. Boot screen

- **Needed?** (only if boot is slow)
- **Content:**

## 8. Control flow (the state machine)

> A fresh reader must be able to trace every control through every context without
> ambiguity, so enumerate the transitions explicitly.

- **Context transitions:** who pushes/pops what, and to where (`push` / `pop` /
  `pop_home` / `set_page` / `next_page` / `prev_page` / `bank_next` / `bank_prev`):
- **The full context stack, worst case** (how deep, and the unwind):
- **Per-control meaning across contexts** (the same knob/button in every context):
- **Unresolved / ambiguous bindings** (none is the goal):

## 8a. Design language

- **Colour roles** (one meaning per colour, no decorative hue):
- **Type** (families, sizes, case, where each is used):
- **Grid and metrics** (padding, gaps, control cells, fixed frame):
- **State language** (active, muted, selected, focus, hover, disabled):
- **Signal language** (scope, spectrum, envelopes, level fills, routing):
- **Copy rules** (case, labels, value formats, name limits):
- **Token source** (the one file the web, plugin, and firmware generate from):

## 9. Acceptance

- **The ten-item gate is filled** (SKILL.md §2, no item left as "TBD"):
- **Screen mockup** (file + URL, every page reviewed at 3x):
- **Host UI tests (scripted keys/knobs/screen captures):**
- **Device checks (held notes during redraw, visible failure state):**
- **The mockup and the generated theme agree** (same tokens, same layout):
- **A stranger can make a sound and find save without help:**
