# Feature contract: OPM bank converter

> One contract per accepted feature. A feature is done when the contract and its
> evidence are satisfied. Compiling is one check among several.

## Identity

- **Feature:** `umetate opm convert`, an OPM text bank to a Type P.fm1 bank.
- **Brief section:** [Mapping OPM voices to Type P.fm1](opm-to-type-p-fm1.md).
- **Owner / date:** P1Onken, 2026-11-06.
- **Disposition:** accepted. The physical device transfer is `blocked` with the
  rest of the device layer.

## Player outcome

- **New player action:** load a VOPM or VOPMex voice as a Type P.fm1 single part
  without rebuilding it by hand.
- **Sound and behaviour:** the same operator graph, ratios, levels, feedback
  depth, and envelope gesture. The timbre sits in the same spectral region and
  the audible envelope stages keep their timing within the stated tolerance.
- **Failure mode:** a malformed bank, an out-of-range field, a
  missing operator line, or a bad slot is rejected with a line number. A field
  with no counterpart (noise, pan, a ratio above 16.00) is reported per slot and
  the rest of the voice still converts.

## Dependencies and interactions

- **Other features:** the preset record and SysEx envelope in `_records.py` and
  `_sysex.py`, the part-patch geometry in `firmware/gen/params.json`, and the
  SysEx layout generator.
- **Platform/API/HAL changes:** none. The converter is a host tool.
- **Persistence/version impact:** a converted part is a normal record version 1.
  The record carries the layout's `n_params` (134) timbre values.
- **MIDI/clock impact:** none. The `.syx` stream uses the existing dump frames.

## Parameter and event semantics

- **Parameters, ranges, defaults, curves, units:** `TL` maps to `99 - TL`,
  `MUL` and `DT2` to the Q16 ratio, `D1L` to `l2 = 99 - 4*D1L`, and the rates
  from the measured stage-time map. The full table is in the mapping page.
- **Note/event ordering and ownership:** the bank is data. Loading a part into a
  part is the device's existing flow.
- **Voice allocation and stealing:** unchanged.
- **Sustain/panic behaviour:** unchanged.

## Bounds and resources

- **Maximum voices/events/effects:** 128 part slots per bank, 64 multi slots.
  The converter fills no multi patches.
- **Per-sample and per-block operations:** none. The converter runs on the host.
- **RAM, flash, stack, pool:** none in the firmware.
- **Overflow/overload policy:** ratios clamp at 16.00, levels clamp at 0 to 99,
  and pitches clamp at the Type P.fm1 detune range.
- **Division, shift, and range analysis:** the converter is Python. The emitted
  values are inside the manifest ranges.

## Files and interfaces

- **Candidate files:** `umetate/_opm.py`, `umetate/opm.py`,
  `umetate/test_opm.py`, `docs/opm-to-type-p-fm1.md`.
- **Public contract/header:** the `umetate opm convert` CLI and the bank JSON.
- **State owner and publication rule:** the host writes the bank. The firmware
  owns the live state after a load.
- **Forbidden dependencies:** none. The converter does not import a plugin or a
  build tree.

## Verification

- **Host vector(s):** `python3 -m umetate.test_opm` parses a bank, converts a
  CON 3 and a CON 0 voice, checks the graph, levels, ratios, feedback, and the
  measured rate map, and round-trips the bank through the SysEx envelope.
- **Browser vector:** not applicable.
- **Target package check:** the `.syx` uses the same records and frames as
  `umetate preset export/import`, which the gate covers.
- **Physical timing/device check:** `blocked`, no hardware.
- **Tolerance/metric:** a factor of 1.5 on the full-band centroid and 95 percent
  roll-off for a held middle-C note, and a factor of 2 on the audible envelope
  timing.
- **Evidence artefact:** the corpus run in this contract.

### Measured evidence

The corpus has 438 text banks and 56,032 voices, and a deterministic 200-voice
sample was rendered at middle C with the filters and wavefolder off and the
VOPMex output FIR off.

| Measure | Median ratio | Within 1.25 | Within 1.5 | Within 2 |
| --- | ---: | ---: | ---: | ---: |
| Spectral centroid | 1.01 | 87 percent | 95 percent | 98 percent |
| 95 percent roll-off | 1.00 | 85 percent | 90 percent | 94 percent |

| Timing measure | Median | Within a factor of 2 |
| --- | ---: | ---: |
| Release time to -20 dB | 1.00 | 98 percent |
| Decay slope, 0.1 to 0.7 s | 1.03 | 77 percent |

The decay slope is the weakest measure because the Type P.fm1 one-pole eases
into a sustain where the OPM decay is a straight dB line. The rate map aims at a
shallower point as the OPM stage gets faster, from 21 dB at rate 0 down to 3 dB at
rates 23 to 31.

The measured algorithm cases in the mapping page land at 0.99 to 1.06 on the
centroid with the current engine.

The pitch LFO depth was measured on a plain sine at C7 with `PMD` 127:

| `PMS` | OPM depth | Type P.fm1 depth |
| --- | ---: | ---: |
| 2 | 12 cents | 12 cents |
| 4 | 48 cents | 50 cents |
| 5 | 96 cents | 103 cents |

The earlier mapping had a unit error here, 1/64 semitone read as 1/64 octave,
which made the vibrato twelve times too deep, and the corpus spectra still matched
because the vibrato averaging hid it, but the A/B renders did not. The unit test
now pins the expected depth.

`D1L` 15 is the special 93 dB step and now maps to silence, though the earlier code
used `99 - 4*15 = 39`, which sustained at about -45 dB and made a decay to `D1L` 15
feel longer. A controlled `D1R` 10, `D1L` 8 stage reaches -9 dB in 0.52 s in both
engines. The whole stage to `D1L` takes 1.41 s in OPM and 2.3 s in Type P.fm1,
because the one-pole tail is longer. The rate map aims 21, 18, 15, 12, 9, 6 or
3 dB into the stage, depending on the OPM rate.

The match table was checked rate by rate against both engines. `AR` 4 to 22 land
within 0.83 to 1.01 of the OPM time at the chosen point, and `D1R` 3 to 23 within
0.80 to 1.17. The slowest three attacks and the slowest two decays hit the Type
P.fm1 rate 0 floor, so `AR` 1 to 3 and `D1R` 1 to 2 still arrive early.

Matching the whole stage time was tried, and it reads badly: an `AR` 3 attack
reached -12 dB at 0.30 s against the OPM's 1.96 s, and an `RR` 4 release was 2
to 3 times too slow. The one-pole spends most of a stage in its quiet tail, so
the audible part has to stay fast. The point match is the shipped choice.

## Risks and fallback

- **Assumptions/open research:** the OPM envelope timing comes from the
  published YM2151 tables simulated at the chip EG clock. A different OPM clock
  would change the absolute times but not the ratio between the two maps.
- **Safe experiment and stop criterion:** render a converted voice through both
  engines and compare the centroid. If the ratio leaves 1.5 and the graph and
  ratios are right, treat it as the serial-chain limit rather than a parse bug.
- **Smaller alternative:** convert one voice at a time and store it in a chosen
  slot with `--first` and `--start`.
- **Rollback:** remove the `opm` command from `cli.py`. The bank format and the
  firmware are untouched.
