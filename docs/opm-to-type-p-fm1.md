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

The comparison looks at the fundamental, the first sixteen harmonics relative to the
fundamental, the spectral centroid, and the odd-to-even harmonic ratio. Absolute
output level is ignored because the two engines have different output gains.

## Mapping at a glance

| OPM | Type P.fm1 | How close |
| --- | --- | --- |
| `M1`, `C1`, `M2`, `C2` | `O1`, `O2`, `O3`, `O4` | direct |
| `CON` 0 to 7 | `algorithm.p0` 0 to 7 | direct for 0, 1, 2, 4, 5, 6, 7, approximate for 3 |
| `MUL` 0 to 15 | `opN_ratio.p0` | direct |
| `TL` 0 to 127 | `opN_level.p0` 0 to 99 | measured curve for carriers, modulator level needs tuning |
| `FL` 0 to 7 | `op1_feedback.p0` 0 to 32767 | approximate, OPM is brighter |
| `AR` | `attack.p0` or `opN.eg.r1.p0` | approximate |
| `D1R` | `opN.eg.r2.p0` | approximate |
| `D1L` | `opN.eg.l2.p0` | approximate |
| `D2R` | `opN.eg.r3.p0` | approximate |
| `RR` | `release.p0` or `opN.eg.r4.p0` | approximate |
| `KS` 0 to 3 | `opN_aenv_ks_lo.p0` and `opN_aenv_ks_hi.p0` | approximate |
| `DT1` 0 to 7 | `opN_detune.p0` | approximate, the OPM table is key-dependent |
| `DT2` 0 to 3 | folded into `opN_ratio.p0` | approximate |
| `PMS`, `AMS`, `AMD`, `PMD`, `LFRQ`, `WF` | pitch LFO and per-operator tremolo | approximate |
| `NE`, `NFRQ` | no counterpart | none |
| `PAN` | no per-voice counterpart | none |
| `SLOT` | `opN_mute.p0` | only whole-operator muting |
| `AME` | `opN_trem_depth.p0` set above 0 | approximate |

## Operator order and algorithms

The useful coincidence is that the operator order lines up. OPM's `M1` becomes Type
P.fm1's `O1`, `C1` becomes `O2`, `M2` becomes `O3`, and `C2` becomes `O4`. The
algorithm numbers also line up for most of the eight connections:

| OPM `CON` | OPM routing | Type P.fm1 routing | Match |
| --- | --- | --- | --- |
| 0 | M1 to C1 to M2 to C2 | O1 to O2 to O3 to O4 | exact |
| 1 | (M1 + C1) to M2 to C2 | (O1 + O2) to O3 to O4 | exact |
| 2 | C1 to M2, M1 and M2 to C2 | (O1 + (O2 to O3)) to O4 | exact |
| 3 | M1 to C1, M2 to C2 | O1 to O2, O1 to O3, (O2 + O3) to O4 | approximate |
| 4 | (M1 to C1) + (M2 to C2) | (O1 to O2) + (O3 to O4) | exact |
| 5 | M1 to M2, M1 to C1, M1 to C2 | O1 to O2, O1 to O3, O1 to O4 | exact |
| 6 | M1 to C1, M2 and C2 direct | O1 to O2, O2 + O3 + O4 | exact |
| 7 | all four parallel | all four parallel | exact |

Algorithm 3 is the one that does not fit. OPM sends M1 to C1 and M2 to C2. Type
P.fm1's algorithm 3 sends O1 to O2, O1 to O3, and then sums O2 and O3 into O4, so it
adds an M1-to-M2 path that OPM does not have. A conversion will sound close, but the
extra path brightens the result. If you need the OPM topology exactly, use another
host or accept the difference.

The file order and the chip order are a separate trap. The `.opm` file lists M1, C1,
M2, C2, while the chip registers are laid out M1, M2, C1, C2. The OPM page covers the
register offsets. This document assumes the file has already been read into the four
logical operators.

## Pitch and level

`MUL` maps straight to the Type P.fm1 ratio. The Type P.fm1 ratio is Q16, with 65536
for 1.0, so `MUL` 0 becomes 32768 for 0.5, `MUL` 1 becomes 65536, and `MUL` 15
becomes 983040. `DT2` has four coarse steps with nominal offsets of 0, 600, 781, and
950 cents, so the simplest conversion folds it into the ratio:

```text
ratio = (0.5 if MUL == 0 else MUL) * 2^(DT2_cents / 1200)
```

`DT1` is a fine detune with a key-dependent table, so start with 0 and add a few
cents of Type P.fm1 detune only if the patch needs it.

`TL` is the level control. The measured carrier curve is close to a straight line:
OPM `TL` loses about 0.75 dB per step, while Type P.fm1 `level` loses about 0.25 dB
per step. Within the overlap the mapping is:

| OPM `TL` | Type P.fm1 `level` | Attenuation |
| --- | --- | --- |
| 0 | 99 | 0 dB |
| 8 | 75 | -6 dB |
| 16 | 51 | -12 dB |
| 24 | 27 | -18 dB |
| 32 | 3 | -24 dB |
| 33 and above | 0 | silent |

