/* 8-waveform oscillator: fm1_sin_ws applies the OPL/OPZ bit trick (dsp-study §2.7)
   to the phase — one quarter-sine table + a 3-bit `waveform` select. */
int32_t ${out.audio} = fm1_sin_ws(${in.phase}, ${param.waveform});
