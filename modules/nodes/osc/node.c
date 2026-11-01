/* Wave reader: one load from the precomputed 12-wave table (`fm1_wave`). The
   `waveform` param is not modulatable, so its `(fm1_wave_base[waveform] << 10)`
   base is recomputed only each block (the node's block_derived); the per-sample
   work is the phase index + the load. For the band-limited waves (9/10/11) the
   `mip` level (from the phasor) is added to the base so the top octaves read a
   table with fewer harmonics and stop aliasing; waves 0-8 ignore it. */
int32_t ${out.audio} = fm1_wave[${state.base}
    + ((${state.bl} ? ${in.mip} : 0u) << 10) + (${in.phase} >> 22)];