/* Low-frequency oscillator (control rate): phase advances by `rate` per sample
   (`rate * CONTROL_BLOCK` per control tick — CONTROL_BLOCK is the emitted macro),
   output is a sine scaled by `depth` (bipolar Q15). */
${state.phase} += ${param.rate} * CONTROL_BLOCK;
${out.cv} = fm1_q15_mul(fm1_sin(${state.phase}), ${param.depth});
