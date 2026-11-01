/* Yamaha total-level gain: audio × cv × gain(level_eff). `level` is 0..99, pushed
   toward 0/99 by a key-follow factor `k` (Q15) — the effective level is
   block-derived. Shifted >> 2 for the −12 dB single-operator headroom. */
int32_t ${out.audio} = fm1_q15_mul(
    fm1_q15_mul(${in.audio}, ${in.cv}),
    fm1_level_gain[${state.level_eff}] >> 2
);
