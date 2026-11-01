/* Wave reader: one load from `fm1_naive_wave` (4 shapes). The `shape` base is
   block-rate (block_derived); the per-sample work is the phase index + the load.
   For the band-limited shapes (0 = saw, 3 = square) the `mip` level (from the
   phasor) is added to the base so the top octaves stop aliasing; sine/triangle
   ignore it. Pulse width comes from a phase_dist (PWM) bend upstream, not a table. */
int32_t ${out.audio} = fm1_naive_wave[${state.base}
    + ((${state.bl} ? ${in.mip} : 0u) << 10) + (${in.phase} >> 22)];
