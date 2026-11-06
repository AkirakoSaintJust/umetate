# Mapping OPM voices to Type P.fm1

The OPM and Type P.fm1 both put four sine operators through a phase-modulation
algorithm, but they are different instruments. I compared VOPMex's OPM core with the
Type P.fm1 engine on the same note, with part 2 muted and only sine operators, and
measured the WAVs. The result is a working starting point for a conversion. It does
not claim that the two patches are the same. The raw format is in
[OPM patch file format](opm-file-format.md).

## Test rig

The OPM side uses `OPM.cpp` from the VOPMex source in `scratch/vopmex_src_20210501`,
compiled into a small renderer. The Type P.fm1 side uses the `p1::Engine` harness and
the generated Type P.fm1 DSP. Both render at 44.1 kHz, 16-bit, with an 800 ms note
and a 400 ms release. The spectrum comes from the steady part of the note, between
0.2 s and 0.6 s, using a Hann window and a plain radix-2 FFT.

The renderers, the case generator, and the spectrum script are in
`scratch/opm-analysis/`. They are local test tools, not part of the firmware build.

The Type P.fm1 side is a single-part patch. Part 2 is muted with `level.p1=0` and
`op1_mute.p1` through `op4_mute.p1` set to 1. All four operator waveforms are 0, so
the operators are sine. The filters and wavefolder are off. The OPM side uses the
same four operators, with `SLOT` 120 so all four key on.

The renderer reads `filter_on`, `filter2_on`, `fold_on`, `fold`, `level.p1`, the
four part-2 mutes, and the four waveforms back from the engine after loading each
case file, and it refuses to render if any of them is not the isolated value. A typo
in a case cannot quietly leave a filter or the wavefolder in the signal.

VOPMex also has an optional output FIR, on by default. The chip has no such stage,
and the filter colours bright patches, so the analysis turns it off (`render_opm`
takes a final `0` argument) and compares the two cores rather than the player's
output stage.

The measures are the full-band spectral centroid, the 95 percent roll-off
frequency, the band energy above 1, 2, 4, and 8 kHz, and the odd-to-even harmonic
ratio. None of them depends on a detected fundamental, which matters because a deep
modulation index can move the strongest partial away from the note. Absolute output
level is ignored because the two engines have different output gains.

## Mapping at a glance

| OPM | Type P.fm1 | How close |
| --- | --- | --- |
| `M1`, `C1`, `M2`, `C2` | `O1`, `O2`, `O3`, `O4` | direct |
| `CON` 0 to 7 | `algorithm.p0` 0 to 7 | direct except 3, which uses algorithm 2 |
| `MUL` 0 to 15 | `opN_ratio.p0` | direct |
| `TL` 0 to 127 | `opN_level.p0` 0 to 99 | measured for carriers and modulators, matched against VOPMex |
| `FL` 0 to 7 | `op1_feedback.p0`, or `op2_feedback.p0` for algorithm 3 | two cycles at 100%, halved per `FL` step |
| `AR` | `attack.p0` or `opN.eg.r1.p0` | measured stage time |
| `D1R` | `opN.eg.r2.p0` | measured stage time |
| `D1L` | `opN.eg.l2.p0` | exact level conversion, 15 is silence |
| `D2R` | `opN.eg.r3.p0` | measured stage time |
| `RR` | `release.p0` or `opN.eg.r4.p0` | measured stage time |
| `KS` 0 to 3 | `opN_aenv_ks_lo.p0` and `opN_aenv_ks_hi.p0` | fitted over F3 to G5 |
| `DT1` 0 to 7 | `opN_detune.p0` | measured at middle C, the OPM table is key-dependent |
| `DT2` 0 to 3 | folded into `opN_ratio.p0` | exact ratio |
| `PMS`, `AMS`, `AMD`, `PMD`, `LFRQ`, `WF` | pitch LFO and per-operator tremolo | measured rate law and pitch depth, approximate tremolo depth |
| `NE`, `NFRQ` | no counterpart | none |
| `PAN` | no per-voice counterpart | none |
| `SLOT` | `opN_mute.p0` | only whole-operator muting |
| `AME` | `opN_trem_depth.p0` set above 0 | approximate |

## Operator order and algorithms

The operator order lines up for algorithms 0, 1, 2, 4, 5, 6, and 7. OPM's `M1`
becomes Type P.fm1's `O1`, `C1` becomes `O2`, `M2` becomes `O3`, and `C2` becomes
`O4`. Algorithm 3 uses a different assignment, covered below. The algorithm numbers
also line up in most cases:

