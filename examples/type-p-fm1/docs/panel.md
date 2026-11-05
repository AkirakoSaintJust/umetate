# Type P.fm1 panel reference

The panel is the real M-VAVE FM-1 surface: 27 keys, a volume pot, three left
encoders, four page encoders, the transport buttons, and a 240 by 240 screen. This
page is the map. It covers the controls, the six contexts, every page, and the
save, load, init, and copy flows.

I kept the live surface simple. The keys and the ALGORITHM encoder are always
available. Everything else is a page you open with a context button.

## The surface

- **27 keys** play notes, F3 to G5. `OCT−` and `OCT+` move the keybed an octave
  down or up, clamped to two octaves either way.
- **MASTER** is the volume pot. It is always volume.
- **ALGORITHM** is the dedicated algorithm encoder. It always edits the active
  part's algorithm. Turning it shows the algorithm graph for about 600 ms after
  you stop.
- **SELECT** is the page encoder. It moves forward and back through the current
  context's pages.
- **PRESETS** opens the preset browser.
- **KNOB 1 to 4** are the page encoders. On a parameter page they edit the
  parameter rows from top to bottom. If a page has fewer than four rows, the extra
  knobs do nothing. Display pages have no assignments.
- **HOME, EDIT, ENV, LFO, FX, GLO** are the six context buttons.
- **SEL** selects the next operator on a single tap. A double tap within about
  300 ms switches the active part. Hold SEL for the chords below. The single tap
  lands after the double-tap window, so there is a short pause.
- **SAVE** opens the save chooser. With SEL it initialises the patch or a part.
- **ARP, SEQ, PLAY, REC** mute operators 1 to 4. With SEL they mute parts.

## How to move

Press a context button to open that context at its first page. Press the same
button again to move to the next page. `SELECT` also pages forward and back. The
pages wrap at the ends.

`HOME` pops back to the home context. Press `HOME` again to step through the home
pages.

The header stays at the top. The first line shows the parts, the four operators,
the algorithm, and the context and page. The second line shows the current page
title. The active part and operator are light blue, muted parts and operators are
red, parameter values and the algorithm number are hot pink, and the page
description is bright green.

The footer shows the gesture legend:

| Gesture | Action |
| --- | --- |
| `SEL` (single tap) | Next operator |
| `2x SEL` | Switch part |
| `SEL` + key | Mute the active operator |
| `SEL` + `EDIT` | Copy the current page |
| `SEL` + `SAVE` | Init patch, or init part in GLO |
| `SEL` + `ARP` or `SEL` + `PLAY` | Mute part 1 |
| `SEL` + `SEQ` or `SEL` + `REC` | Mute part 2 |
| `ARP`, `SEQ`, `PLAY`, `REC` | Mute operators 1, 2, 3, 4 |

A popup owns the controls while it is open. It closes on its own after about
three seconds of no input without committing. Press `SAVE` to commit.

## HOME

The home context is the display and performance view. It has eight pages. The four
page knobs have no assignments on any of them. The `ALGORITHM` encoder and the
keys are the live controls.

| Page | What it shows |
| --- | --- |
| ALGORITHM | The current algorithm as four operator blocks and a routing string. Carriers are pink, modulators white. Turn `ALGORITHM` to change it. |
| A-ENVS | Four amplitude-envelope graph cells. In the current firmware all four draw the selected operator's envelope, so use `SEL` to step through the operators and compare them. |
| SCOPES | Four oscilloscope traces, one per operator of the active part. |
| SPECTROS | Four spectrograms, one per operator of the active part. |
| SCOPES | The two part mixes, one larger scope per part. |
| SPECTROS | The two part mixes, one larger spectrogram per part. |
| POST-FX MULTI-PATCH SCOPE | The final mixed output after both filters and the wavefolder. |
| POST-FX MULTI-PATCH SPECTRO | The final mix as a spectrogram. |

The two pairs of scope pages share a title. The first pair shows four small traces
for the operators. The second pair shows two larger traces for the part mixes. The
post-FX pages say `POST-FX MULTI-PATCH`, so they are easy to tell apart.

The algorithm graph popup appears while you turn the encoder and stays for about
600 ms after you stop.

## EDIT

