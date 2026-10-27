/* Band-limited saw (2nd-order polyBLEP). `inv_inc` = 2^32/inc is a Q32
   reciprocal; ph * inv_inc is the Q32 fractional phase position ph/inc (no shift
   — the product already carries the fraction). */
uint32_t ph = ${state.phase} + ${state.inc} + ${in.fm} + ${in.mod};
${state.phase} = ph;
int32_t saw = (int32_t)(ph >> 16) - 32768;      /* naive saw, Q15 */
if (ph < ${state.inc}) {
    /* just after the wrap: u = ph/inc (Q32); residual 2u - u^2 - 1 (negative). */
    uint32_t u = (uint32_t)((uint64_t)ph * ${state.inv_inc});
    int64_t q = (int64_t)(2ull * u - (((uint64_t)u * u) >> 32));   /* 2u - u^2, [0, 2^32) */
    int32_t r = (int32_t)((q - 0x100000000LL) >> 17);
    saw -= r;
} else if (ph > 0u - ${state.inc}) {
    /* just before the wrap: w = 2^32 - ph; residual (1 - w/inc)^2. */
    uint32_t w = 0u - ph;
    uint32_t u = (uint32_t)((uint64_t)w * ${state.inv_inc});
    uint64_t omt = 0x100000000ull - u;          /* 1 - w/inc, in (0, 2^32] */
    int32_t r = (int32_t)((omt * omt) >> 49);
    saw -= r;
}
int32_t ${out.audio} = saw;
