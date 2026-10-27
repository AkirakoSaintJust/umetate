/* one-pole lowpass (Q15): z1 = z1 + cutoff * (in - z1). */
int32_t ${out.audio} = ${state.z1} + fm1_q15_mul(${param.cutoff}, ${in.audio} - ${state.z1});
${state.z1} = ${out.audio};
