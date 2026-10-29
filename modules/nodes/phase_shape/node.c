/* Vector phaseshaping (VPS, DAFx-11): one 2-D inflection point (d, v) bends the
   phase ramp [0,1) -> [0,v) then [v,1). `v` may exceed [0,1]; the uint32 cast wraps
   the shaped phase past the wavecycle (v<0 wraps backward). Slopes s0=v/d and
   s1=(1-v)/(1-d) are block_derived (control-rate). */
uint32_t p = ${in.phase} >> 17;   /* phase fraction, Q15 */
int32_t q = (p < (uint32_t)${state.d_c})
    ? fm1_q15_mul((int32_t)p, ${state.s0})
    : (int32_t)${in.v} + fm1_q15_mul((int32_t)(p - (uint32_t)${state.d_c}), ${state.s1});
uint32_t ${out.phase} = (uint32_t)((int64_t)q * 131072);   /* Q15 -> Q32 (wraps) */
