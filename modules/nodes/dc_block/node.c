/* One-pole DC blocker: y[n] = x[n] - x[n-1] + r*y[n-1]. `r` (Q15, ~0.999) is the
   pole, so a higher r lowers the high-pass cutoff and lengthens the settle, and it
   removes the DC of an asymmetric pulse such as the APC's. The audio band stays
   untouched. */
int32_t ${out.out} = ${in.in} - ${state.x1} + fm1_q15_mul(${param.r}, ${state.y1});
${state.x1} = ${in.in};
${state.y1} = ${out.out};
