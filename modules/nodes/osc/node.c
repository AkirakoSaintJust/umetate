/* Wave reader: one load from the precomputed 12-wave table (`fm1_wave`). The
   `waveform` param is not modulatable, so its `(waveform << 10)` base is
   recomputed only each block (the node's block_derived); the per-sample work is
   just the phase index + the load. */
int32_t ${out.audio} = fm1_wave[${state.base} + (${in.phase} >> 22)];
