/* xorshift32 white noise (bounded, no heap), Q15 ±32768. The LFSR is zero at
   reset and 0 is a fixed point, so self-seed once on the first sample. */
if (!${state.lfsr}) ${state.lfsr} = 0x9E3779B9u;
${state.lfsr} ^= ${state.lfsr} << 13;
${state.lfsr} ^= ${state.lfsr} >> 17;
${state.lfsr} ^= ${state.lfsr} << 5;
int32_t ${out.audio} = (int32_t)(${state.lfsr} >> 16) - 32768;
