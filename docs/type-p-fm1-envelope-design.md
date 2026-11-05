# Type P.fm1 envelope design

Type P.fm1 gives every operator its own four-rate, three-level amplitude envelope,
plus key scaling, velocity, tremolo, and a part-level pitch envelope. That is a classic
FM envelope with per-operator expression, and it covers most of the sounds the
instrument is aiming at. It is not a modern multi-stage modulation envelope.

## Envelope controls

Each operator has four rates and three levels. The rates are attack or `r1`, `r2`,
`r3`, and release or `r4`. The levels are `l1`, `l2`, and `l3`. The envelope moves
through the levels on the way to the sustain stage, holds there while the key is
down, and then runs the release stage. On the parameter side, operator 1's first and
last rates appear as `attack.p0` and `release.p0`, while operators 2 to 4 use
`opN.eg.r1.p0` and `opN.eg.r4.p0`. The rest of the envelope is per operator.

The per-operator controls are:

- Four envelope rates and three envelope levels.
- Level key scaling, with separate low and high amounts around the breakpoint.
- Envelope-rate key scaling, with separate low and high amounts.
- Velocity to amplitude, velocity to FM depth, and velocity to envelope rate.
- Tremolo with its own rate, depth, and waveform.

The instrument also has a part-level pitch envelope with four rates, three levels,
key scaling, and velocity. That envelope is shared by the operators in the part.

## Stage lengths and curve shape

The envelope runs at the control rate, 32 frames per tick, so one tick is 0.73 ms
at 44.1 kHz. A stage moves the gain toward its level target with a one-pole step,
using the coefficient the rate selects. It ends when the gain is within 8 units of
the target, about 72 dB below full scale, so the times below run to the envelope's
own floor rather than to silence in the room.

| Rate | Coefficient | Time constant | Silence to level 99 | Level 99 to silence |
| ---: | ---: | ---: | ---: | ---: |
| 99 | 65536 | 0.7 ms | 0.7 ms | 0.7 ms |
| 96 | 13222 | 3.6 ms | 26.8 ms | 27.6 ms |
| 90 | 4096 | 11.6 ms | 92.2 ms | 93.6 ms |
| 80 | 1167 | 40.7 ms | 295.3 ms | 296.1 ms |
| 70 | 452 | 105.2 ms | 675.6 ms | 676.3 ms |
| 64 | 277 | 171.7 ms | 1,023.1 ms | 1,023.9 ms |
| 50 | 102 | 466.2 ms | 2,327.8 ms | 2,328.5 ms |
| 40 | 54 | 880.6 ms | 3,843.6 ms | 3,844.4 ms |
| 30 | 30 | 1,585.1 ms | 5,992.2 ms | 5,992.9 ms |
| 20 | 18 | 2,641.9 ms | 8,641.5 ms | 8,642.2 ms |
| 10 | 11 | 4,323.1 ms | 12,025.8 ms | 12,026.5 ms |
| 0 | 7 | 6,793.5 ms | 15,844.7 ms | 15,845.4 ms |

The shortest stage is one tick, 0.73 ms. A rate of 99 moves the whole span in one
step, so nothing can be quicker. The longest is 15.8 s at rate 0, which is long
enough for a slow swell on a held note and too long to release a voice in a dense
chord. The two ends are about 21,800 apart. Attack and decay take the same time
for the same span, because they use the same coefficient, and the release tracks
them within a millisecond.

Stage time is not the time constant. A plain one-pole needs about 8 time constants
to come within 8 units of its target, and the forced one-unit step shortens that
tail, so a full-scale stage runs for about 8 time constants at the fast end and
2.3 at the slow end. The 7 s figure beside rate 0 in the table generator is the
time constant.

The curve is fixed. Each tick moves a constant fraction of the remaining gain, so
the stage starts quickly and eases into its target. Measured at rate 50, the first
half of the gain span arrives in 14 percent of the stage time and the first 90
percent in 46 percent. On a 2.3 s attack, half the gain is in place after a third
of a second and 90 percent after about a second, so the stage reads faster than
its length suggests. A release to silence is an exponential decay, which is a
straight line in decibels until the remaining gain is small enough for the
one-unit step to take over. A decay to a sustain level flattens as it approaches
that level, which is the shape that makes an electric piano bark and then settle.

