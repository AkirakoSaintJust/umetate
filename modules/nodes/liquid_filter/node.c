/* A 4-pole resonant lowpass ladder in the spirit of the Ripples / Liquid Filter.
   Four one-pole OTA stages in series, the 4th fed back negatively (4x, so the loop
   gain reaches unity at the cutoff and it self-oscillates). The soft clip sits on
   the resonance feedback path (the Ripples OTA, and the SH-101's feedback diodes),
   not on the input, so the input stays linear and the self-oscillation amplitude
   does not change with the input level. The states are not clamped: the feedback
   clip already bounds the loop, so the cells settle within a few times the input
   level and int32 holds them comfortably. `f` is the per-stage coefficient (Q16);
   `fc` is block-derived (envelope + key / velocity follow). Locals are scoped so
   several instances can coexist. */
int32_t ${out.out} = 0;
int32_t ${out.lp2} = 0;
int32_t ${out.band} = 0;
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
    ${out.out} = ${state.z4}
        + fm1_q15_mul(${state.z4}, fm1_q15_mul(${param.res} >> 1, ${param.comp}));
} else {
    ${out.out} = ${in.audio};
    ${out.lp2} = ${in.audio};
    ${out.band} = 0;
}
