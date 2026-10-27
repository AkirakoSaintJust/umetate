/* 1-sample delay: the read (source) is ordered first, the write (sink) last. */
@@read@@
int32_t ${out.out} = ${state.prev};
@@write@@
${state.prev} = ${in.in};
