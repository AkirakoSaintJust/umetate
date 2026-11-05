/* Q32 phase accumulator with octave/semi/cent tuning (note-derived). `inc` is
   note-derived: note increment × 2^(octave + semi/12 + cent/1200). `pitch` (control,
   Q15) scales it — full-scale = ±1 octave (the vibrato input); the pitch-scaled
   increment is block-constant, so it is recomputed once per block into `${state.step}`
   (the node's `block_derived`) — the per-sample body is just the add.

   `fm` (audio, Q15) is a *phase offset* scaled by 2^20, so full scale is eight
   cycles (16π, the FM index). `mod` (control) is a small additive offset — both
   apply to the readout phase only. The accumulator advances by `step` alone;
   accumulating `fm` would be frequency modulation, not the Yamaha phase
   modulation (it detunes the carrier with any modulator DC and lets feedback
   settle on a DC fixed point).

   32-bit arithmetic throughout: `(uint32_t)fm << 20` is `fm * 2^20` modulo 2^32,
   and the phase sums are plain mod-2³² uint32 additions. The wrap *is* the phase
   wrap, so losing the high bits is the intended behaviour.

   `mip` (the band-limited table level) is block-constant (block_derived), so it is
   copied to its output here. */
uint32_t ${out.phase} = ${state.phase} + ((uint32_t)${in.fm} << 20) + (uint32_t)${in.mod};
${state.phase} += ${state.step};
uint32_t ${out.mip} = ${state.mip};
