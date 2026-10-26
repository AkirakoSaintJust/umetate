/* phase accumulator (Q32 wrapping). fm (audio) and mod (control) are additive. */
uint32_t ${out.phase} = ${state.phase} + ${state.inc} + ${in.fm} + ${in.mod};
${state.phase} = ${out.phase};
