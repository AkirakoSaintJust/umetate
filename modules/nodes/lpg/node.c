/* vactrol low-pass gate: a fast-attack / slow-decay envelope (`level`, Q15) drives
   both the one-pole cutoff and the VCA gain, so the sound gets quieter *and*
   darker as it closes, which gives the "woody" pluck. */
if (${in.gate}) {
    ${state.level} += ${param.attack};
    if (${state.level} > 32767) ${state.level} = 32767;
} else {
    ${state.level} -= fm1_q16_mul(${param.release}, ${state.level});
    if (${state.level} < 0) ${state.level} = 0;
}
${state.z1} += fm1_q15_mul(${state.level}, ${in.audio} - ${state.z1});
int32_t ${out.audio} = fm1_q15_mul(${state.level}, ${state.z1});
