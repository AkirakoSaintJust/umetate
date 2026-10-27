/* Q32 phase accumulator. `inc` (note-derived) is the pitch; `pitch` (control, Q15)
   scales it — full-scale = ±1 octave, i.e. `inc * (1 + pitch/32768)` (the vibrato
   input). `fm` (audio, Q15) is scaled <<16 — full-scale = ±π phase (the FM index);
   `mod` (control) is a small additive offset. */
uint32_t ${out.phase} = ${state.phase}
    + (uint32_t)(((int64_t)${state.inc} * (32768 + ${in.pitch})) >> 15)
    + (${in.fm} << 16) + ${in.mod};
${state.phase} = ${out.phase};
