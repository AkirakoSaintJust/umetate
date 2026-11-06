/* Low-frequency oscillator (control rate): phase advances by `rate` per sample
   (`rate * CONTROL_BLOCK` per control tick, where CONTROL_BLOCK is the emitted
   macro),
   output is a `fm1_wave` waveform (selected by `wave`) scaled by `depth`
   (bipolar Q15). */
${state.phase} += ${param.rate} * CONTROL_BLOCK;
${out.cv} = fm1_q15_mul(fm1_wave[${state.base} + (${state.phase} >> 22)], ${param.depth});
