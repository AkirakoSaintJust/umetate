/* 8-waveform oscillator: fm1_sin_opz applies the OPZ (YM2414) waveform set to the
   phase — sine, triangle, half/double derivatives, selected by a `waveform` param. */
int32_t ${out.audio} = fm1_sin_opz(${in.phase}, ${param.waveform});
