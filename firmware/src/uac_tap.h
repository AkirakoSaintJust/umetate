/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments */
#ifndef UAC_TAP_H
#define UAC_TAP_H

#include <stdint.h>

/* Apply one polyphase FIR phase to a pair of explicit L/R history windows.
 *
 * `taps` points at the phase's first tap and `n` is UAC_FIR_N. With
 * reverse == 0 the taps run oldest input first; with reverse == 1 the
 * symmetric prototype is read backwards. The two windows are separate
 * objects, so no pointer arithmetic crosses from L into R.
 */
static inline void uac_fir_pair(const int16_t *left, const int16_t *right,
                                const int16_t *taps, uint32_t n, int reverse,
                                int32_t *sum_left, int32_t *sum_right)
{
    uint32_t i;

    for (i = 0; i < n; i++) {
        int32_t t = reverse ? taps[n - 1u - i] : taps[i];
        *sum_left += t * left[i];
        *sum_right += t * right[i];
    }
}

#endif
