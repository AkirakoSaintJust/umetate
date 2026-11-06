/* Classic phase distortion: the VPS inflection with v=0.5 fixed, with a bend at x=`d`
   distorts the phase ramp along x only. Slopes s0=0.5/d and s1=0.5/(1-d) are
   block_derived (control-rate). */
uint32_t p = ${in.phase} >> 17;   /* phase fraction, Q15 */
int32_t q = (p < (uint32_t)${state.d_c})
    ? fm1_q15_mul((int32_t)p, ${state.s0})
    : 16384 + fm1_q15_mul((int32_t)(p - (uint32_t)${state.d_c}), ${state.s1});
uint32_t ${out.phase} = (uint32_t)q << 17;   /* Q15 -> Q32, two's-complement shift (wraps) */
