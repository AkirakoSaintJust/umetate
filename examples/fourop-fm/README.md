# Worked example: fourop-fm (4-op Yamaha FM)

This worked example puts the framework through a complete four-operator FM
synth, documented in `docs/roadmap.md` §6.9. The instrument follows the OPZ/DX21
lineage and includes per-operator and carrier feedback, seven runtime-selectable
algorithms, rate/level envelopes, and 12 waveforms. It also has a shared pitch LFO
and pitch envelope, plus an amplitude LFO for each operator.

## 1. The synth

- **Voice (8 voices):** four `fm_op` operators, each built from `phasor → osc →
  dx_env → vca`, with one-sample self-feedback and a tremolo LFO. Four `delay1`
  nodes provide the feedback paths, and a `route` node applies the selected
  algorithm's routing matrix at runtime. Because modulation reads delayed outputs,
  the graph stays acyclic for every algorithm. The `algo` node selects the matrix
  and routes the HOME `feedback` control to the carrier.
- **Global:** the carrier sum passes through an `svf` low-pass and `wavefolder`
  before `out`. A shared `plfo` (vibrato) and `penv` (pitch envelope) feed each
  operator's `pitch` through `csum`.
- **Algorithms:** seven rows from ymfm's `s_algorithm_ops`: {0, 1, 2, 4, 5, 6,
  7}. Algorithm 3 is omitted because it mirrors algorithm 2; see
  `dsp-algorithm.md`.

## 2. Files

| File | What it holds |
| --- | --- |
| `patch.json` | the declarative synth (voice/global zones, 39 friendly params, the `routing` table) |
| `panel.json` | the UI (`home` + `op` + `fx` + `glo` contexts) |
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
python3 -m umetate.test_generate     # renders the patch + resolves the panel
umetate build                        # generate dsp.c + build the firmware (needs the toolchain)
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
5. **Velocity is unwired (deferred).** Like the pocket-drone, the operator VCA
   doesn't take the allocator's `velocity`; scaling it is a follow-up.
6. **Control-rate LFO (shipped).** Each tick, the `lfo` node advances by
   `rate × CONTROL_BLOCK`, using the macro emitted by the generator. Its phase is
   therefore measured in samples, and its output holds for one sub-block. This
   works for sub-audio rates without adding per-sample work. The pitch LFO is a
   global scalar computed before the voice loop; tremolo LFOs run per voice.
   **Vibrato scales `inc`, not phase.** The `phasor`'s `pitch` input applies
   `inc × (1 + pitch/32768)`, producing a relative pitch change (constant cents
   across the keyboard) rather than the absolute-Hz wobble from reusing `fm`.
7. **Twelve OPZ and OPL waveforms (shipped).** `fm1_sin_wave` provides the YM2414
   set from ymfm's `opz_registers` as waveforms 0–7: sine, the "trianglish" sin²,
   and their half-, double-, and rectified derivatives. Waveforms 8–11 add the
   OPL2/OPL3-only shapes: rectified `|sin|`, pulse, square, and saw. The chips share
   four waves and contribute four each (`docs/dsp-study.md` §2.7). See
   `dsp-algorithm.md` §`osc.waveform`.
