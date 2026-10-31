/* Yamaha total-level gain: audio × cv × gain(level). `level` is 0..99, mapped by
   `fm1_level_gain` (0.25 dB/step: 99 = max, 50 ≈ −12 dB, 0 = silence) and shifted
   >> 2 for the −12 dB single-operator headroom. */
int32_t ${out.audio} = fm1_q15_mul(
    fm1_q15_mul(${in.audio}, ${in.cv}),
    fm1_level_gain[${param.level}] >> 2
);
