/* key-follow factor: recomputed each block (block_derived) from the voice's note
   + the breakpoint + LO/HI; the output copies it. One block of ~0.7 ms latency,
   inaudible for a timbre-shaping parameter. */
${out.k} = ${state.k};
