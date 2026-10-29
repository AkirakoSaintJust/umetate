/* Q32 phase accumulator. `inc` (note-derived) is the pitch; `pitch` (control, Q15)
   scales it — full-scale = ±1 octave, i.e. `inc * (1 + pitch/32768)` (the vibrato
   input). The pitch-scaled increment is block-constant (`inc` is note-derived,
   `pitch` is control-rate), so it is recomputed once per block into `${state.step}`
   (the node's `block_derived`) — the per-sample body is just the add. `fm` (audio,
   Q15) is scaled <<16 — full-scale = ±π phase (the FM index); `mod` (control) is a
   small additive offset. The whole sum is int64 then cast to uint32, so the
   `fm << 16` of a negative (bipolar) modulator is well-defined. */
uint32_t ${out.phase} = (uint32_t)(
    (int64_t)${state.phase}
    + (int64_t)${state.step}
    + ((int64_t)${in.fm} << 16)
    + (int64_t)${in.mod}
);
${state.phase} = ${out.phase};
