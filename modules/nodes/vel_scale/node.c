/* Velocity-follow factor: block-derived from the voice's velocity and the amount,
   gated by the global velocity-sensitivity switch. The output copies it. */
${out.k} = ${state.k};
