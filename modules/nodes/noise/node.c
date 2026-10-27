/* xorshift32 white noise (bounded, no heap). */
${state.lfsr} ^= ${state.lfsr} << 13;
${state.lfsr} ^= ${state.lfsr} >> 17;
${state.lfsr} ^= ${state.lfsr} << 5;
int32_t ${out.audio} = (int32_t)(${state.lfsr} >> 8);
