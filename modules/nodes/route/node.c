/* 4-op FM algorithm router (audio rate): the four routing rows the patch consumes
   — rows 1/2/3 (modulation into op2/op3/op4) and row 4 (the carrier mask) — each a
   weighted sum of the four delayed operator outputs, indexed by the `alg` control
   input (the selected algorithm, clamped to the 8 shipped routings). Row 0
   (modulation into op1) is all-zero and omitted.

   Specialized: the 8 algorithms' weights are 0/1 (Q15 `0`/`32767` — `32768`, the
   true "1.0", does not fit an int16 and would overflow the top Q15 value). So each
   output is a selective sum — `fm1_q15_mul(x, 32767)` for a 1-weight, nothing for a
   0-weight — instead of four runtime-table `fm1_route4` calls (16 multiplies + 16
   table loads). Bit-exact: a 1-weight is the exact `32767` scale (the compiler
   folds the constant to a 32-bit shift/sub/add); a 0-weight term is exactly 0.
   `alg` is a block-constant scalar, so the switch is perfectly predicted.

   The modulator outputs are ×2. The phasor scales `fm` by 2^20, so full
   scale is eight cycles, and the operators' -12 dB headroom quarter-scales the
   path (`tl`'s `>>2`, for the 4-carrier sum). ×2 brings a level-99 modulator to
   four cycles of phase deviation, the OPM's full-scale index at TL 0. The
   per-operator *feedback* bypasses this router: it taps the level gain and
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
