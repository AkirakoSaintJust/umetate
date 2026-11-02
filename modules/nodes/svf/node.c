/* Chamberlin state-variable filter. `f` = 2*sin(pi*fc/fs) (Q16), `q` = damping
   (Q16), state `low`/`band` (Q15, saturating). low += f*band; high = in - low -
   q*band; band += f*high. The combined cutoff `fc` (clamped) is block-derived (it
   only depends on block-rate inputs), so this per-sample body just reads it; `type`
   picks LP/BP/HP for `out`; `on` 0 bypasses (out = in). */
${state.low} = fm1_sat_add32(${state.low}, fm1_q16_mul(${state.fc}, ${state.band}));
int32_t ${out.high} = ${in.audio} - ${state.low} - fm1_q16_mul(${param.q}, ${state.band});
${state.band} = fm1_sat_add32(${state.band}, fm1_q16_mul(${state.fc}, ${out.high}));
int32_t ${out.low} = ${state.low};
int32_t ${out.band} = ${state.band};
int32_t ${out.out} = ${param.on}
    ? (${param.type} == 1u ? ${out.band} : ${param.type} == 2u ? ${out.high} : ${out.low})
    : ${in.audio};
