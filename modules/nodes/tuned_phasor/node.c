/* Q32 phase accumulator with octave/semi/cent tuning (note-derived). `inc` is
   note-derived: note increment × 2^(octave + semi/12 + cent/1200). `pitch` (control,
   Q15) scales it — full-scale = ±1 octave (the vibrato input); the pitch-scaled
   increment is block-constant, so it is recomputed once per block into `${state.step}`
   (the node's `block_derived`) — the per-sample body is just the add. `fm` (audio,
   Q15) is scaled by 2^16 — full-scale = ±π phase (the FM index); `mod` (control) is a
   small additive offset. Multiplication (not `<< 16`) so a negative (bipolar)
   modulator is well-defined; the sum is int64 then cast to uint32. */
uint32_t ${out.phase} = (uint32_t)(
    (int64_t)${state.phase}
    + (int64_t)${state.step}
    + ((int64_t)${in.fm} * 65536)
    + (int64_t)${in.mod}
);
${state.phase} = ${out.phase};
