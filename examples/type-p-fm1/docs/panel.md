# Type P.fm1 panel reference

The panel is the real M-VAVE FM-1 surface, and this page covers what every control
does, where every page lives, and how to save.

I kept the live page flat on purpose. The four knobs always do something you can
hear, whilst the deeper operator work stays behind EDIT.

## Controls

- **27 keys** play notes, F3 to G5.
- **MASTER** is the volume pot. It is always volume, nothing else.
- **SELECT**, **ALGORITHM**, and **PRESETS** are the three left encoders.
- **KNOB 1 to 4** are the page encoders. Their meaning changes with the page, and
  the screen labels what they do.
- **OCT− / OCT+** shift the keybed a whole octave, down or up.
- The buttons: **FX**, **SEL**, **ENV**, **LFO**, **EDIT**, **GLO**, **HOME**,
  **SAVE**, **ARP**, **SEQ**, **PLAY**, **REC**. The transport buttons (ARP, SEQ,
  PLAY, REC) are not used.

## Four modes

The buttons switch between four modes.

- **HOME** is the performance page. KNOB 1 to 4 are cutoff, resonance, wavefolder
  amount, and operator 1 feedback. The header shows the algorithm.
- **EDIT** is the operator editor. KNOB 1 to 4 edit the four parameters on the
  current page. `SELECT` steps through the pages. `SEL` moves between operators 1
  to 4.
- **FX** is the output chain. KNOB 1 to 4 are cutoff, resonance, and wavefolder.
- **GLO** is the global modulation, the vibrato and the pitch envelope.

`HOME` always returns to the performance page from any mode.

## Editing an operator

`EDIT` opens it. The selected operator and its mute state stay visible in the
header. The pages, in order, with what KNOB 1 to 4 do:

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 |
| --- | --- | --- | --- | --- |
| Pitch | ratio | level | feedback | waveform |
| Env rates | attack | decay 1 | decay 2 | release |
| Env levels | level 1 | level 2 | level 3 | |
| Tremolo | rate | depth | | |
| Mute | op 1 | op 2 | op 3 | op 4 |

The envelope pages also draw the selected operator's envelope as a graph.

## Saving

Press **SAVE**, and a chooser opens for what to save: a single part or the multi
patch, and which slot. The chooser owns the controls while it is open, and it
closes on its own after about three seconds of no input. A save shows a brief
acknowledgement on screen.

There are 128 single-part slots and 64 multi-patch slots. Saving writes only when
the engine is quiet, so a save never clicks.

## Loading

The preset browser opens from the **PRESETS** encoder, and you can also load and
back up the whole bank over SysEx (see the MIDI reference).

## What the screen shows

The screen is 240 by 240, with the algorithm, the selected operator, and the mute
state in the header where they apply. The footer shows the page gesture legend
when there is room. Keys light as they sound, and the selected operator's key
glows in the editor.
