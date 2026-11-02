/* velocity-follow factor: block-derived from the voice's velocity + the amount,
   gated by the global velocity-sensitivity switch; the output copies it. */
${out.k} = ${state.k};
