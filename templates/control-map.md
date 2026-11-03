# Control map (UI plan)

> Fill this in during the UI interview. It becomes the `panel.json`. Delete
> rejected options. One control map per project. The voice architecture and
> parameter manifest (in `synth-brief.md`) are upstream of this: bind only
> parameters that exist there.

## 1. Surface inventory

- **Board / revision:**
- **Controls and their kinds** (momentary / latch / absolute / relative / pot / pad / fader / wheel / key / MIDI):
- **Knob kinds** (smooth analog pot = volume vs detented encoder = parameter. Dedicated knob vs page-slot knob):
- **Silkscreen labels** (the printed name of each control, a fixed constraint the design must respect):
- **Display / fonts / LEDs available:**
- **Controls explicitly unmapped (and why):**

## 2. Player model

- **Performance gesture** (one hand on keys, one on …):
- **Menu depth tolerance:**
- **Keys as shortcuts** (does the keybed double as a menu surface, operator select, mute?):
- **What must stay playable during any interaction** (held notes, transport):

## 3. Contexts (modes) and their bindings

> A context owns both its view and its control meaning. For **each** context,
> fill a table like the one below, one row per control/MIDI source that does
> something here, and a row for every on-enter/on-exit side effect.
>
> First draw the **menu tree**, every context (menu), its pages, and the *modes*
> within a page (a page whose widgets change under a hold/shift, or a multi-mode
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

## 6. LED / pad feedback

| State | LED / pad | Meaning |
| --- | --- | --- |

## 7. Boot screen

- **Needed?** (only if boot is slow)
- **Content:**

## 8. Control flow (the state machine)

> A fresh reader must trace every control through every context with no
> ambiguity. Enumerate the transitions explicitly.

- **Context transitions:** who pushes/pops what, and to where (`push` / `pop` /
  `pop_home` / `set_page` / `next_page` / `prev_page` / `bank_next` / `bank_prev`):
- **The full context stack, worst case** (how deep, and the unwind):
- **Per-control meaning across contexts** (the same knob/button in every context):
- **Unresolved / ambiguous bindings** (none is the goal):

## 9. Acceptance

- **Host UI tests (scripted keys/knobs/screen captures):**
- **Device checks (held notes during redraw, visible failure state):**
