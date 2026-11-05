/* Q32 phase accumulator. `inc` (note-derived) is the pitch; `pitch` (control, Q15)
   scales it — full-scale = ±1 octave, i.e. `inc * (1 + pitch/32768)` (the vibrato
   input). `detune` (cents −50..50) adds an exact per-operator offset:
   `inc * (1 + (pitch + fm1_detune_pitch[detune+50])/32768)`. The pitch-scaled
   increment is block-constant (`inc` is note-derived, `pitch` is control-rate), so
   it is recomputed once per block into `${state.step}` (the node's `block_derived`)
   — the per-sample body is just the add.

   `fm` (audio, Q15) is a *phase offset* scaled by 2^20, so full scale is eight
   cycles (16π, the FM index); the router and the feedback tap feed it less than
   that. `mod` (control) is a small additive offset — both apply to the readout
   phase only. The accumulator advances by `step` alone: accumulating `fm` would
   integrate the modulator into the frequency (FM), which detunes the carrier with
   any modulator DC and lets a feedback loop settle on a DC fixed point. This is the
   Yamaha model: `out = wave(acc + modulator)`, `acc += step`.

   32-bit arithmetic throughout: `(uint32_t)fm << 20` is `fm * 2^20` modulo 2^32,
   and the phase sums are plain mod-2³² uint32 additions. The wrap *is* the phase
   wrap, so losing the high bits is the intended behaviour, and the per-sample body
   stays one add per input.

   `mip` (the band-limited table level) is block-constant (block_derived), so it is
   copied to its output here — the per-sample body stays the accumulator add, the
   FM offset add, and this copy. */
uint32_t ${out.phase} = ${state.phase} + ((uint32_t)${in.fm} << 20) + (uint32_t)${in.mod};
${state.phase} += ${state.step};
uint32_t ${out.mip} = ${state.mip};
