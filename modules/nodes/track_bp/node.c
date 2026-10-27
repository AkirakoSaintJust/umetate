/* note-tracked state-variable band-pass. `f` = 2*sin(pi*f_note/fs) (note_cutoff). */
${state.low} = fm1_sat_add32(${state.low}, fm1_q16_mul(${state.f}, ${state.band}));
int32_t high = ${in.audio} - ${state.low} - fm1_q16_mul(${param.res}, ${state.band});
${state.band} = fm1_sat_add32(${state.band}, fm1_q16_mul(${state.f}, high));
int32_t ${out.audio} = ${state.band};
