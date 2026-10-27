/* phase accumulator (Q32 wrapping). `fm` (audio, Q15) is scaled <<16 so a
   full-scale modulator = a ±π phase swing (the FM index); `mod` (control) is a
   small additive offset. */
uint32_t ${out.phase} = ${state.phase} + ${state.inc} + (${in.fm} << 16) + ${in.mod};
${state.phase} = ${out.phase};
