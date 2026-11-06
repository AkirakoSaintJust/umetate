/* Key-follow factor: recomputed each block (block_derived) from the voice's note,
   the breakpoint, and LO/HI. The output copies it. That is one block of ~0.7 ms
   latency, which is inaudible for a timbre-shaping parameter. */
${out.k} = ${state.k};
