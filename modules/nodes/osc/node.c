/* 12-waveform oscillator: fm1_sin_wave applies the OPZ + OPL waveform union to the
   phase (0-7 OPZ, 8-11 OPL-only), selected by a `waveform` param. */
int32_t ${out.audio} = fm1_sin_wave(${in.phase}, ${param.waveform});
