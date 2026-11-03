/* A 4-pole resonant lowpass ladder in the spirit of the Ripples / Liquid Filter.
   Four one-pole OTA stages in series, the 4th fed back negatively (4x, so the loop
   gain reaches unity at the cutoff and it self-oscillates). The soft clip sits on
   the resonance feedback path (the Ripples OTA, and the SH-101's feedback diodes),
   not on the input, so the input stays linear and the self-oscillation amplitude
   does not change with the input level. Each cell is clamped to Q15 (the opamp
   rail). `f` is the per-stage coefficient (Q16); `fc` is block-derived (envelope +
   key / velocity follow). Locals are scoped so several instances can coexist. */
int32_t ${out.out} = 0;
int32_t ${out.lp2} = 0;
int32_t ${out.band} = 0;
if (${param.on}) {
    int32_t fb = fm1_q16_mul(${param.res}, ${state.z4}) * 4;
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
    if (${state.z1} > 32767) ${state.z1} = 32767;
    else if (${state.z1} < -32768) ${state.z1} = -32768;
    d = ${state.z1} - ${state.z2};
    ${state.z2} += fm1_q16_mul(${state.fc}, d);
    if (${state.z2} > 32767) ${state.z2} = 32767;
    else if (${state.z2} < -32768) ${state.z2} = -32768;
    d = ${state.z2} - ${state.z3};
    ${state.z3} += fm1_q16_mul(${state.fc}, d);
    if (${state.z3} > 32767) ${state.z3} = 32767;
    else if (${state.z3} < -32768) ${state.z3} = -32768;
    d = ${state.z3} - ${state.z4};
    ${state.z4} += fm1_q16_mul(${state.fc}, d);
    if (${state.z4} > 32767) ${state.z4} = 32767;
    else if (${state.z4} < -32768) ${state.z4} = -32768;
    ${out.lp2} = ${state.z2};
    ${out.band} = ${state.z1} - ${state.z2};
    ${out.out} = ${state.z4}
        + fm1_q15_mul(${state.z4}, fm1_q15_mul(${param.res} >> 1, ${param.comp}));
} else {
    ${out.out} = ${in.audio};
    ${out.lp2} = ${in.audio};
    ${out.band} = 0;
}
