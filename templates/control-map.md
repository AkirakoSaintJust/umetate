# Control map (UI plan)

> Fill this in during the UI interview; it becomes the `panel.json`. Delete
> rejected options. One control map per project.

## 1. Surface inventory

- **Board / revision:**
- **Controls and their kinds** (momentary / latch / absolute / relative / pot / pad / fader / wheel / key / MIDI):
- **Display / fonts / LEDs available:**

## 2. Player model

- **Performance gesture** (one hand on keys, one on …):
- **Menu depth tolerance:**
- **What must stay playable during any interaction** (held notes, transport):

## 3. Contexts (modes)

| Context | Entered by | Pages | Key bindings (what changes here) | on-enter / on-exit |
| --- | --- | --- | --- | --- |
| home | boot | | keys = notes | |
| | | | | |

## 4. Global bindings (always-on)

| Source | Target / action | Behavior / curve |
| --- | --- | --- |
| MASTER | master.volume | absolute |

## 5. Display pages

| Page | Widgets | Update rule |
| --- | --- | --- |

## 6. LED / pad feedback

| State | LED / pad | Meaning |
| --- | --- | --- |

## 7. Boot screen

- **Needed?** (only if boot is slow)
- **Content:**

## 8. Navigation

- **Page → page, context → context, and the combos:**

## 9. Acceptance

- **Host UI tests (scripted keys/knobs/screen captures):**
- **Device checks (held notes during redraw, visible failure state):**
