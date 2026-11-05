/* Self-feedback tap: `(x[n] + x[n-1]) / 2 * level`, gated on `level_eff` so a
   patch with no feedback pays nothing. The two-sample average is the OPM's
   `(o + Inp_last) >> Fl`. Its zero at Nyquist is the point: a one-sample
   feedback loop with no damping can ring at the top of the band. The half and
   the Q15 scale are folded into one shift, `(x + prev) * level >> 16`, which is
   a 32-bit multiply: `audio` is Q15, so the sum is at most 65536 and the product
   stays under INT32_MAX. The shift truncates instead of rounding, which loses at
   most one LSB on the feedback phase. While the tap is gated the state holds its
   last value, so the first samples after turning feedback up fade in from the
   previous setting. */
int32_t ${out.audio} = 0;
if (${state.level_eff}) {
    ${out.audio} = ((${in.audio} + ${state.prev}) * ${state.level_eff}) >> 16;
    ${state.prev} = ${in.audio};
}
