/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate)
 * Host parity for hal/fm1_dsp_kernels.h: the C fallback here is the reference the
 * pi32v2 asm bodies (rep + memory-MAC) must match bit-for-bit. */
#include <stdio.h>
#include <stdint.h>
#include <limits.h>
#include "fm1_dsp_kernels.h"

static int failures;

static void ok(int cond, const char *what)
{
    printf("%s %s\n", cond ? "ok:" : "FAIL:", what);
    if (!cond)
        failures++;
}

int main(void)
{
    static const int32_t a5[] = {1, 2, 3, 4, 5};
    static const int32_t b5[] = {10, 20, 30, 40, 50};
    static const int32_t neg[] = {-1, 2, -3, 4};

    /* ---- rep sum ---- */
    ok(fm1_kernel_sum_i32(a5, 5) == 15, "sum: 1..5 = 15");
    ok(fm1_kernel_sum_i32(a5, 1) == 1, "sum: single element");
    ok(fm1_kernel_sum_i32(neg, 4) == 2, "sum: -1+2-3+4 = 2");

    /* ---- memory-MAC dot (64-bit accumulate, low word) ---- */
    ok(fm1_kernel_dot_i32(a5, b5, 5) == 550, "dot: 1*10+..+5*50 = 550");
    ok(fm1_kernel_dot_i32(a5, a5, 5) == 55, "dot: 1^2+..+5^2 = 55");
    ok(fm1_kernel_dot_i32(neg, neg, 4) == 30, "dot: 1+4+9+16 = 30");
    {
        /* 2 * INT32_MAX overflows a 32-bit accumulator: the 64-bit path must wrap
         * to 0xFFFFFFFE and return the low word -2, matching the asm's r1_r0. */
        static const int32_t big_a[] = {INT32_MAX, 1};
        static const int32_t big_b[] = {2, 0};
        ok(fm1_kernel_dot_i32(big_a, big_b, 2) == (int32_t)0xFFFFFFFEu,
           "dot: 2*INT32_MAX wraps in 64-bit -> low word -2");
    }

    printf("%s\n", failures ? "SOME TESTS FAILED" : "kernel test passed");
    return failures ? 1 : 0;
}