| OPM `CON` | OPM routing | Type P.fm1 routing | Match |
| --- | --- | --- | --- |
| 0 | M1 to C1 to M2 to C2 | O1 to O2 to O3 to O4 | exact |
| 1 | (M1 + C1) to M2 to C2 | (O1 + O2) to O3 to O4 | exact |
| 2 | C1 to M2, M1 and M2 to C2 | (O1 + (O2 to O3)) to O4 | exact |
| 3 | M1 to C1, C1 and M2 to C2 | algorithm 2 with M2=O1, M1=O2, C1=O3, C2=O4, feedback on O2 | exact with remap |
| 4 | (M1 to C1) + (M2 to C2) | (O1 to O2) + (O3 to O4) | exact |
| 5 | M1 to M2, M1 to C1, M1 to C2 | O1 to O2, O1 to O3, O1 to O4 | exact |
| 6 | M1 to C1, M2 and C2 direct | O1 to O2, O2 + O3 + O4 | exact |
| 7 | all four parallel | all four parallel | exact |

Algorithm 3 is the one that needs a different operator assignment. OPM sends M1 to
C1 and then C1 and M2 into C2. Type P.fm1's algorithm 2 is
`O1 + (O2 to O3) to O4`, so set `M2` to `O1`, `M1` to `O2`, `C1` to `O3`, and `C2` to
`O4`. Then O2 (M1) modulates O3 (C1), and O1 (M2) plus O3 (C1) modulate O4 (C2). OPM
puts the feedback on M1, which is O2 in this layout, so set `op2_feedback.p0` rather
than the usual `op1_feedback.p0`. That reproduces the OPM 3 graph. Type P.fm1's own
algorithm 3 adds an M1-to-M2 path that OPM does not have, so leave it for patches
that want the extra modulation.

The file order and the chip order are a separate trap. The `.opm` file lists M1, C1,
M2, C2, while the chip registers are laid out M1, M2, C1, C2. The OPM page covers the
register offsets. This document assumes the file has already been read into the four
logical operators.

## Pitch and level

`MUL` maps straight to the Type P.fm1 ratio. The Type P.fm1 ratio is Q16, with 65536
for 1.0, so `MUL` 0 becomes 32768 for 0.5, `MUL` 1 becomes 65536, and `MUL` 15
becomes 983040. `DT2` is not a cents offset. Its four steps multiply the operator
frequency by 1, √2, π/2, and √3, so the combined ratio is:

```text
dt2 = [1, sqrt(2), pi/2, sqrt(3)][DT2]
ratio = (0.5 if MUL == 0 else MUL) * dt2
```

The nominal cent values 0, 600, 781, and 950 are the same ratios in cents. With
`MUL`, the four series are `MUL`, `MUL*√2`, `MUL*π/2`, and `MUL*√3`, so `MUL` 0 gives
0.5, √2/2, π/4, and √3/2. Those inharmonic steps are why `DT2` is useful for bells,
metal, and gong-like timbres.

`DT1` is a fine detune with a key-dependent table, so start with 0 and add a few
cents of Type P.fm1 detune only if the patch needs it.

`TL` is the level control. Both engines use the Yamaha total-level scale: 0.75 dB
per step, so the mapping is one OPM `TL` step per Type P.fm1 `level` step:

| OPM `TL` | Type P.fm1 `level` | Attenuation |
| --- | --- | --- |
| 0 | 99 | 0 dB |
| 8 | 91 | -6 dB |
| 16 | 83 | -12 dB |
| 24 | 75 | -18 dB |
| 32 | 67 | -24 dB |
| 64 | 35 | -48 dB |
| 99 and above | 0 | silent |

The practical formula is `level = 99 - TL`, clamped to 0 to 99. Type P.fm1 runs
out of range above `TL` 99, where OPM still has 21 dB left. A carrier at `TL` 110
is about -82 dB in OPM and silent in Type P.fm1 at level 0. That tail is below
the noise floor of most material.

Modulators follow the same level curve. Type P.fm1's generated router scales the
modulator path by 2 and the phasor scales that by 2^20. A level-99 modulator
reaches four cycles of phase deviation, which is the OPM's full-scale index at
`TL` 0. The index at a level follows the same 0.75 dB step, so the DX21, DX27 and
DX100 line up too: their output level maps to `TL = 99 - level`, and a level-75
modulator reaches π radians in both. A two-operator test at ratio 1:1 confirms the
curve: the Type P.fm1 centroid follows the OPM centroid within about 9 percent at
`TL` 0 and within a few percent through the musical range. Use the same
`level = 99 - TL` formula for modulators and carriers.

