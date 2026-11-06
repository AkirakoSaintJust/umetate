/* Velocity-follow factor (global): block-derived from the highest held velocity
   and the amount, gated by the global velocity-sensitivity switch. The output
   copies it. */
${out.k} = ${state.k};
