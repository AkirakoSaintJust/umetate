# Worked example: Type P.fm1 (4-op Yamaha-style phase modulation)

Type P.fm1 is a worked example I made to put the framework through the process of
designing, implementing and publishing a complete two-part, four-operator FM synth,
and it corresponds to the **type-p-fm1 program** in `docs/roadmap.md` §6.11, with
the modules it shipped documented in §6.9. It's broadly inspired by the OPZ, OPL and
OPM/OPN/OPP (DX21, Mega Drive, etc) lineage, with some new features drawn from my
experience with those synths. It has per-operator feedback, eight algorithms,
rate/level envelopes, and 12 waveforms, plus a per-part pitch LFO, a per-note pitch
envelope, and an amplitude LFO for each operator. It builds into a full firmware with
**two independent timbres** (parts, channels 0/1), velocity, presets (128 single
parts+64 multi patches plus system settings), SysEx, and MIDI CC, sustain, panic,
and bend. The app glue `app.c` composes onto the frozen `rib.c` framework through
`umetate build --synth`.

## 1. Synth architecture

- **Voice (20 voices):** four `fm_op` operators, each built from `phasor → osc →
  dx_env → tl`, with one-sample self-feedback and a tremolo LFO. Four `delay1`
  nodes provide the feedback paths, and a `route` node applies the selected
  algorithm's routing matrix at runtime. Because modulation reads delayed outputs,
  the graph stays acyclic for every algorithm. The `algo` node selects the matrix
  at runtime.
- **Global:** the carrier sum passes through FILTER 1 (a `liquid_filter`
  ladder), the `wavefolder`, and FILTER 2 (a second `liquid_filter`) before
  `out`. A per-part `plfo` (vibrato) and a per-note `penv` (pitch envelope) feed
  each operator's `pitch` through `csum`.
- **Algorithms:** eight rows from ymfm's `s_algorithm_ops`: {0, 1, 2, 3, 4, 5, 6,
  7}, the full standard TX81Z/DX100/DX21 4-op set. See `dsp-algorithm.md`.

## 2. Files

| File | Contents |
| --- | --- |
| `patch.json` |  declarative synth definition (voice/global zones, the `routing` table, `parts: 2`, the `model` byte, the `cc:` list, 56 exposed params → 194 set_param ids) |
| `panel.json` | UI definition (`home` + `op` + `fx` + `glo` contexts) |
| `app.c` | framework-composed app glue (the `app_audio`/`app_main`/`app_idle` + service contexts) |
| `host-script.txt` | the host leg's script (notes on both parts, a CC, panic → WAV + screens) |
| `synth-brief.md` | synth design brief |
| `dsp-algorithm.md` | per-component math (dx_env, osc.waveform, routing, fm_op, lfo) |
| `code-structure.md` | description of the shipped nodes/macros + HAL helpers |
| `control-map.md` | UI interview (contexts, bindings, pages) |

The implementation is stored in `modules/nodes/` (`dx_env`, `mix4`,
`route4`, `route`, `algo`, `lfo`, `mute`, `gain`, `cmul`, `csum`, `pitch_env`),
`modules/macros/fm_op/`, and two helpers in `firmware/hal/fm1_math.h`:
`fm1_sin_wave` and `fm1_route4`.

## 3. Run

```sh
umetate deep-check --all                       # the gate (renders the patch, resolves the panel, runs the composition)
umetate build --synth examples/type-p-fm1       # compose + host run + target package (needs the toolchain)
umetate emu --check --mhz 240                  # boot the package, hold a chord (no halt, full-scale peak)
umetate preset export examples/type-p-fm1       # the 128+64 bank as .syx (import reverses it)
umetate budget examples/type-p-fm1/patch.json --voices 20   # the measured polyphony figure
```

## 4. Lessons drawn

Building the example exposed two bugs, both fixed, and a bunch of follow-up work.

1. **The `phasor` FM input was inaudible (fixed).** `fm` was added to the Q32
   phase unscaled, so a full-scale modulator swung the phase by ~1/65536 of a
   cycle. The `phasor` node now scales `fm << 16`, so full-scale = ±π (the FM
   index). See `dsp-algorithm.md` §`fm_op`.
2. **Five `route4` nodes wasn't the right architecture (fixed).** The plan's five
   `route4` instances would each carry their own `algorithm` param, five knobs
   for one selection. A single `route` node (one `algorithm`, four rows) replaced
   them. `route4` stays as the general primitive, and `route` is the ergonomic 4-op
   wrapper.
3. **Patch `params:` `default` is ignored (recorded).** `patch.schema.json`
   accepts a `default` on a param binding, but the generator uses the node
   param's literal as the DSP initial value. Recorded in the roadmap §6.9.
4. **The liquid ladder has a coefficient ceiling (recorded).** Above 55296 the
   feedback loop breaks into a parasitic oscillation at moderate resonance, so
   the node clamps there. The Type P.fm1 resonance knob tops out below the
   self-oscillation threshold, at the strongest stable resonance. Recorded in
   the roadmap §6.9.
5. **Velocity → amplitude/FM/envelope-rate is wired, defaulted off (shipped,
   F2).** The `fm_op` macro has `vel_amp`/`vel_fm`/`vel_rate` depths (the
   reserved `velocity` input), so velocity reaches the operators, but the
   test project sets each depth to 0 by default, so velocity is inaudible until set via
   `set_param` (`opN.velamp.depth` etc.). Not on the panel/CC surface.
6. **Control-rate LFO (shipped).** Each tick, the `lfo` node advances by
   `rate × CONTROL_BLOCK`, using the macro emitted by the generator. Its phase is
   therefore measured in samples, and its output holds for one sub-block. This
   works for sub-audio rates without adding per-sample work. The pitch LFO runs
   per voice (its rate/depth are per-part params). Tremolo LFOs run per voice.
   **Vibrato scales `inc`, not phase.** The `phasor`'s `pitch` input applies
   `inc × (1 + pitch/32768)`, producing a relative pitch change (constant cents
   across the keyboard) rather than the absolute-Hz wobble from reusing `fm`.
7. **Twelve OPZ and OPL waveforms (shipped).** `fm1_sin_wave` provides the YM2414
   set from ymfm's `opz_registers` as waveforms 0–7: sine, the "trianglish" sin²,
   and their half-, double-, and rectified derivatives. Waveforms 8–11 add the
   OPL2/OPL3-only shapes: rectified `|sin|`, pulse, square, and saw. The chips share
   four waves and contribute four each (`docs/dsp-study.md` §2.7). See
   `dsp-algorithm.md` §`osc.waveform`.