## Feedback

OPM feedback is the `FL` field on M1, with 0 to 7. Type P.fm1 has
`op1_feedback.p0` from 0 to 32767, and the other operators have their own feedback
controls. For OPM algorithm 3, M1 is `O2` in the remapped layout, so use
`op2_feedback.p0` there.

Both engines take the feedback from the operator's level-gained output and average
two samples, so the depth follows the level. OPM's `FL` 7 is two cycles of phase
deviation at a full-level operator, half a cycle at `TL` 16 and a quarter at
`TL` 24. Type P.fm1's 100% is the same set of depths. Each OPM `FL` step is 6 dB,
so halve the Type P.fm1 value per step:

| OPM `FL` | `opN_feedback.p0` |
| ---: | ---: |
| 0 | 0 |
| 1 | 512 |
| 2 | 1024 |
| 3 | 2048 |
| 4 | 4096 |
| 5 | 8192 |
| 6 | 16384 |
| 7 | 32767 |

The measured match is closest at moderate depths. On a single self-feedback
operator at `FL` 7, the `TL` 24 and `TL` 32 cases read 416 Hz in both engines and
313 Hz against 312 Hz. Half feedback is darker in Type P.fm1, 312 Hz against
416 Hz at `TL` 24, so a patch that leans on a small feedback amount may want one
step more. A full-level operator puts the loop in a chaotic regime in both
engines, and the spectra differ there, so treat the top of the range as a similar
amount of noise rather than the same noise.

The harmonic balance differs too. OPM was odd-heavy in the test, at +8.1 dB, while
Type P.fm1 was even-heavy, at -4.2 dB. The two synths will not match harmonic for
harmonic.

## Envelope

The envelope fields map by job: `AR` to `attack` or `opN.eg.r1`, `D1R` to
`opN.eg.r2`, `D1L` to `opN.eg.l2`, `D2R` to `opN.eg.r3`, and `RR` to `release` or
`opN.eg.r4`. The level conversion is exact. The attack target is `l1` 99, the first
decay target is `l2 = 99 - 4*D1L` for `D1L` 0 to 14, and the second decay runs to
`l3` 0. `D1L` 15 is the special 93 dB step, so it maps to 0 rather than 39. When
`D2R` is 0 the second decay holds `l2`, so `l3` is `l2`.

The rates come from measured stage times, not a guessed table. The converter
simulates the OPM envelope tables at the chip EG clock, 13.98 kHz, and the Type
P.fm1 one-pole at the 1.38 kHz control rate, then picks the rate whose time to a
chosen point in the stage is closest. The attack matches the time to -12 dB below
full. The decays match the time 16 dB into the trip, or the whole stage when it is
shorter, and the rate then moves up four steps. The release matches the time to
-20 dB. The four-step bias is deliberate: the one-pole tail made the stage read
long, and a slightly faster rate brings the whole stage closer even though the
first few dB are now a little fast.

A controlled `D1R` 10, `D1L` 8 stage takes 1.87 s in OPM and 2.07 s in Type P.fm1
to reach the target, against 2.84 s without the bias. On the demo bank, Solid Bass
tracks the OPM within about a decibel through 0.8 s, Hard Tines is about 1.5 dB
fast, and Tubular Bells is still about 3.5 dB long at 0.4 s.

The curves still differ. An OPM decay is a straight line in dB. The Type P.fm1
one-pole starts faster and eases into its target, and its one-unit floor sets a
minimum speed at low gain. A slow OPM decay to a low `D1L` settles differently, and
a `D2R` stage that takes tens of seconds in OPM maps to the slowest Type P.fm1 rate
and still arrives sooner. The chosen points stay close, and the tail beyond them
does not.

OPM rates are key-scaled. The converter compares the OPM stage times two octaves
either side of the breakpoint and fits the change onto the envelope key-follow
controls. The broader sound-design assessment is in
[Type P.fm1 envelope design](type-p-fm1-envelope-design.md).

## LFO and noise

`PMS` sets the pitch modulation sensitivity, which maps to the pitch LFO depth.
`AMS` sets the amplitude modulation sensitivity, which maps to the per-operator
tremolo depth. The global `AMD`, `PMD`, `LFRQ`, and `WF` set the shape and rate of
the modulation, and Type P.fm1's `pitch_rate`, `pitch_depth`, `pitch_wave`,
`opN_trem_rate`, `opN_trem_depth`, and `opN_trem_wave` are the nearest controls. The
OPM LFO rates and depths do not share a scale with Type P.fm1, so set the shape first
and tune the rate by ear.

