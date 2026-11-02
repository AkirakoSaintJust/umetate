/* 4-op FM algorithm router (audio rate): the four routing rows the patch consumes
   — rows 1/2/3 (modulation into op2/op3/op4) and row 4 (the carrier mask) — each a
   weighted 0/1 sum of the four delayed operator outputs, indexed by the `alg`
   control input (the selected algorithm, clamped to the 8 shipped routings). Row 0
   (modulation into op1) is all-zero and omitted. The clamp stays here (not hoisted
   to `block_derived`): `alg` is a *global* scalar, so the compiler already hoists
   the load + clamp + pointer arithmetic out of the sample loop (measured — a
   `block_derived` hoist was a wash and forced a per-voice array read instead).

   The modulator outputs are ×2: the operators carry a −12 dB headroom (`tl`'s
   `>>2`, for the 4-carrier sum) that also quarter-scales the phase-modulation
   depth, while the per-operator *feedback* taps the raw oscillator (full scale).
   ×2 restores the FM to half scale — a modulator at level 99 + feedback 0 now
   matches what level 99 + 50% feedback used to sound like — without touching the
   feedback (which is summed *inside* the operator, not here). */
uint32_t alg = ${in.alg} > 7u ? 7u : ${in.alg};
int32_t ${out.mod2} = fm1_route4(&${table.@}[(alg * 20u) + 4u], ${in.a}, ${in.b}, ${in.c}, ${in.d}) * 2;
int32_t ${out.mod3} = fm1_route4(&${table.@}[(alg * 20u) + 8u], ${in.a}, ${in.b}, ${in.c}, ${in.d}) * 2;
int32_t ${out.mod4} = fm1_route4(&${table.@}[(alg * 20u) + 12u], ${in.a}, ${in.b}, ${in.c}, ${in.d}) * 2;
int32_t ${out.car} = fm1_route4(&${table.@}[(alg * 20u) + 16u], ${in.a}, ${in.b}, ${in.c}, ${in.d});
