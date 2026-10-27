# Worked example: fourop-fm (4-op Yamaha FM)

A committed end-to-end dogfood (`docs/roadmap.md` §6.9) that exercises the
framework and surfaces gaps: a 4-operator FM synth in the OPZ/DX21 lineage, with
**per-operator feedback**, **7 runtime-selectable algorithms**, **rate/level
envelopes**, **8 operator waveforms**, one **global pitch LFO**, and one
**amplitude LFO per operator**.

## 1. The synth

- **Voice** (8 voices): four `fm_op` operators (`phasor → osc → dx_env → vca`,
  each with 1-sample self-feedback + a per-op tremolo LFO) + four `delay1` + one
  `route`. Every modulation reads the 1-sample-delayed output of its sources, so
  the graph is acyclic for *every* algorithm; the algorithm is a `tables:`
  routing matrix the `route` node applies at runtime.
- **Global:** carrier sum → `svf` low-pass → `wavefolder` → master `vca`, plus
  the shared `plfo` (pitch/vibrato) whose `cv` feeds every operator's `pitch`.
- **Algorithms:** the 7 rows of ymfm's `s_algorithm_ops` {0,1,2,4,5,6,7}
  (algorithm 3 dropped as algorithm 2's mirror — see `dsp-algorithm.md`).

## 2. Files

| File | What it holds |
| --- | --- |
| `patch.json` | the declarative synth (voice/global zones, 26 friendly params, the `routing` table) |
| `panel.json` | the UI (`home` + `op` + `lfo` contexts) |
| `synth-brief.md` | the instrument brief (source of truth for the above) |
| `dsp-algorithm.md` | the per-component math (dx_env, osc.waveform, routing, fm_op, lfo) |
| `code-structure.md` | the nodes/macros + HAL helpers the dogfood shipped |
| `control-map.md` | the UI interview (contexts, bindings, pages) |

The dogfood shipped library code in `modules/nodes/` (`dx_env`, `mix4`, `route4`,
`route`, `lfo`), `modules/macros/fm_op/`, and two helpers in
`firmware/hal/fm1_math.h` (`fm1_sin_ws`, `fm1_route4`).

## 3. Run

```sh
python3 -m umetate.test_generate     # renders the patch + resolves the panel
umetate build                        # generate dsp.c + build the firmware (needs the toolchain)
```

## 4. Lessons (what the example exposed)

The dogfood did its job — it surfaced two bugs (fixed) and several gaps
(recorded, not fixed here):

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
6. **The LFO is a control-rate accumulator (shipped).** The `lfo` node advances
   `rate × CONTROL_BLOCK` per tick (the emitted `CONTROL_BLOCK` macro), so the
   phase increments in sample units and the output is a per-sub-block held value
   — smooth for sub-audio rates, no per-sample cost. The pitch LFO is a *global*
   control-rate node (scalar, computed before the voice audio loop, so it can feed
   the operators); the tremolo LFOs are per-voice. **Vibrato scales `inc`, not
   phase:** the `phasor` gained a `pitch` input (`inc × (1 + pitch/32768)`), so
   vibrato is *relative* — constant cents across the keyboard — rather than the
   absolute-Hz wobble you'd get by reusing `fm`.
7. **The OPZ's exact 8-waveform mask (deferred).** `fm1_sin_ws` implements the
   OPL/OPZ bit-trick scheme with the OPL's mask table; the OPZ's exact 8 are a
   documented follow-up in `dsp-algorithm.md`.
