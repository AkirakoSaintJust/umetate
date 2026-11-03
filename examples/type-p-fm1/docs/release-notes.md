# Release notes

## 1.0.1

- Works on units that ship the UC25HQ80 flash chip (JEDEC id `0xB36014`), common
  on recent AliExpress stock. Before this, those units showed a flash error when
  saving (saves stayed in RAM) and the update loader refused to install. The
  firmware now accepts both the Puya P25Q80 (`0x856014`) and the UC25HQ80
  (`0xB36014`), in the app and in the update loader.

## 1.0.0

First release.

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