The practical formula is `level = 99 - 3 * TL`, clamped to 0 to 99. Type P.fm1 runs
out of range above about `TL` 33, where OPM is still audible. A carrier at `TL` 40 is
roughly -30 dB in OPM and silent in Type P.fm1 at level 0. If that quiet tail
matters, you need a different gain stage or you accept the difference.

Modulators do not follow the same curve. Type P.fm1's generated router scales the
modulator path by 2, about 6 dB relative to the carrier, and its phase-modulation index
changes at a different rate per level step. In a two-operator test at ratio 1:1, OPM
`TL` 0 through 32 all wanted Type P.fm1 level 99, while `TL` 40 wanted level 80, `TL`
48 wanted level 30, and `TL` 64 wanted level 5. The spectral distance stayed large
even at the best match, so treat the carrier formula as a starting point and tune the
modulator against the spectrum or by ear.

## Feedback

OPM feedback is the `FL` field on M1, with 0 to 7. Type P.fm1 has
`op1_feedback.p0` from 0 to 32767. The two scales are not the same. With a two-
operator patch and feedback on the modulator, OPM `FL` 7 produced a spectral centroid
of 1099 Hz. Type P.fm1 at 100% feedback produced 389 Hz with the mapped modulator
level, and 761 Hz with the modulator raised to 99. OPM stays brighter in both cases.

The harmonic balance also changes. OPM was odd-heavy in the test, with an odd-to-even
ratio of +8.1 dB. Type P.fm1 at the bright setting was even-heavy, at -4.2 dB. Start
at 32767 for `FL` 7, then raise the modulator level and listen for the point where
the edge appears. The two synths will not match harmonic for harmonic.

## Envelope

The envelope fields map by job: `AR` to `attack` or `opN.eg.r1`, `D1R` to
`opN.eg.r2`, `D1L` to `opN.eg.l2`, `D2R` to `opN.eg.r3`, and `RR` to `release` or
`opN.eg.r4`. The rates and curves are different, so the numbers are a starting point.

A measured pluck with `AR` 31, `D1R` 10, `D1L` 8, `D2R` 4, and `RR` 8 fell from
-24.9 dB to -37.0 dB over the first 0.8 s. The first Type P.fm1 setting, with `r2`
40, `r3` 20, `l2` 70, and `l3` 40, fell from -16.3 dB to -19.4 dB over the same
time. The Type P.fm1 envelope sustained more, so adjust `r2`, `r3`, `l2`, and `l3`,
or shorten the note. OPM rates are also key-scaled, which Type P.fm1 models with the
envelope key-follow controls rather than the rate number itself.

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

The cases below use the same note and the same operator ratios. The Type P.fm1
"nominal" column uses the `level = 99 - 3 * TL` mapping. The "bright" column raises
the modulator levels to 99.

| Case | OPM centroid | Type P.fm1 centroid | Result |
| --- | --- | --- | --- |
| Additive algorithm 7 | 454 Hz | 408 Hz | close |
| Serial algorithm 0 | 1849 Hz | 970 Hz nominal, 1489 Hz bright | topology matches, OPM is brighter |
| Parallel algorithm 4 | 1950 Hz | 652 Hz nominal, 734 Hz bright | topology matches, OPM is much brighter |
| Feedback, `FL` 7 | 1099 Hz | 389 Hz at level 51, 761 Hz at level 99 | OPM is brighter, harmonic balance differs |
| Envelope pluck | -24.9 to -37.0 dB | -16.3 to -19.4 dB | OPM decays more |

The additive case is the closest because there is no modulation index to match. The
serial and parallel cases show the real limit: the operator graph maps, but the OPM
modulation index is hotter than Type P.fm1 can reach at the same nominal level.

## Conversion recipe

1. Start from an init patch. Set `level.p1=0` and `op1_mute.p1` through
   `op4_mute.p1` to 1, so only part 1 sounds.
2. Set `op1_waveform.p0` through `op4_waveform.p0` to 0. This page assumes sine
   operators only.
3. Set `filter_on=0`, `filter2_on=0`, `fold_on=0`, and `fold=0`.
4. Assign OPM `M1`, `C1`, `M2`, `C2` to Type P.fm1 `O1`, `O2`, `O3`, `O4`.
5. Set `algorithm.p0` from `CON`. Use the table above and expect algorithm 3 to be
   approximate.
6. Set each ratio from `MUL`, folding `DT2` into the ratio if it is not zero.
7. Set each carrier level with `99 - 3 * TL`, clamped to 0 to 99. Start modulators
   at the same value and tune them against the spectrum.
8. Set `op1_feedback.p0` from `FL`, starting at 32767 for `FL` 7.
9. Map the envelope rates and levels, then adjust `r2`, `r3`, `l2`, and `l3` until
   the decay sits where you want it.
10. Play the same note through both patches and compare the first few harmonics.
    The useful goal is the same ratios, the same algorithm, and a similar
    brightness. The two synths will not null.

## Remaining differences

The two engines differ in the phase-modulation index scale, the phase relationship
between carrier and modulator, the level taper, the envelope timing, the feedback
depth, and the LFO ranges. Type P.fm1 also has no noise generator and no per-voice
pan. A conversion can preserve the operator graph and the ratio relationships, and
it can get close on the level curve, but the spectrum will not be identical. That is
expected. The two chips share a family resemblance, but they are different designs.
