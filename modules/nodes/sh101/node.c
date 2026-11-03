/* Roland SH-101-style 4-pole resonant lowpass (IR3109 ladder). Four one-pole
   OTA stages in series; the 4th stage is fed back negatively (4x, so the loop
   gain reaches unity at the cutoff and the filter self-oscillates). The feedback
   sum is soft-clipped (cubic up to +/-1, flat at +/-2/3 beyond), standing in for
   the OTA tanh and the SH-101's clipping diodes, so self-oscillation is a clean,
   bounded sine. The output is boosted as resonance rises (the SH-101's
   output-level resonance compensation, unlike the Juno's input compensation).
   `f` is the per-stage coefficient (Q16); `fc` is block-derived (envelope + key /
   velocity follow). Locals are scoped so several instances can coexist. */
int32_t ${out.out} = 0;
int32_t ${out.lp2} = 0;
int32_t ${out.band} = 0;
if (${param.on}) {
    int32_t fb = fm1_q16_mul(${param.res}, ${state.z4});
    int32_t u = ${in.audio} - (fb << 2);
    int32_t us;
    if (u > 32767) {
        us = 21845;
    } else if (u < -32767) {
        us = -21845;
    } else {
        int32_t u2 = (u * u) >> 15;
        int32_t u3 = (u2 * u) >> 15;
        us = u - ((u3 * 21846) >> 16);
    }
    int32_t d = us - ${state.z1};
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
