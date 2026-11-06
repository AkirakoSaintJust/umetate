/* Yamaha total-level gain: audio × cv × gain(level_eff). `level` is 0..99, pushed
   toward 0/99 by a key-follow factor `k` (Q15), and the effective level is
   block-derived. The result is shifted >> 2 for the −12 dB single-operator
   headroom. When `level_eff` (the 0..99 level) is 0 the operator is silent, so the
   two multiplies are skipped. That is bit-exact because `fm1_level_gain[0] >> 2` =
   0. The block-constant condition is perfectly predicted. */
int32_t ${out.audio} = ${state.level_eff}
    ? fm1_q15_mul(fm1_q15_mul(${in.audio}, ${in.cv}), fm1_level_gain[${state.level_eff}] >> 2)
    : 0;
