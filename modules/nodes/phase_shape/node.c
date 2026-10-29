/* Vector phaseshaping (VPS, DAFx-11): one 2-D inflection point (d, v) bends the
   phase ramp [0,1) -> [0,v) then [v,1). `v` > 1 wraps the shaped phase forward past
   the wavecycle (uint32); `v` < 0 is clamped to 0 in block_derived. Slopes s0=v/d
   and s1=(1-v)/(1-d) are block_derived (control-rate). */
uint32_t p = ${in.phase} >> 17;   /* phase fraction, Q15 */
int32_t q = (p < (uint32_t)${state.d_c})
    ? fm1_q15_mul((int32_t)p, ${state.s0})
    : (int32_t)${state.v_c} + fm1_q15_mul((int32_t)(p - (uint32_t)${state.d_c}), ${state.s1});
uint32_t ${out.phase} = (uint32_t)((int64_t)q * 131072);   /* Q15 -> Q32 (wraps) */
