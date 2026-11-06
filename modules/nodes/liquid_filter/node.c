/* A 4-pole resonant lowpass ladder in the spirit of the Ripples / Liquid Filter.
   Four one-pole OTA stages run in series, with the 4th fed back negatively at 4x.
   The loop gain reaches unity at the cutoff, so it self-oscillates. The soft clip
   sits on the resonance feedback path (the Ripples OTA, and the SH-101's feedback
   diodes) rather than on the input, so the input stays linear and the
   self-oscillation amplitude does not change with the input level. The states are
   not clamped. The feedback clip already bounds the loop, so the cells settle
   within a few times the input level and int32 holds them comfortably. `f` is the
   per-stage coefficient (Q16). `fc` is block-derived from the envelope plus key /
   velocity follow, and clamped at 55296 because the feedback loop breaks into a
   parasitic oscillation above that coefficient. The feedback also drops the passband by `1/(1+4.5*res)`, so
   `comp` (Q15) is the fraction of a `1+4.5*res` makeup applied to the LP4 output;
   at `comp` = 1 the passband stays level as the resonance rises. `mode` selects
   the output: 0 = LP4, 1 = the band tap, 2 = the 2-pole highpass, the (1 - L)^2
   tap whose corner lines up with the LP pole. Locals are scoped so several
   instances can coexist. */
int32_t ${out.out} = 0;
int32_t ${out.lp2} = 0;
int32_t ${out.band} = 0;
int32_t ${out.hp} = 0;
if (${param.on}) {
    int32_t fb = fm1_q16_mul(${param.res}, ${state.z4});
    fb = fb * 9 / 2;                 /* 4.5x: a little past the discretized threshold */
    int32_t fbc;
    if (fb > 32767) {
        fbc = 21845;
    } else if (fb < -32767) {
        fbc = -21845;
    } else {
        int32_t f2 = (fb * fb) >> 15;
        int32_t f3 = (f2 * fb) >> 15;
        fbc = fb - ((f3 * 21846) >> 16);
    }
    int32_t u = ${in.audio} - fbc;
    int32_t d = u - ${state.z1};
    ${state.z1} += fm1_q16_mul(${state.fc}, d);
    d = ${state.z1} - ${state.z2};
    ${state.z2} += fm1_q16_mul(${state.fc}, d);
    d = ${state.z2} - ${state.z3};
    ${state.z3} += fm1_q16_mul(${state.fc}, d);
    d = ${state.z3} - ${state.z4};
    ${state.z4} += fm1_q16_mul(${state.fc}, d);
    ${out.lp2} = ${state.z2};
    ${out.band} = ${state.z1} - ${state.z2};
    {
        int32_t boost = fm1_q16_mul(${param.res}, ${param.comp} << 1); /* res * comp */
        boost = boost * 9 / 2;                 /* 4.5x: the ladder feedback */
        int32_t lp4 = ${state.z4} + fm1_q16_mul(${state.z4}, boost);
        /* The 2-pole HP is the (1 - L)^2 tap, so its corner lines up with the
           LP pole rather than the 1.55x offset of the 4-pole (1 - L)^4 tap. */
        int32_t hp = u - 2 * ${state.z1} + ${state.z2};
        ${out.hp} = hp;
        ${out.out} = (${param.mode} == 1u) ? ${out.band}
                   : ((${param.mode} == 2u) ? hp : lp4);
    }
} else {
    ${out.out} = ${in.audio};
    ${out.lp2} = ${in.audio};
    ${out.band} = 0;
    ${out.hp} = 0;
}