The `EDIT` context is the operator editor. It has four pages. `SEL` chooses the
operator, 1 to 4, and the header shows which one. The first three pages follow the
selected operator. `OP DETUNES` is part-level and shows all four operators.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| OSCILLATOR | RATIO | LEVEL | FEEDBACK | WAVE | A scope of the selected operator. |
| OP DETUNES | OP 1 | OP 2 | OP 3 | OP 4 | The four per-operator detunes for the active part. |
| OP KEY FOLLOW | OP LEVEL KS LO | OP LEVEL KS HI | OP FB KS LO | OP FB KS HI | The selected operator's level and feedback key follow. |
| OP VEL SENS | OP LEVEL VS | OP FB VS | | | The selected operator's level and feedback velocity sensitivity. |

`OP DETUNES` is the only part-level page here. The key-follow and velocity pages
are operator-relative, so they change the operator named in the header.

## ENV

The `ENV` context is the envelope editor. It has six pages. The A-ENV pages edit
the selected operator's amplitude envelope. The P-ENV pages edit the part's pitch
envelope. The last two pages set the key and velocity follow for the envelope
rates.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| A-ENV (rates) | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | RELEASE RATE | The selected operator's A-ENV graph. |
| A-ENV (levels) | LEVEL 1 | LEVEL 2 | SUSTAIN | | The same graph, for the levels. |
| P-ENV (rates) | ON | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | The part pitch-envelope graph. |
| P-ENV (levels) | RELEASE RATE | LEVEL 1 | LEVEL 2 | SUSTAIN | The same graph, for the levels. |
| ENV KEY SCALE | A-ENV RATE KS LO | A-ENV RATE KS HI | P-ENV RATE KS LO | P-ENV RATE KS HI | The rate key-follow amounts. |
| VEL SENS | A-ENV RATE VS | P-ENV RATE VS | | | The rate velocity-follow amounts. |

Both A-ENV pages are titled `A-ENV`, and both P-ENV pages are titled `P-ENV`. The
row labels tell you which half you are on. The A-ENV pages follow the selected
operator. The P-ENV pages are part-level.

## LFO

The `LFO` context has two pages. `A-LFO` is the selected operator's amplitude LFO.
`P-LFO` is the part pitch LFO. This is a separate context from `GLO`.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| A-LFO | RATE | DEPTH | WAVE | | The selected operator's amplitude LFO. |
| P-LFO | RATE | DEPTH | WAVE | | The part pitch LFO. |

The fourth knob is unused on both pages.

## FX

The `FX` context is the output chain. It has eight pages. The signal order is
filter 1, then the wavefolder, then filter 2. Filter 1 has the F-ENV. Filter 2 is
static. The key-follow and velocity pages set how the filters and the F-ENV
respond across the keyboard.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| FILTER | ON | CUTOFF | RES | TYPE | Filter 1. |
| F-ENV (rates) | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | RELEASE RATE | The filter-envelope graph. |
| F-ENV (levels) | LEVEL 1 | LEVEL 2 | SUSTAIN | DEPTH | The filter-envelope graph and its depth. |
| WAVEFOLD | ON | AMOUNT | THRESH | FOLDS | The wavefolder. |
| FILTER 2 | ON | CUTOFF | RES | TYPE | Filter 2, after the wavefolder. |
| F1 KEY FOLLOW | F1 CUTOFF KS LO | F1 CUTOFF KS HI | F-ENV RATE KS LO | F-ENV RATE KS HI | Filter 1 and F-ENV key follow. |
| F2 KEY FOLLOW | F2 CUTOFF KS LO | F2 CUTOFF KS HI | | | Filter 2 key follow. |
| FILTER VEL SENS | F1 CUTOFF VS | F2 CUTOFF VS | F-ENV RATE VS | | Filter 1, filter 2, and F-ENV velocity sensitivity. |

Both F-ENV pages are titled `F-ENV`. The rates page has the four stage rates. The
levels page has the three levels and the envelope depth. Filter 2 has no envelope
of its own, so its page is only the filter controls.

## GLO

The `GLO` context is the setup and global page. It has ten pages. This is where the
two parts are layered, split, assigned to MIDI channels, and named. It also holds
the voice mode, the mono stack, the backup page, and the credits.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| SINGLE PART LAYERING | PART 1 LEVEL | PART 1 DELAY | PART 2 LEVEL | PART 2 DELAY | The two part levels and delays. |
| KEY SPLIT | P1 LOW | P1 HIGH | P2 LOW | P2 HIGH | The key ranges for the two parts. |
| MIDI CH | P1 CH | P2 CH | | | The MIDI channel for each part. |
| KEY SCALING | BREAKPOINT | KEY SENS ON | | | The global key-follow breakpoint and switch. The targets are in EDIT, FX, and ENV. |
| VEL SENS | VEL SENS ON | | | | The global velocity-follow switch. The targets are in EDIT, FX, and ENV. |
| VOICE MODE | MODE | PRIORITY | LEGATO | PORTA | The part voice mode. TUNE is shown below PORTA but has no page-knob assignment in this panel. |
| MONO STACK | VOICES | DETUNE | | | The mono stack count and detune. |
| NAMES | PART 1 NAME | PART 2 NAME | MULTI-PATCH NAME | | Open the name editor with the matching knob. |
| BACKUP / LOAD | | | | | Host-side SysEx backup, `umetate preset export/import`, model byte 64. No MIDI channel is needed. |
| VERSION + CREDITS | | | | | The firmware version, the product name, and the typeface credit. |

