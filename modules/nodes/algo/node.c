/* the FM algorithm selector + carrier-feedback master (control rate): echo the
   algorithm for the router, and gate `car_fb` by the carrier mask. */
${out.alg} = (int32_t)${param.algorithm};
${out.fb1} = ${table.@}[(${param.algorithm} * 20u) + 16u] ? ${param.car_fb} : 0;
${out.fb2} = ${table.@}[(${param.algorithm} * 20u) + 17u] ? ${param.car_fb} : 0;
${out.fb3} = ${table.@}[(${param.algorithm} * 20u) + 18u] ? ${param.car_fb} : 0;
${out.fb4} = ${table.@}[(${param.algorithm} * 20u) + 19u] ? ${param.car_fb} : 0;
