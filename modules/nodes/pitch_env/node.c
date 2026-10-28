/* Global pitch envelope (the "pitch blip"): on the patch gate rising, `level` =
   `base`; then decay toward 0 at `rate` (one-pole, q16). `cv` is a q15 pitch
   offset (bipolar), summed with the vibrato into the operators' pitch. */
if (${in.gate} && !${state.prev}) {
    ${state.level} = ${param.base};
}
${state.prev} = ${in.gate} ? 1u : 0u;
${state.level} -= (int32_t)(((int64_t)${state.level} * ${param.rate}) >> 16);
${out.cv} = ${state.level};
