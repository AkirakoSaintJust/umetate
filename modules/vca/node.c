/* gain cell: Q15 multiply (audio * cv). */
int32_t ${out.audio} = fm1_q15_mul(${in.audio}, ${in.cv});
