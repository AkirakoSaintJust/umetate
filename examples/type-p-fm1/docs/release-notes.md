# Release notes

Newest first.

## 1.0.2

- Adds a live PERFORMANCE page to HOME with cutoff, resonance, wavefolder amount, and operator 1 feedback.
- Moves TUNE to MONO STACK, so the part tune is reachable from a page knob.
- Draws one amplitude envelope per operator on the HOME A-ENVS page.
- Adds a confirmation popup before INIT PATCH.
- The manual now includes the full panel walkthrough, the parameter reference, and the save, load, init, and copy flows.
- The browser app draws the 240 by 240 screen at 1:1 on a wide desktop and uses the plugin interface language, with self-hosted Zen Dots and DotGothic16.
- The help panel has a single `controls` section for the key map, the knobs, the buttons, and the shortcuts, plus `links`. It drops the `what this is` section, and the links open the manual, release notes, and source on GitHub.
- The wordmark is `type P.fm1` in Zen Dots. `type` is lowercase, `P` is uppercase, `.fm1` is lowercase, and the dot is pink. The browser app and the plugin use the same mark.

## 1.0.1

- This release works on units that ship the UC25HQ80 flash chip (JEDEC id
  `0xB36014`), which is common on recent AliExpress stock. Those units used to
  show a flash error when saving (saves stayed in RAM), and the update loader
  refused to install. The firmware now accepts both the Puya P25Q80 (`0x856014`)
  and the UC25HQ80 (`0xB36014`), in the app and in the update loader.

## 1.0.0

The first release ships the full instrument.

- Four-operator FM with eight algorithms, two multitimbral parts, twenty voices.
- Two multimode filters and a wavefolder.
- Per-operator feedback, detune, twelve waveforms, four-stage amplitude envelope,
  and tremolo.
- Voice modes: poly and mono, unison up to eight, legato, portamento, and note
  priority.
- Pitch LFO and per-note pitch envelope.
- Key and velocity follow across the operators, filters, and envelopes.
- A 240 by 240 panel built on the M-VAVE FM-1 surface, with the operator editor,
  the output chain, the global modulation, and the save and preset flows.
- MIDI in with CC control, sustain, panic, pitch bend, and program change.
- SysEx for the parameters, the part patches, the multi patches, and the settings.
- A browser app that runs the same sound engine, for trying patches without a
  device.
