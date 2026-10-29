/* Band-limited triangle: the polyBLEP'd square (width 0.5), leaky-integrated.
   `integ` is the one extra state; the leak (`integ >> 10` per sample) stops the
   DC that a pure integrator would accumulate, at the cost of a brief note-on
   transient (the integrator starts from 0). `slope` = inc/2^16 (block-derived)
   is the integration gain, so the steady-state output is full-scale at any pitch;
   the int64 accumulator peaks around 2^30 (no int32 overflow). */
uint32_t ph = ${state.phase} + ${state.inc} + ${in.fm} + ${in.mod};
${state.phase} = ph;
int32_t sq = (ph < 0x80000000u) ? 32767 : -32767;   /* naive square, Q15 */
sq += fm1_poly_blep(ph, ${state.inc}, ${state.inv_inc});
sq -= fm1_poly_blep(ph - 0x80000000u, ${state.inc}, ${state.inv_inc});
int64_t acc = (int64_t)${state.integ} - ((int64_t)${state.integ} >> 10)
            + (int64_t)${state.slope} * sq;
${state.integ} = (int32_t)acc;
int32_t ${out.audio} = (int32_t)(acc >> 14);
