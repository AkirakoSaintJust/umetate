/* the FM algorithm selector + carrier-feedback master (control rate): echo the
   algorithm for the router, and gate `car_fb` by the carrier mask. The algorithm
   is clamped to the 8 shipped routings (the routing table has 8 rows). */
uint32_t alg = ${param.algorithm} > 7u ? 7u : ${param.algorithm};
${out.alg} = (int32_t)alg;
${out.fb1} = ${table.@}[(alg * 20u) + 16u] ? ${param.car_fb} : 0;
${out.fb2} = ${table.@}[(alg * 20u) + 17u] ? ${param.car_fb} : 0;
${out.fb3} = ${table.@}[(alg * 20u) + 18u] ? ${param.car_fb} : 0;
${out.fb4} = ${table.@}[(alg * 20u) + 19u] ? ${param.car_fb} : 0;