`NE` and `NFRQ` have no Type P.fm1 counterpart. Type P.fm1 has no noise generator,
so an OPM patch that relies on C2 noise needs a different source, such as a noisy
waveform or heavy feedback.

`PAN` has no per-voice counterpart in the single-part Type P.fm1 patch. The part
output is fixed. `SLOT` is a key-on mask, and Type P.fm1's `opN_mute` only mutes a
whole operator, so use levels for partial operator mixes and keep all four operators
unmuted in a normal conversion.

## Measured cases

The cases below use the same note and the same operator ratios. Type P.fm1 uses
`level = 99 - TL` for every operator. The measure is the full-band spectral
centroid of the steady segment.

| Case | OPM centroid | Type P.fm1 centroid | Ratio |
| --- | --- | --- | --- |
| Additive algorithm 7 | 345 Hz | 348 Hz | 1.01 |
| Serial algorithm 0 | 4841 Hz | 4989 Hz | 1.03 |
| Algorithm 3 remap | 3405 Hz | 3359 Hz | 0.99 |
| Parallel algorithm 4 | 2660 Hz | 2810 Hz | 1.06 |
| Feedback, `FL` 7, `TL` 24 | 416 Hz | 416 Hz | 1.00 |

The additive case has no modulation index, so it tests the level curve only. The
serial case compounds the index through three stages, and it was the farthest
apart before the index and level scales were corrected. With the OPM output FIR
off, all five cases land within 7 percent.

A two-operator pair at ratio 1:1 isolates the index. The modulator `TL` sweeps from
0 to 64, and the centroid follows the OPM until the Type P.fm1 level runs out:

| OPM `TL` | OPM centroid | Type P.fm1 centroid |
| --- | --- | --- |
| 0 | 3895 Hz | 4262 Hz |
| 8 | 1947 Hz | 2049 Hz |
| 16 | 969 Hz | 986 Hz |
| 24 | 494 Hz | 495 Hz |
| 32 | 532 Hz | 527 Hz |
| 40 | 314 Hz | 262 Hz |

## Brightness and scaling

The brightness of the two engines comes from the modulation index, and the index
scale used to be wrong. The operators carry a -12 dB headroom for the four-carrier
sum, and the router doubled the modulator path, so a level-99 modulator reached a
quarter of a cycle of phase deviation where the OPM reaches four. That is a 24 dB
shortfall, and no modulator level could close it.

The phasor now scales `fm` by 2^20 and the router by 2. A level-99 modulator
reaches four cycles, the same as the OPM at `TL` 0, and the level curve does the
rest. The feedback path bypasses the router and taps the level gain, so it reaches
half that index.

The sweep above is the evidence. With the old scale the Type P.fm1 pair read
262 Hz to 524 Hz across `TL` 0 to 32, against the OPM's 494 Hz to 3895 Hz. The
current build reads 4262 Hz at `TL` 0 against 3895 Hz, and the two centroids stay
within a few percent through `TL` 8 to 40.

Feedback no longer adds to the gap. Both engines tap the level-gained output,
average two samples, and reach two cycles at a full-level operator, so the depth
law matches. The top of the range is still a chaotic regime and the spectra differ
there.

## Conversion recipe

1. Start from an init patch. Set `level.p1=0` and `op1_mute.p1` through
   `op4_mute.p1` to 1, so only part 1 sounds.
2. Set `op1_waveform.p0` through `op4_waveform.p0` to 0. This page assumes sine
   operators only.
3. Leave `filter_on`, `filter2_on`, `fold_on`, and `fold` at 0. These are global
   settings, not part-patch parameters, and the instrument ships with them
   bypassed. The bank assumes that.
4. Assign operators. For algorithms 0, 1, 2, 4, 5, 6, and 7 use
   `M1=O1`, `C1=O2`, `M2=O3`, `C2=O4`. For OPM algorithm 3 use `M2=O1`, `M1=O2`,
   `C1=O3`, `C2=O4` and put the feedback on `op2_feedback.p0`.
5. Set `algorithm.p0` from `CON`, but use algorithm 2 for OPM `CON` 3. The remap in
   the previous step supplies the OPM 3 graph.
6. Set each ratio from `MUL`, folding `DT2` into the ratio if it is not zero.
7. Set every level with `99 - TL`, clamped to 0 to 99. Carriers and modulators
   use the same formula.
8. Set `op1_feedback.p0` from `FL`: 32767 for `FL` 7, and half for each step down
   the table above.
