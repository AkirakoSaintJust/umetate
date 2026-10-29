/* routing-matrix row mixer: out = a*w0 + b*w1 + c*w2 + d*w3, where the four 0/1
   Q15 weights are row (algorithm, dest) of the selected `routing` table. Both
   indices are clamped to the table (8 algorithms x 5 rows). */
uint32_t alg = ${param.algorithm} > 7u ? 7u : ${param.algorithm};
uint32_t dst = ${param.dest} > 4u ? 4u : ${param.dest};
int32_t ${out.audio} = fm1_route4(
    &${table.@}[(alg * 20u) + (dst * 4u)],
    ${in.a}, ${in.b}, ${in.c}, ${in.d});
