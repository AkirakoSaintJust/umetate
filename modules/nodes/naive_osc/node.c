/* Wave reader: shape 0 = saw, 1 = sine, 2 = triangle, 3 = square (one Q15 table
   `fm1_naive_wave`), 4 = white noise (xorshift, self-seeded). Saw (0) and square
   (3) are six band-limited tables each, selected by the `mip` level (from the
   phasor) so the top octaves stop aliasing; sine/triangle ignore it. Pulse width
   comes from a phase_dist (PWM) bend upstream, not a table. */
int32_t ${out.audio};
if (${state.is_noise}) {
    if (!${state.lfsr}) ${state.lfsr} = 0x9E3779B9u;
    ${state.lfsr} ^= ${state.lfsr} << 13;
    ${state.lfsr} ^= ${state.lfsr} >> 17;
    ${state.lfsr} ^= ${state.lfsr} << 5;
    ${out.audio} = (int32_t)(${state.lfsr} >> 16) - 32768;
} else {
    ${out.audio} = fm1_naive_wave[${state.base}
        + ((${state.bl} ? ${in.mip} : 0u) << 10) + (${in.phase} >> 22)];
}
