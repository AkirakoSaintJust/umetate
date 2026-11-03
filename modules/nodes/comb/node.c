/* Feedback comb filter: a fractional delay line + damped feedback + dry/wet mix.
   `freq` is the cutoff as a Q32 rate (Hz); the block-derived `dly` is the delay in
   Q16 samples (fs/freq). The read interpolates linearly between the two nearest
   taps; `tone` is the one-pole damping coefficient in the feedback path (0 = dark,
   32767 = bright); `res` is the feedback amount; `mix` crossfades the dry input and
   the wet comb signal. The wet signal is saturated to Q15 before it is written, so
   the line can never overflow. */
int32_t ${out.out};
${out.out} = ${state.buf}[(${state.idx} - (${state.dly} >> 16)) & ${const.mask}]
    + fm1_q16_mul(
        ${state.buf}[(${state.idx} - (${state.dly} >> 16) - 1u) & ${const.mask}]
        - ${state.buf}[(${state.idx} - (${state.dly} >> 16)) & ${const.mask}],
        (int32_t)(${state.dly} & 0xFFFFu));
${state.lp} = ${state.lp} + fm1_q15_mul(${param.tone}, ${out.out} - ${state.lp});
${out.out} = ${in.in} + fm1_q15_mul(${param.res}, ${state.lp});
if (${out.out} > 32767) ${out.out} = 32767;
else if (${out.out} < -32768) ${out.out} = -32768;
${state.buf}[${state.idx}] = (int16_t)${out.out};
${state.idx} = (${state.idx} + 1u) & ${const.mask};
${out.out} = ${in.in} + fm1_q15_mul(${param.mix}, ${out.out} - ${in.in});
