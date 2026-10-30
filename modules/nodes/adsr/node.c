/* Linear ADSR (Q15, control rate). On the gate rising: attack (0 -> 32767); at the
   top: decay (32767 -> s); gate off: release (level -> 0). Rates are Q16 one-pole
   coefficients applied per control tick. `stage`: 0 attack, 1 decay, 2 sustain, 3 release. */
if (${in.gate}) {
    if (${state.stage} == 3u) { ${state.stage} = 0u; }
} else if (${state.stage} != 3u) {
    ${state.stage} = 3u;
}
if (${state.stage} == 0u) {
    ${state.level} += (int32_t)(((int64_t)(32767 - ${state.level}) * ${param.a}) >> 16);
    if (${state.level} >= 32760) { ${state.level} = 32767; ${state.stage} = 1u; }
} else if (${state.stage} == 1u) {
    ${state.level} -= (int32_t)(((int64_t)(${state.level} - ${param.s}) * ${param.d}) >> 16);
    if (${state.level} <= ${param.s} + 8) { ${state.level} = ${param.s}; ${state.stage} = 2u; }
} else if (${state.stage} == 2u) {
    ${state.level} = ${param.s};
} else {
    ${state.level} -= (int32_t)(((int64_t)${state.level} * ${param.r}) >> 16);
    if (${state.level} < 8) ${state.level} = 0;
}
${out.cv} = ${state.level};
