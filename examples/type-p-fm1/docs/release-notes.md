# Release notes

Newest first.

## 1.0.4

- Filters: FILTER 1 and FILTER 2 are now the 24 dB/oct liquid ladder. It has low-pass, band-pass and high-pass modes, a level-preserving resonance make-up, and a cutoff envelope that uses the whole range.
- Resonance: the display reads 0.00 to 100.00 percent with an exponential taper. The top of the knob is the strongest stable resonance, and the curve gives fine control near it.
- Cutoff: the top of the range stops at the ladder's stable coefficient ceiling, so the filter stays clean at every resonance.

## 1.0.3

- Level: the operator level is now the Yamaha total-level scale, 0.75 dB per step. Level 75 on a ratio 1 modulator gives half a cycle of phase deviation, and the level-to-index table matches the OPM and the DX21, DX27, and DX100.
- Modulators: the phase-modulation scale reaches the OPM's four-cycle full-scale deviation at level 99. A 1:1 pair follows the VOPMex centroid within about 11 percent from `TL` 0 to `TL` 32.
- Feedback: the self-feedback tap takes the level-gained output, averages two samples, and reaches two cycles at a full-level operator. The depth follows the operator level, so a decaying sound keeps its shape.
- Ratio knobs: the knob steps through multiples of 0.50, 1, √2, π/2, and √3, with √2/2, π/4, and √3/2 near the bottom. The firmware, web app, and plugin share the ladder, and the plugin's arrow keys step it.
- Effects: the filters and the wavefolder start bypassed at power-on and in the plugin. Part 2 stays active.
- Scopes: the plugin and screen scopes are rescaled for the new level curve, with a soft knee so a loud trace stays inside the widget.
- Docs: the OPM mapping covers the level curve, the feedback depth law, and the measured cases. The envelope note gains the stage lengths and curve shape.
- Licensing: the plugin archives carry their notices in `licences/`, the source archive includes `vendor/deps/`, the Terminus OFL notice is added, and VOPMex is credited.

## 1.0.2

- Adds a live PERFORMANCE page to HOME with cutoff, resonance, wavefolder amount, and operator 1 feedback.
- Moves TUNE to MONO STACK, so the part tune is reachable from a page knob.
- Draws one amplitude envelope per operator on the HOME A-ENVS page.
- Adds a confirmation popup before INIT PATCH.
- Manual: the full panel walkthrough, the parameter reference, and the save, load, init, and copy flows.
- Browser app: draws the 240 by 240 screen at 1:1 on a wide desktop and uses the plugin interface language, with self-hosted Zen Dots and DotGothic16.
- Help panel: a single `controls` section for the key map, the knobs, the buttons, and the shortcuts, plus `links`. It drops the `what this is` section, and the links open the manual, release notes, and source on GitHub.
- Wordmark: `type P.fm1` in Zen Dots. `type` is lowercase, `P` is uppercase, `.fm1` is lowercase, and the dot is pink. The browser app and the plugin use the same mark.

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
