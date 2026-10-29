/* Band-limited pulse (2nd-order polyBLEP, two BLEPs): the rising edge is the
   phase wrap (corrected by +blep(ph)), the falling edge is at the pulse width
   `pw` (corrected by -blep(ph - pw), the `(ph + 1 - pw) mod 1` shift). `width` is
   a param (block-rate), so `pw` is block_derived. `inv_inc` = 2^32/inc (note-on). */
uint32_t ph = ${state.phase} + ${state.inc} + ${in.fm} + ${in.mod};
${state.phase} = ph;
int32_t pulse = (ph < ${state.pw}) ? 32767 : -32767;   /* naive pulse, Q15 */
int32_t ${out.audio} = pulse
    + fm1_poly_blep(ph, ${state.inc}, ${state.inv_inc})
    - fm1_poly_blep(ph - ${state.pw}, ${state.inc}, ${state.inv_inc});
