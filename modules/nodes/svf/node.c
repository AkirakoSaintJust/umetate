/* Chamberlin state-variable filter. `f` = 2*sin(pi*fc/fs) (Q16), `q` = damping
   (Q16), and the state `low`/`band` is Q15 and saturating. The body runs
   low += f*band, then high = in - low - q*band, then band += f*high. The combined
   cutoff `fc` (clamped) is block-derived, because it only depends on block-rate
   inputs, so the per-sample body just reads it. `type` picks LP/BP/HP for `out`,
   and `on` 0 bypasses with out = in. */
${state.low} = fm1_sat_add32(${state.low}, fm1_q16_mul(${state.fc}, ${state.band}));
int32_t ${out.high} = ${in.audio} - ${state.low} - fm1_q16_mul(${param.q}, ${state.band});
${state.band} = fm1_sat_add32(${state.band}, fm1_q16_mul(${state.fc}, ${out.high}));
int32_t ${out.low} = ${state.low};
int32_t ${out.band} = ${state.band};
int32_t ${out.out} = ${param.on}
    ? (${param.type} == 1u ? ${out.band} : ${param.type} == 2u ? ${out.high} : ${out.low})
    : ${in.audio};
