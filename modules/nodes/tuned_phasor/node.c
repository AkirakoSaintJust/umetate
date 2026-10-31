/* Q32 phase accumulator with octave/semi/cent tuning (note-derived). `inc` is
   note-derived: note increment × 2^(octave + semi/12 + cent/1200). `pitch` (control,
   Q15) scales it — full-scale = ±1 octave (the vibrato input); the pitch-scaled
   increment is block-constant, so it is recomputed once per block into `${state.step}`
   (the node's `block_derived`) — the per-sample body is just the add.

   `fm` (audio, Q15) is a *phase offset* scaled by 2^16 (full-scale = ±π, the FM
   index) and `mod` (control) is a small additive offset — both apply to the readout
   phase only. The accumulator advances by `step` alone; accumulating `fm` would be
   frequency modulation, not the Yamaha phase modulation (it detunes the carrier with
   any modulator DC and lets feedback settle on a DC fixed point). Multiplication
   (not `<< 16`) so a negative (bipolar) modulator is well-defined. */
uint32_t ${out.phase} = (uint32_t)(
    (int64_t)${state.phase}
    + ((int64_t)${in.fm} * 65536)
    + (int64_t)${in.mod}
);
${state.phase} = (uint32_t)((int64_t)${state.phase} + (int64_t)${state.step});
