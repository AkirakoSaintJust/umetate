/* ring-buffer delay: the read (tap) is ordered first, the write (advance) last. */
@@read@@
int32_t ${out.out} = ${state.buf}[${state.idx}];
@@write@@
${state.buf}[${state.idx}] = ${in.in} + fm1_q15_mul(${out.out}, ${param.fb});
${state.idx} = (${state.idx} + 1) & ${const.mask};