9. Map the envelope levels with `l1=99`, `l2=99-4*D1L`, and `l3=0` when `D2R` is
   running. Pick the rates from the measured stage times, or let the converter do
   it.
10. Play the same note through both patches and compare the first few harmonics.
    The useful goal is the same ratios, the same algorithm, and a similar
    brightness. The two synths will not null.

## The converter

`umetate opm convert` does the whole recipe. It reads a VOPM or VOPMex text bank,
converts every voice, and writes a 128-slot bank JSON. The `--syx` option also
writes the device stream, and `--report` prints the per-slot warnings.

```sh
umetate opm convert voices.opm --out voices.bank.json --syx voices.syx
umetate opm convert voices.opm --first 16 --pack --report
```

The converter keeps the OPM slot number when it is free, so a full bank keeps its
layout. `--pack` fills from `--start` upwards instead, which is handier for a
partial selection. `--first` takes the first voices after the slot and silent
filters.

A device part record holds 134 timbre parameters. The five routing fields
(`channel`, `low`, `high`, `level`, `delay`) live in the multi patch, so the
converter leaves the part record at the SysEx layout's `n_params` and fills no
multi patches. Load a converted part from the `GLO` browser. The `.syx` stream
round-trips through `umetate preset import`.

The converter is not a clone and does not try to null the two engines. It keeps
the graph, the ratios, the level curve, the modulation index, the feedback depth,
and the measured envelope timing. It warns on the fields it cannot carry or has to
clamp: the OPM noise generator, a pan setting, a ratio above 16.00, an operator
with `AR` 0, a pitch LFO depth above the Type P.fm1 range, and a name over 15
characters. The feature contract and the corpus evidence are in
[the converter contract](feature-contract-opm-converter.md).

### Tolerance

The working tolerance is a factor of 1.5 on the full-band spectral centroid and
the 95 percent roll-off for a held middle-C note, and a factor of 2 on the
audible envelope timing. A voice inside that band is recognisably the same kind of
sound. The comparison set is a local corpus of 438 OPM bank files and 56,032
voices, rendered at middle C with both filters and the wavefolder off and the
VOPMex output FIR off.

On a 200-voice sample, 89 percent of the converted voices are within 1.5 on the
centroid, 82 percent within 1.25, and 89 percent within 1.5 on the roll-off. The
median ratio is 1.01. The release time is within a factor of 2 for 97 percent of
the voices that have an audible release. The decay slope over 0.1 to 0.7 s has a
median of 0.97 and 83 percent inside a factor of 2. It is still the weakest
measure because the one-pole eases into a sustain where the OPM decay is a
straight dB line. Treat the timing tolerance as the stage time at the chosen
point, not the whole curve.

The serial graphs are the furthest apart in the spectrum because the index
compounds. A converted serial patch can read brighter than its OPM source by a
factor of two or more, still with the same ratios and envelope gesture. The
converter reports nothing for that case, because it is a property of the two
engines rather than a bad parse.

## Remaining differences

The two engines differ in the chaotic regime at the top of the feedback range, the
phase relationship between carrier and modulator, the level taper at low levels,
the envelope curve, and the LFO depth ranges. Type P.fm1 also has no noise
generator and no per-voice pan. A conversion can preserve the operator graph, the
ratio relationships, the level curve, the modulation index, the feedback depth, and
the envelope stage times, but the spectrum will not be identical. That is
expected. The two chips share a family resemblance, but they are different designs.

The LFO mapping is the least exact part. `LFRQ` converts through the measured
YM2151 rate law, so the rate is right. `PMS` and `PMD` convert through the OPM
1/64-semitone `PmValue` law. On a plain sine at C7 with `PMD` 127, the measured
depth is 12 cents in both engines at `PMS` 2, 48 against 50 cents at `PMS` 4, and
96 against 103 cents at `PMS` 5. The Type P.fm1 pitch depth tops out at about
165 cents, so `PMS` 6 and 7 at a high `PMD` clamp, and the tremolo depth is a
fraction of the gain rather than an attenuation in dB, so the average level can
rise slightly where OPM only cuts. The converter warns on the clamp and leaves
the smooth approximations alone.

A ratio above 16.00 clamps to the Type P.fm1 maximum. `MUL` 15 with `DT2` 3 is
25.98, which is the usual case. A patch that relies on the top of that range will
lose the top partials.

## Credits

VOPMex is by osoumen, a fork of the original VOPM by sam. The comparison measured
its rendered output. VOPMex is not part of this repository or the instrument, and
none of its source is redistributed. The licence audit is in
[LICENSING.md](../LICENSING.md).
