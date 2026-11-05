/* Self-feedback tap: `(x[n] + x[n-1]) / 2 * level`, gated on `level_eff` so a
   patch with no feedback pays nothing. The two-sample average is the OPM's
   `(o + Inp_last) >> Fl`. Its zero at Nyquist is the point: a one-sample
   feedback loop with no damping can ring at the top of the band. Halving each
   sample before the add keeps the sum inside the Q15 range, and the truncation
   loses at most one LSB on an odd sample. While the tap is gated the state holds
   its last value, so the first samples after turning feedback up fade in from
   the previous setting instead of jumping from zero. */
int32_t ${out.audio} = 0;
if (${state.level_eff}) {
    int32_t half = ${in.audio} >> 1;
    ${out.audio} = fm1_q15_mul(half + ${state.prev}, ${state.level_eff});
    ${state.prev} = half;
}