`KEY SCALING` and `VEL SENS` only hold the breakpoint and the on/off switch. The
per-target amounts live in `EDIT` for operator level and feedback, in `FX` for the
filter cutoffs and the F-ENV rate, and in `ENV` for the A-ENV and P-ENV rates.

`VOICE MODE` has five rows. The four page knobs reach MODE, PRIORITY, LEGATO, and
PORTA. TUNE is visible, but this panel does not assign it to a page knob.

The `NAMES` page opens the name editor from the matching knob. The editor uses
`K1` for the character, `K2` for the cursor, `SEL` to delete, `SAVE` to accept, and
`HOME` to cancel. The editor auto-closes after about three seconds of no input and
restores the old name.

`BACKUP / LOAD` and `VERSION + CREDITS` are read-only pages. The four page knobs do
nothing there.

## Saving and loading

`SAVE` opens the save chooser. The chooser has two rows, `single part` and
`multi-patch`, and each row shows the slot number and the stored name. `KNOB 1`
toggles the kind, `KNOB 2` scrolls the slot, `SAVE` commits, and `HOME` cancels.

For a single part, `SAVE` opens the `WHICH SINGLE PART` chooser. `KNOB 1` picks
part 1 or part 2, `SAVE` saves, and `HOME` cancels.

For a multi-patch, `SAVE` opens the save-mode chooser. `KNOB 1` picks the mode,
`SAVE` saves, and `HOME` goes back to the slot chooser. The three modes are:

- **discard edits**: save the composition using the parts' stored single-part
  slots, so the active part's live edits are not written into a part slot.
- **save as new part**: write the active part's live edits to a new empty
  single-part slot, then save the multi-patch referencing it.
- **mutate in place**: write the active part's live edits into its existing
  single-part slot, then save the multi-patch.

The actual bank write waits until the engine is quiet, so a save never clicks.

`PRESETS` opens the preset browser. Outside `GLO` it browses the multi-patches. In
`GLO` it browses the single parts. The popup shows the slot number and the stored
name. Scroll with the encoder, then stop for about two seconds to apply. A
single-part load opens the `WHICH SINGLE PART` chooser first.

`SEL` + `SAVE` outside `GLO` initialises the whole patch. Both parts go to their
init values, part 2 is muted, and the names reset to `INIT PART` and `INIT MULTI`.
Save first if you want to keep the current patch. In `GLO`, `SEL` + `SAVE` opens
the part chooser so you can initialise one part.

`SEL` + `EDIT` copies the current page. On a part-level page the chooser lists the
two parts. On an operator page it lists the eight part and operator targets.
`KNOB 1` picks the target, `SAVE` applies, and `HOME` cancels. On a page with
nothing to copy, the chord opens `EDIT` instead.

## The screen and the LEDs

The screen is 240 by 240. The header and footer stay fixed while the page below
them changes. The header shows the active part and operator, the algorithm, the
context and page, and the page title. The footer carries the gesture legend.

Keys light as they sound. The `OCT−` and `OCT+` buttons light when the keybed is
shifted below or above its base. Muted parts and operators show red in the header.
The parameter values and the algorithm number are hot pink, and the page
description is bright green.

Popups are modal. They cover the page, take every control, and close after about
three seconds of no input without committing. `SAVE` commits the save and name
editors.

## Quick reference

| Context | Pages | What it is |
| --- | --- | --- |
| HOME | 8 | Algorithm graph, envelope graphs, scopes, spectros, post-FX displays. |
| EDIT | 4 | Operator oscillator, detunes, key follow, velocity sensitivity. |
| ENV | 6 | A-ENV, P-ENV, envelope key follow, envelope velocity sensitivity. |
| LFO | 2 | A-LFO and P-LFO. |
| FX | 8 | Filter 1, F-ENV, wavefolder, filter 2, filter follow. |
| GLO | 10 | Parts, split, MIDI channels, voice mode, names, backup, credits. |
