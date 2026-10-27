/* routing-matrix row mixer: out = a*w0 + b*w1 + c*w2 + d*w3, where the four 0/1
   Q15 weights are row (algorithm, dest) of the selected `routing` table. */
int32_t ${out.audio} = fm1_route4(
    &${table.@}[(${param.algorithm} * 20u) + (${param.dest} * 4u)],
    ${in.a}, ${in.b}, ${in.c}, ${in.d});
