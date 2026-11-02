/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate)
 *
 * Reusable pi32v2 DSP kernels — the compiler-codegen gap made a contract.
 *
 * The stock firmware is fast because its compiler emits the pi32v2's VLIW/loop
 * machinery; our clang 4.0.1 emits neither. This header wraps the primitives that
 * close that gap as `static inline` helpers, one per operation, each with a
 * bit-identical C fallback for host/WASM (the `#else` branch) and a pi32v2 asm
 * body (`#if defined(UMETATE_TARGET)`). The pattern is the same one fm1_math.h
 * uses for the ROM transcendentals: portable C everywhere, hand-asm on device.
 *
 * Verified against the assembler (the disassembler's "arithmetic" syntax is NOT
 * what the parser accepts — this header holds the parser's form):
 *
 *   rep <counter> { <body> }         zero-overhead hardware loop; the body size is
 *                                     auto-computed (2*iwords); <counter> is a
 *                                     register (runtime) or immediate. The counter
 *                                     register is CLOBBERED and wraps on 0, so the
 *                                     count must be > 0.
 *   <alu>  # <b-slot>                VLIW dual-issue: an A-slot arithmetic op and a
 *                                     B-slot load/store issue in parallel (the `#`
 *                                     terminates the A instruction; the next line is
 *                                     the B instruction). Two ALU ops do NOT pair.
 *   rA_rB += [rC ++= i1]*[rD ++= i2] 64-bit memory-MAC: two auto-incrementing loads
 *                                     multiplied and accumulated in one instruction
 *                                     (`h[..]` = 16-bit halfword operand, `(s)` signed).
 *   r1_r0 = r0 * r0                  square (64-bit); `r1_r0 += r0 * r0` square-MAC.
 *
 * Every kernel must stay bit-identical to its C fallback — the host/WASM parity
 * tests (firmware/tests) rely on that. Counts are runtime (a `rep` register); the
 * generator/RuBI passes NVOICE and CONTROL_BLOCK directly.
 */
#pragma once
#include <stdint.h>

#define FM1_KERNEL_INLINE static inline __attribute__((always_inline))

/* Sum `n` 32-bit words (a[i] added into a 32-bit accumulator). `n` must be > 0 —
 * `rep` with a 0 counter wraps to 2^32. */
FM1_KERNEL_INLINE int32_t fm1_kernel_sum_i32(const int32_t *in, uint32_t n)
{
#ifdef UMETATE_TARGET
    int32_t acc;
    __asm__ volatile(
        "r2 = 0\n"
        "rep %1 %{\n"
        "  r3 = [%0 ++= 4]\n"
        "  r2 += r3\n"
        "%}\n"
        "%2 = r2\n"
        : "+r"(in), "+r"(n), "=r"(acc)
        : : "r2", "r3", "memory");
    return acc;
#else
    int32_t acc = 0;
    for (uint32_t i = 0; i < n; i++) acc += in[i];
    return acc;
#endif
}

/* Dot product of `n` 32-bit signed words — 64-bit accumulate (matches the asm's
 * r1_r0), returns the low word. This is the route / mix inner loop. `n` > 0. */
FM1_KERNEL_INLINE int32_t fm1_kernel_dot_i32(const int32_t *a, const int32_t *b, uint32_t n)
{
#ifdef UMETATE_TARGET
    int32_t lo;
    __asm__ volatile(
        "r1_r0 = 0\n"
        "rep %2 %{\n"
        "  r1_r0 += [%0 ++= 4] * [%1 ++= 4] (s)\n"
        "%}\n"
        "%3 = r0\n"
        : "+r"(a), "+r"(b), "+r"(n), "=r"(lo)
        : : "r0", "r1", "memory");
    return lo;
#else
    int64_t acc = 0;
    for (uint32_t i = 0; i < n; i++) acc += (int64_t)a[i] * b[i];
    return (int32_t)acc;
#endif
}

/* Zero `n` 32-bit words — the `rep` + auto-increment-store primitive. `n` > 0.
 * `UMETATE_NO_ASM` forces the C fallback on target for the before/after gate. */
FM1_KERNEL_INLINE void fm1_kernel_zero_i32(int32_t *p, uint32_t n)
{
#if defined(UMETATE_TARGET) && !defined(UMETATE_NO_ASM)
    __asm__ volatile(
        "r3 = 0\n"
        "rep %1 %{\n"
        "  [%0 ++= 4] = r3\n"
        "%}\n"
        : "+r"(p), "+r"(n) : : "r3", "memory");
#else
    for (uint32_t i = 0; i < n; i++) p[i] = 0;
#endif
}