The one-unit floor also sets the slowest possible movement. At rate 0 a step of 1
unit per tick covers 4681 units in 3.4 s, so any move smaller than that runs at
one unit per tick whatever the exponential would do. One level step at the top of
the range is about 930 units and takes 0.68 s at rate 0. The floor keeps the
envelope converging instead of stalling, and it puts a hard lower bound on how
slowly a small level change can move.

## Strengths

The basic FM job is covered. A modulator envelope that falls makes the timbre soften
after the attack, while a carrier envelope shapes the volume. That is the core of
most FM sounds, from electric piano and bells to brass and pads. The per-operator
envelopes let you separate the attack transient from the body, for example a fast
modulator decay against a slow carrier.

The three levels and four rates are enough for a two-stage decay and a shaped
sustain, which is more than a plain ADSR and enough for acoustic-inspired FM. The
key scaling and velocity controls make the sound respond across the keyboard and to
touch, and the shared pitch envelope handles the attack pitch blip or the rising
brass gesture.

The per-operator velocity-to-FM-depth control is particularly useful. It lets a
harder note open the timbre without changing the carrier level, which is a common
way to make FM sounds feel expressive rather than static.

## Limits

The envelope cannot loop a section, so it will not produce the slow evolving or
rhythmic textures that a looping envelope gives you on held notes. It has no tempo
sync, so it cannot lock a rhythmic shape to the host. Modern FM synths such as FM7
and FM8 offer looped envelopes and tempo-synced breakpoints, and Aurora FM offers
six stages with selectable slopes. Type P.fm1 offers neither.

It also cannot make an arbitrary multi-stage shape. Three levels and four rates
cover a two-stage decay, but not a double-strike attack, a three-slope attack, or a
long chain of breakpoints. FM7 allows up to 31 breakpoints per envelope, with
independent slopes. The Type P.fm1 envelope also has fixed curves rather than a
choice of linear, logarithmic, or exponential segments.

The pitch envelope is shared by the operators in a part, so you cannot bend one
operator against another. The
Deep DX article on the DX7 makes the same point about Yamaha's global pitch
envelope, and calls per-operator pitch modulation the more useful design. Type P.fm1
has per-operator tremolo but not per-operator pitch envelopes.

There is no envelope delay or hold stage, and no separate envelope routed to FM
depth or another destination. The operator's amplitude envelope necessarily shapes
its modulation depth, but there is no free modulation matrix behind it.

## Verdict

For a four-operator FM instrument aimed at classic FM and hands-on sound design, the
envelopes are adequate. They are more flexible than a plain ADSR and more
per-operator than the OPM's five-parameter envelope. They are not a modern
modulation envelope, and a sound designer who wants looping, tempo-locked, or
multi-breakpoint shapes will run out of stages.

If the instrument grows a modulation matrix, the first additions should be a loop
mode and a per-operator pitch envelope. Those unlock movement and expression
without changing the core FM sound.

## Sources

- Sound on Sound, [More About Envelopes](https://www.soundonsound.com/techniques/more-about-envelopes).
- Sound on Sound, [Native Instruments FM7](https://www.soundonsound.com/reviews/native-instruments-fm7).
- YamahaSynth, [FM 101, Part Six: Complex Systems](https://yamahasynth.com/learn/synth-programming/fm-101-part-six-complex-systems/).
- YamahaSynth, [Manny's FM-Xpert #4: The Envelope(s), Please](https://yamahasynth.com/learn/montage-series-synthesizers/mannys-fm-xpert-4-the-envelopes-please/).
- The Introvert, [Deep DX, Part 4: Topology of a Sound](https://theintrovert.net/2024/02/21/deep-dx-part-4-topology-of-a-sound/).
- Audio Nebula, [Aurora FM Guide](https://www.audionebula.ca/aurora_fm_guide.html).
