/* sine wavefolder: dry/wet crossfade of the input into sin(pi * x). `amount` Q15:
   0 = dry, 32768 = full fold. Memoryless. */
int32_t folded = fm1_sin((uint32_t)((int64_t)${in.audio} * 65536));
int32_t ${out.audio} = ${in.audio} + fm1_q15_mul(${param.amount}, folded - ${in.audio});
