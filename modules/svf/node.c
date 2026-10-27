/* Chamberlin state-variable filter. `f` = 2*sin(pi*fc/fs) (Q16), `q` = damping
   (Q16), state `low`/`band` (Q15, saturating). low += f*band; high = in - low -
   q*band; band += f*high. */
${state.low} = fm1_sat_add32(${state.low}, fm1_q16_mul(${param.f}, ${state.band}));
int32_t ${out.high} = ${in.audio} - ${state.low} - fm1_q16_mul(${param.q}, ${state.band});
${state.band} = fm1_sat_add32(${state.band}, fm1_q16_mul(${param.f}, ${out.high}));
int32_t ${out.low} = ${state.low};
int32_t ${out.band} = ${state.band};
