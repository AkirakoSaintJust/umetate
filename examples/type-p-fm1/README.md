# Worked example: Type P.fm1 (4-op Yamaha FM)

This worked example puts the framework through a complete four-operator FM
synth — the **type-p-fm1 program** in `docs/roadmap.md` §6.11 (the modules it
shipped are documented in §6.9). The instrument follows the OPZ/DX21 lineage and
includes per-operator feedback, eight runtime-selectable algorithms,
rate/level envelopes, and 12 waveforms. It also has a per-part pitch LFO and a
per-note pitch envelope, plus an amplitude LFO for each operator. It builds into
a full
firmware: **two independent timbres** (parts, channels 0/1), velocity, presets
(128+64 + settings), SysEx, and MIDI CC/sustain/panic/bend, composed from the app
glue `app.c` onto the frozen `rib.c` framework (`umetate build --synth`).

## 1. The synth

- **Voice (20 voices):** four `fm_op` operators, each built from `phasor → osc →
  dx_env → tl`, with one-sample self-feedback and a tremolo LFO. Four `delay1`
  nodes provide the feedback paths, and a `route` node applies the selected
  algorithm's routing matrix at runtime. Because modulation reads delayed outputs,
  the graph stays acyclic for every algorithm. The `algo` node selects the matrix
  at runtime.
- **Global:** the carrier sum passes through an `svf` low-pass and `wavefolder`
  before `out`. A per-part `plfo` (vibrato) and a per-note `penv` (pitch
  envelope) feed each operator's `pitch` through `csum`.
- **Algorithms:** eight rows from ymfm's `s_algorithm_ops`: {0, 1, 2, 3, 4, 5, 6,
  7} — the full standard TX81Z/DX100/DX21 4-op set; see `dsp-algorithm.md`.

## 2. Files

| File | What it holds |
| --- | --- |
| `patch.json` | the declarative synth (voice/global zones, the `routing` table, `parts: 2`, the `model` byte, the `cc:` list — 56 exposed params → 194 set_param ids) |
| `panel.json` | the UI (`home` + `op` + `fx` + `glo` contexts) |
| `app.c` | the app glue (the `app_audio`/`app_main`/`app_idle` + service contexts) the framework composes |
| `host-script.txt` | the host leg's script (notes on both parts, a CC, panic → WAV + screens) |
| `synth-brief.md` | the instrument brief (source of truth for the above) |
| `dsp-algorithm.md` | the per-component math (dx_env, osc.waveform, routing, fm_op, lfo) |
| `code-structure.md` | the nodes/macros + HAL helpers the dogfood shipped |
| `control-map.md` | the UI interview (contexts, bindings, pages) |

The example's implementation lives in `modules/nodes/` (`dx_env`, `mix4`,
`route4`, `route`, `algo`, `lfo`, `mute`, `gain`, `cmul`, `csum`, `pitch_env`),
`modules/macros/fm_op/`, and two helpers in `firmware/hal/fm1_math.h`:
`fm1_sin_wave` and `fm1_route4`.

## 3. Run

```sh
umetate deep-check --all                       # the gate (renders the patch, resolves the panel, runs the composition)
umetate build --synth examples/type-p-fm1       # compose + host run + target package (needs the toolchain)
umetate emu --check --mhz 240                  # boot the package, hold a chord (no halt, full-scale peak)
umetate preset export examples/type-p-fm1       # the 128+64 bank as .syx (import reverses it)
umetate budget examples/type-p-fm1/patch.json --voices 20   # the measured polyphony claim
```

## 4. Lessons (what the example exposed)

Building the example exposed two bugs, both fixed, and several follow-up items.
The list below notes whether each is recorded, deferred, or shipped:

1. **The `phasor` FM input was inaudible (fixed).** `fm` was added to the Q32
   phase unscaled, so a full-scale modulator swung the phase by ~1/65536 of a
   cycle. The `phasor` node now scales `fm << 16`, so full-scale = ±π (the FM
   index). See `dsp-algorithm.md` §`fm_op`.
2. **Five `route4` nodes was the wrong shape (fixed).** The plan's five
   `route4` instances would each carry their own `algorithm` param — five knobs
   for one selection. A single `route` node (one `algorithm`, four rows) replaced
   them. `route4` stays as the general primitive; `route` is the ergonomic 4-op
   wrapper.
3. **Patch `params:` `default` is ignored (recorded).** `patch.schema.json`
   accepts a `default` on a param binding, but the generator uses the node
   param's literal as the DSP initial value. Recorded in the roadmap §6.9.
4. **`svf` has a sub-LSB limit cycle (recorded).** The Chamberlin SVF never
   reaches *exactly* zero after the input stops (≈ −80 dBFS), so a post-voice
   filter fails the strict "silent after off" host contract. The dogfood uses a
   decay-to-near-silence contract. Recorded in the roadmap §6.9.
5. **Velocity → amplitude/FM/envelope-rate is wired, defaulted off (shipped,
   F2).** The `fm_op` macro has `vel_amp`/`vel_fm`/`vel_rate` depths (the
   reserved `velocity` input), so velocity reaches the operators — but the
   dogfood defaults each depth to 0, so velocity is inaudible until set via
   `set_param` (`opN.velamp.depth` etc.). Not on the panel/CC surface.
6. **Control-rate LFO (shipped).** Each tick, the `lfo` node advances by
   `rate × CONTROL_BLOCK`, using the macro emitted by the generator. Its phase is
   therefore measured in samples, and its output holds for one sub-block. This
   works for sub-audio rates without adding per-sample work. The pitch LFO runs
   per voice (its rate/depth are per-part params); tremolo LFOs run per voice.
   **Vibrato scales `inc`, not phase.** The `phasor`'s `pitch` input applies
   `inc × (1 + pitch/32768)`, producing a relative pitch change (constant cents
   across the keyboard) rather than the absolute-Hz wobble from reusing `fm`.
7. **Twelve OPZ and OPL waveforms (shipped).** `fm1_sin_wave` provides the YM2414
   set from ymfm's `opz_registers` as waveforms 0–7: sine, the "trianglish" sin²,
   and their half-, double-, and rectified derivatives. Waveforms 8–11 add the
   OPL2/OPL3-only shapes: rectified `|sin|`, pulse, square, and saw. The chips share
   four waves and contribute four each (`docs/dsp-study.md` §2.7). See
   `dsp-algorithm.md` §`osc.waveform`.
