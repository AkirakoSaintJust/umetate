/* gain cell: Q15 multiply (audio * cv * level). */
int32_t ${out.audio} = fm1_q15_mul(fm1_q15_mul(${in.audio}, ${in.cv}), ${param.level});
