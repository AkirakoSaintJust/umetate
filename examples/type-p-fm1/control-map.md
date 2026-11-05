# Control map (UI plan), type-p-fm1

> The UI interview, translated into `panel.json`. The control surface is the real
> M-VAVE FM-1: a smooth `MASTER` volume pot, three dedicated left encoders
> (`SELECT`/`ALGORITHM`/`PRESETS`), four page-slot encoders (`KNOB1–4`), fourteen
> buttons, and a 27-key keybed. The editor uses a **page-slot** model: `KNOB1–4`
> edit the four on-screen parameter rows, `SELECT` pages, and `SEL` selects the
> operator.

## 1. Surface inventory

- **Board / revision:** FM-1 (`--board fm1`).
- **Controls and their kinds:** 27 keys (momentary note, F3–G5). `MASTER` is a
  smooth analogue pot (volume, platform-owned, never a page slot). `SELECT`,
  `ALGORITHM`, `PRESETS`, `KNOB1–4` are detented encoders. `OCT− OCT+ FX SEL ENV
  LFO EDIT GLO HOME SAVE ARP SEQ PLAY REC` are momentary buttons.
- **Knob kinds:** dedicated (`ALGORITHM`, `PRESETS`) and page-slot (`KNOB1–4`).
  `MASTER` is volume.
- **Silkscreen labels:** `ALGORITHM`, `PRESETS`, `ENV`, `LFO`, `FX`, `GLO`,
  `EDIT`, `HOME`, `SAVE`, `SEL`, `OCT−/OCT+`. The firmware means what they say.
- **Display / fonts / LEDs available:** 240×240 LCD. The widget set includes
  `label`, `value`, `bar`, `param_row`, `param_column`, `list`, `grid`, `op_row`,
  `part_row`, `envelope`, `genv`, `scope`, `spectro`, `algo`, `name`, `status`,
  and `custom`. Per-key and per-button LEDs.
- **Controls explicitly unmapped:** none. `ARP/SEQ/PLAY/REC` mute operators, and
  with `SEL` they mute parts. `PRESETS` opens the browser. `SAVE` opens the save
  chooser. `ENV` and `LFO` open their own contexts.
- **Firmware-level controls:** `OCT−`/`OCT+` shift the keybed base note a whole
  octave (`app_oct`, clamped ±2) in `app.c`. `MASTER` is platform volume.

## 2. Player model

- **Performance gesture:** one hand on the keys, one on the `ALGORITHM` encoder.
  The four page knobs belong to the page you open.
- **Menu depth tolerance:** six sibling contexts (`home`, `edit`, `env`, `lfo`,
  `fx`, `glo`). The stack is `[home, mode]`, depth 2.
- **Keys as shortcuts:** `SEL` + key mutes the active operator. The keybed does
  not double as a menu surface.
- **What must stay playable during any interaction:** held notes. Redraw is
  rate-bounded and never runs in the audio callback.

## 3. Navigation

- **Context buttons:** `HOME`, `EDIT`, `ENV`, `LFO`, `FX`, `GLO`. A button opens
  its context at page 0. Pressing the same button again advances to the next page,
  wrapping. `SELECT` moves forward and back through the current context.
- **HOME:** pops back to the home context. Pressing `HOME` while already home
  advances to the next home page.
- **Page knobs:** `KNOB1–4` edit the page's parameter rows from top to bottom. A
  page with fewer than four rows leaves the extra knobs idle. Display pages have
  no assignments.
- **Modifier chords:**

| Gesture | Action |
| --- | --- |
| `SEL` (single tap) | Next operator, after the double-tap window |
| `2x SEL` | Switch the active part |
| `SEL` + key | Mute the active operator |
| `SEL` + `EDIT` | Copy the current page |
| `SEL` + `SAVE` | Init patch, or init part in GLO |
| `SEL` + `ARP` or `SEL` + `PLAY` | Mute part 1 |
| `SEL` + `SEQ` or `SEL` + `REC` | Mute part 2 |
| `ARP`, `SEQ`, `PLAY`, `REC` | Mute operators 1, 2, 3, 4 |

## 4. Contexts and pages

### `home`

Display and performance context. Nine pages. It opens on `PERFORMANCE`, the live
page with cutoff, resonance, wavefolder amount, and operator 1 feedback. The other
eight pages are displays, and the four page knobs have no assignments there. The
`ALGORITHM` encoder edits the active part's algorithm and shows the graph popup.

| Page | Contents |
| --- | --- |
| PERFORMANCE | Cutoff, resonance, wavefolder amount, operator 1 feedback. |
| ALGORITHM | Algorithm graph and routing string. Carriers pink, modulators white. |
| A-ENVS | An envelope graph for each operator of the active part. |
| SCOPES | Four operator scopes for the active part. |
| SPECTROS | Four operator spectrograms for the active part. |
| SCOPES | Two larger part-mix scopes. |
| SPECTROS | Two larger part-mix spectrograms. |
| POST-FX MULTI-PATCH SCOPE | Final mix scope after both filters and the wavefolder. |
| POST-FX MULTI-PATCH SPECTRO | Final mix spectrogram. |

### `edit`

Operator editor. Four pages, operator-relative except `OP DETUNES`.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| OSCILLATOR | RATIO | LEVEL | FEEDBACK | WAVE | Selected operator scope |
| OP DETUNES | OP 1 | OP 2 | OP 3 | OP 4 | Four part-level detunes |
| OP KEY FOLLOW | OP LEVEL KS LO | OP LEVEL KS HI | OP FB KS LO | OP FB KS HI | Selected operator |
| OP VEL SENS | OP LEVEL VS | OP FB VS | | | Selected operator |

### `env`

