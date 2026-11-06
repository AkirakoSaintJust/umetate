/* 4-op FM algorithm router (audio rate). The patch consumes four routing rows:
   rows 1/2/3 modulate op2/op3/op4, and row 4 is the carrier mask. Each row is a
   weighted sum of the four delayed operator outputs, indexed by the `alg` control
   input, which is the selected algorithm clamped to the 8 shipped routings. Row 0,
   the modulation into op1, is all-zero and omitted.

   The router is specialised, because the 8 algorithms' weights are 0/1. In Q15,
   `32768`, the true "1.0", does not fit an int16 and would overflow the top value,
   so a 1-weight is `32767`. Each output is then a selective sum:
   `fm1_q15_mul(x, 32767)` for a 1-weight and nothing for a 0-weight, instead of
   four runtime-table `fm1_route4` calls with 16 multiplies and 16 table loads. It
   stays bit-exact, because a 1-weight is the exact `32767` scale, which the
   compiler folds to a 32-bit shift/sub/add, and a 0-weight term is exactly 0. The
   switch is perfectly predicted, because `alg` is a block-constant scalar.

   The modulator outputs are ×2. The phasor scales `fm` by 2^20, so full scale is
   eight cycles, and the operators' -12 dB headroom quarter-scales the path (`tl`'s
   `>>2`, for the 4-carrier sum). The ×2 brings a level-99 modulator to four cycles
   of phase deviation, which is the OPM's full-scale index at TL 0. The
   per-operator *feedback* bypasses this router, because it taps the level gain and
   averages two samples, so it reaches half that index, as the OPM does. */
uint32_t alg = ${in.alg} > 7u ? 7u : ${in.alg};
int32_t ${out.mod2}, ${out.mod3}, ${out.mod4}, ${out.car};
switch (alg) {
case 0u: /* O1 -> O2 -> O3 -> O4 -> out */
    ${out.mod2} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod3} = fm1_q15_mul(${in.b}, 32767) * 2;
    ${out.mod4} = fm1_q15_mul(${in.c}, 32767) * 2;
    ${out.car} = fm1_q15_mul(${in.d}, 32767);
    break;
case 1u: /* (O1 + O2) -> O3 -> O4 -> out */
    ${out.mod2} = 0;
    ${out.mod3} = (fm1_q15_mul(${in.a}, 32767) + fm1_q15_mul(${in.b}, 32767)) * 2;
    ${out.mod4} = fm1_q15_mul(${in.c}, 32767) * 2;
    ${out.car} = fm1_q15_mul(${in.d}, 32767);
    break;
case 2u: /* (O1 + (O2 -> O3)) -> O4 -> out */
    ${out.mod2} = 0;
    ${out.mod3} = fm1_q15_mul(${in.b}, 32767) * 2;
    ${out.mod4} = (fm1_q15_mul(${in.a}, 32767) + fm1_q15_mul(${in.c}, 32767)) * 2;
    ${out.car} = fm1_q15_mul(${in.d}, 32767);
    break;
case 3u: /* 1,2,3 modulators, 4 carrier; 1 -> 2, 1 -> 3, 2+3 -> 4 */
    ${out.mod2} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod3} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod4} = (fm1_q15_mul(${in.b}, 32767) + fm1_q15_mul(${in.c}, 32767)) * 2;
    ${out.car} = fm1_q15_mul(${in.d}, 32767);
    break;
case 4u: /* (O1 -> O2) + (O3 -> O4) -> out (O2 + O4) */
    ${out.mod2} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod3} = 0;
    ${out.mod4} = fm1_q15_mul(${in.c}, 32767) * 2;
    ${out.car} = fm1_q15_mul(${in.b}, 32767) + fm1_q15_mul(${in.d}, 32767);
    break;
case 5u: /* (O1 -> O2) + (O1 -> O3) + (O1 -> O4) -> out (O2 + O3 + O4) */
    ${out.mod2} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod3} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod4} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.car} = fm1_q15_mul(${in.b}, 32767) + fm1_q15_mul(${in.c}, 32767) + fm1_q15_mul(${in.d}, 32767);
    break;
case 6u: /* (O1 -> O2) + O3 + O4 -> out (O2 + O3 + O4) */
    ${out.mod2} = fm1_q15_mul(${in.a}, 32767) * 2;
    ${out.mod3} = 0;
    ${out.mod4} = 0;
    ${out.car} = fm1_q15_mul(${in.b}, 32767) + fm1_q15_mul(${in.c}, 32767) + fm1_q15_mul(${in.d}, 32767);
    break;
default: /* 7 (alg is clamped 0..7): O1 + O2 + O3 + O4 -> out */
    ${out.mod2} = 0;
    ${out.mod3} = 0;
    ${out.mod4} = 0;
    ${out.car} = fm1_q15_mul(${in.a}, 32767) + fm1_q15_mul(${in.b}, 32767) + fm1_q15_mul(${in.c}, 32767) + fm1_q15_mul(${in.d}, 32767);
    break;
}
