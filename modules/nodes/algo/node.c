/* the FM algorithm selector (control rate): echo the algorithm for the router.
   The 8 shipped routings clamp at 7. */
uint32_t alg = ${param.algorithm} > 7u ? 7u : ${param.algorithm};
${out.alg} = (int32_t)alg;