Envelope context. Six pages. A-ENV follows the selected operator. P-ENV is
part-level.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| A-ENV (rates) | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | RELEASE RATE | A-ENV graph |
| A-ENV (levels) | LEVEL 1 | LEVEL 2 | SUSTAIN | | A-ENV graph |
| P-ENV (rates) | ON | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | P-ENV graph |
| P-ENV (levels) | RELEASE RATE | LEVEL 1 | LEVEL 2 | SUSTAIN | P-ENV graph |
| ENV KEY SCALE | A-ENV RATE KS LO | A-ENV RATE KS HI | P-ENV RATE KS LO | P-ENV RATE KS HI | |
| VEL SENS | A-ENV RATE VS | P-ENV RATE VS | | | |

### `lfo`

Two pages. `A-LFO` follows the selected operator. `P-LFO` is part-level.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| A-LFO | RATE | DEPTH | WAVE | | Selected operator's amplitude LFO |
| P-LFO | RATE | DEPTH | WAVE | | Part pitch LFO |

### `fx`

Output chain. Eight pages. Signal order is filter 1 → wavefolder → filter 2.
Filter 1 has the F-ENV. Filter 2 is static.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| FILTER | ON | CUTOFF | RES | TYPE | Filter 1 |
| F-ENV (rates) | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | RELEASE RATE | F-ENV graph |
| F-ENV (levels) | LEVEL 1 | LEVEL 2 | SUSTAIN | DEPTH | F-ENV graph |
| WAVEFOLD | ON | AMOUNT | THRESH | FOLDS | Wavefolder |
| FILTER 2 | ON | CUTOFF | RES | TYPE | Filter 2 |
| F1 KEY FOLLOW | F1 CUTOFF KS LO | F1 CUTOFF KS HI | F-ENV RATE KS LO | F-ENV RATE KS HI | |
| F2 KEY FOLLOW | F2 CUTOFF KS LO | F2 CUTOFF KS HI | | | |
| FILTER VEL SENS | F1 CUTOFF VS | F2 CUTOFF VS | F-ENV RATE VS | | |

### `glo`

Setup and global context. Ten pages.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| SINGLE PART LAYERING | PART 1 LEVEL | PART 1 DELAY | PART 2 LEVEL | PART 2 DELAY | Two part levels and delays |
| KEY SPLIT | P1 LOW | P1 HIGH | P2 LOW | P2 HIGH | Key ranges |
| MIDI CH | P1 CH | P2 CH | | | Part channels |
| KEY SCALING | BREAKPOINT | KEY SENS ON | | | Targets in EDIT/FX/ENV |
| VEL SENS | VEL SENS ON | | | | Targets in EDIT/FX/ENV |
| VOICE MODE | MODE | PRIORITY | LEGATO | PORTA | The part voice mode |
| MONO STACK | VOICES | DETUNE | TUNE | | The mono stack and part tune |
| NAMES | PART 1 NAME | PART 2 NAME | MULTI-PATCH NAME | | Opens the name editor |
| BACKUP / LOAD | | | | | Host-side SysEx, model byte 64 |
| VERSION + CREDITS | | | | | Firmware and typeface credit |

## 5. Flows

- **Save:** `SAVE` opens the chooser. `KNOB1` toggles single part or multi-patch,
  `KNOB2` scrolls the slot, `SAVE` commits, `HOME` cancels. A single part then
  opens the part chooser. A multi-patch then opens the mode chooser (`discard
  edits`, `save as new part`, `mutate in place`). The bank write waits for
  silence.
- **Load:** `PRESETS` opens the multi-patch browser outside GLO and the
  single-part browser in GLO. The popup shows the slot and name. Two seconds of
  idle applies it. A single-part load opens the part chooser first.
- **Init:** `SEL+SAVE` outside GLO opens a confirmation popup. SAVE resets the
  whole patch, mutes part 2, and resets the names. HOME cancels. In GLO it opens
  the part chooser to initialise one part.
- **Copy:** `SEL+EDIT` on a page with copyable params. Part pages copy to another
  part. Operator pages copy to another part and operator. `KNOB1` picks the
  target, `SAVE` applies, `HOME` cancels.
- **Names:** from `GLO/NAMES`, the matching knob opens the editor. `K1` changes
  the character, `K2` moves the cursor, `SEL` deletes, `SAVE` accepts, `HOME`
  cancels. An idle close restores the old name.

## 6. LED / pad feedback

- Sounding keys light.
- `OCT−`/`OCT+` light when the keybed is shifted below or above its base.
- Muted parts and operators show red in the header.
- The selected part and operator show light blue in the header.
- Parameter values and the algorithm number are hot pink. The page description is
  bright green.

## 7. Boot screen

- **Needed?** No.

## 8. Control flow

- **Context transitions:** boot → `home`. `EDIT`, `ENV`, `LFO`, `FX`, and `GLO`
  are siblings. A switch pops back to home and pushes the new context. Pressing
  the same context button again advances its page.
- **Full context stack, worst case:** `[home, mode]`, depth 2.
- **Selected operator:** a flat 0..3 counter (`op_next`), shared across contexts.
- **Selected part:** a flat 0..1 counter (`part_next`), shared across contexts.
- **Unresolved or ambiguous bindings:** none.

## 9. Known gaps

None after the panel fixes. The live page, the TUNE assignment, the per-operator
envelope graphs, and the INIT PATCH confirmation all match `panel.json` and the
app handlers.

## 10. Acceptance

- **Host UI tests:** `test_generate.py` resolves `panel.json` against the patch's
  `param_ids`. The generated `panel.h` compiles against `ui.h`.
- **Device checks:** held notes during redraw. Visible safe-failure screen,
  `blocked` until hardware.
