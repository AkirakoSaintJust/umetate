/* Analogue wave reader: one load from fm1_analog_wave (4 shapes). The `shape` base
   is block-rate (block_derived); the per-sample work is the phase index + load.
   Pulse width comes from a phase_dist (PWM) bend upstream, not a table. */
int32_t ${out.audio} = fm1_analog_wave[${state.base} + (${in.phase} >> 22)];
