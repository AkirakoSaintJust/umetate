/* Band-limited saw (2nd-order polyBLEP). `inv_inc` = 2^32/inc is a Q32
   reciprocal, and the residual is fm1_poly_blep (one correction per cycle). */
uint32_t ph = ${state.phase} + ${state.inc} + ${in.fm} + ${in.mod};
${state.phase} = ph;
int32_t saw = (int32_t)(ph >> 16) - 32768;      /* naive saw, Q15 */
saw -= fm1_poly_blep(ph, ${state.inc}, ${state.inv_inc});
int32_t ${out.audio} = saw;
