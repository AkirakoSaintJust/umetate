/* velocity depth (control rate): gain = 32768 - depth + velocity*depth/32768. */
${out.cv} = 32768 - ${param.depth} + fm1_q15_mul(${in.velocity}, ${param.depth});
