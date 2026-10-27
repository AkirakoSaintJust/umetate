/* band-limited saw (2nd-order polyBLEP). `inv_inc` = 2^32/inc (note-on reciprocal). */
uint32_t ph = ${state.phase} + ${state.inc} + ${in.fm} + ${in.mod};
${state.phase} = ph;
int32_t saw = (int32_t)(ph >> 16) - 32768;      /* naive saw, Q15 */
if (ph < ${state.inc}) {
    /* just after the wrap: u = ph/inc; residual 2u - u^2 - 1 (negative). */
    int64_t u = ((int64_t)ph * ${state.inv_inc}) >> 32;
    int32_t r = (int32_t)((2 * u - ((u * u) >> 32) - 0x100000000LL) >> 17);
    saw -= r;
} else if (ph > 0u - ${state.inc}) {
    /* just before the wrap: w = 2^32 - ph; residual (1 - w/inc)^2. */
    uint32_t w = 0u - ph;
    int64_t u = ((int64_t)w * ${state.inv_inc}) >> 32;
    int64_t one_minus_u = 0x100000000LL - u;
    int32_t r = (int32_t)((one_minus_u * one_minus_u) >> 49);
    saw -= r;
}
int32_t ${out.audio} = saw;
