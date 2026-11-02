/* Q32 phase accumulator with octave/semi/cent tuning (note-derived). `inc` is
   note-derived: note increment × 2^(octave + semi/12 + cent/1200). `pitch` (control,
   Q15) scales it — full-scale = ±1 octave (the vibrato input); the pitch-scaled
   increment is block-constant, so it is recomputed once per block into `${state.step}`
   (the node's `block_derived`) — the per-sample body is just the add.

   `fm` (audio, Q15) is a *phase offset* scaled by 2^16 (full-scale = ±π, the FM
   index) and `mod` (control) is a small additive offset — both apply to the readout
   phase only. The accumulator advances by `step` alone; accumulating `fm` would be
   frequency modulation, not the Yamaha phase modulation (it detunes the carrier with
   any modulator DC and lets feedback settle on a DC fixed point).

   32-bit arithmetic throughout: `(uint32_t)fm << 16` is the exact two's-complement
   `fm * 65536` (Q15 → Q31, fits int32), and the phase sums are plain mod-2³² uint32
   additions — the old int64 form truncates to the same low 32 bits, so this is
   bit-exact without the 64-bit ops.

   `mip` (the band-limited table level) is block-constant (block_derived), so it is
   copied to its output here. */
uint32_t ${out.phase} = ${state.phase} + ((uint32_t)${in.fm} << 16) + (uint32_t)${in.mod};
${state.phase} += ${state.step};
uint32_t ${out.mip} = ${state.mip};
