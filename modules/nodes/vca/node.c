/* gain cell: audio × cv × level_eff (Q15). The level is pushed toward 0/32767 by
   a key-follow factor `k` (Q15), and the effective level is block-derived. When
   `level_eff` is 0 (e.g. the per-op self-feedback with `feedback` = 0) the two
   multiplies are skipped, which is bit-exact because `fm1_q15_mul(x, 0)` = 0, and the
   block-constant condition is perfectly predicted. */
int32_t ${out.audio} = ${state.level_eff}
    ? fm1_q15_mul(fm1_q15_mul(${in.audio}, ${in.cv}), ${state.level_eff})
    : 0;
