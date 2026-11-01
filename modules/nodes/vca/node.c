/* gain cell: audio × cv × level_eff (Q15). The level is pushed toward 0/32767 by
   a key-follow factor `k` (Q15) — the effective level is block-derived. */
int32_t ${out.audio} = fm1_q15_mul(fm1_q15_mul(${in.audio}, ${in.cv}), ${state.level_eff});
