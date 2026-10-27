/* xorshift32 white noise (bounded, no heap), Q15 ±32768. */
${state.lfsr} ^= ${state.lfsr} << 13;
${state.lfsr} ^= ${state.lfsr} >> 17;
${state.lfsr} ^= ${state.lfsr} << 5;
int32_t ${out.audio} = (int32_t)(${state.lfsr} >> 16) - 32768;
