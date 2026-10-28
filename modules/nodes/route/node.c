/* 4-op FM algorithm router (audio rate): the four routing rows the patch consumes
   — rows 1/2/3 (modulation into op2/op3/op4) and row 4 (the carrier mask) — each a
   weighted 0/1 sum of the four delayed operator outputs, indexed by the `alg`
   control input (the selected algorithm). Row 0 (modulation into op1) is all-zero
   and omitted. */
int32_t ${out.mod2} = fm1_route4(&${table.@}[(${in.alg} * 20u) + 4u], ${in.a}, ${in.b}, ${in.c}, ${in.d});
int32_t ${out.mod3} = fm1_route4(&${table.@}[(${in.alg} * 20u) + 8u], ${in.a}, ${in.b}, ${in.c}, ${in.d});
int32_t ${out.mod4} = fm1_route4(&${table.@}[(${in.alg} * 20u) + 12u], ${in.a}, ${in.b}, ${in.c}, ${in.d});
int32_t ${out.car} = fm1_route4(&${table.@}[(${in.alg} * 20u) + 16u], ${in.a}, ${in.b}, ${in.c}, ${in.d});
