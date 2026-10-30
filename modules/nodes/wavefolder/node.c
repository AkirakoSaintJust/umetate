/* Sine wavefolder: folds the portion of the input above `threshold` (Q15) by
   `folds` sine folds, crossfaded by `amount` (Q15, modulatable). `on` 0 = dry
   bypass; `type` 0 = sine fold (reserved). The band below `threshold` passes
   unmodified; the excess is folded `folds` times and crossfaded in. Bounded:
   each sine fold maps Q15 (0..32767) back to Q15. */
int32_t in = ${in.audio};
int32_t ${out.audio};
if (!${param.on}) {
    ${out.audio} = in;
} else {
    int32_t th = ${param.threshold};
    int32_t mag = in < 0 ? -in : in;
    int32_t over = mag - th;
    if (over <= 0) {
        ${out.audio} = in;                         /* fully dry below the threshold */
    } else {
        int32_t x = over;
        uint32_t k, n = ${param.folds};
        for (k = 0; k < n && k < 8u; k++)
            x = fm1_sin((uint32_t)((int64_t)x * 65536));   /* sin(pi * x), one fold */
        int32_t excess = over + fm1_q15_mul(${param.amount}, x - over);
        ${out.audio} = (in < 0 ? -1 : 1) * (th + excess);
    }
}
