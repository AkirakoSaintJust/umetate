/* SPDX-License-Identifier: GPL-3.0-only
 * Stereo regression for the 44.1 -> 48 kHz USB audio tap. The old code read the
 * right channel through &rs.l[s] + 2*RS_H, this test makes a channel swap or a
 * stride error fail on the host, without a device. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../src/uac_fir.h"
#include "../src/uac_tap.h"

static void require(int ok, const char *message)
{
    if (!ok) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
    printf("ok: %s\n", message);
}

static void fill_ramps(int16_t *left, int16_t *right, uint32_t n)
{
    uint32_t i;
    for (i = 0; i < n; i++) {
        left[i] = (int16_t)(i + 1u);
        right[i] = (int16_t)-(int32_t)(i + 1u);
    }
}

static void test_explicit_channels(void)
{
    int16_t left[UAC_FIR_N], right[UAC_FIR_N], taps[UAC_FIR_N] = {0};
    int32_t sum_left = 0, sum_right = 0;
    uint32_t i;

    fill_ramps(left, right, UAC_FIR_N);
    taps[0] = 1;
    uac_fir_pair(left, right, taps, UAC_FIR_N, 0, &sum_left, &sum_right);
    require(sum_left == 1 && sum_right == -1, "one-hot tap reads L and R from separate windows");

    sum_left = sum_right = 0;
    for (i = 0; i < UAC_FIR_N; i++)
        taps[i] = (int16_t)(i + 1u);
    uac_fir_pair(left, right, taps, UAC_FIR_N, 0, &sum_left, &sum_right);
    require(sum_left > 0 && sum_right == -sum_left, "multi-tap L/R sums stay independent and opposite");
}

static void test_reverse_phase(void)
{
    int16_t left[UAC_FIR_N], right[UAC_FIR_N], taps[UAC_FIR_N] = {0};
    int32_t sum_left = 0, sum_right = 0;

    fill_ramps(left, right, UAC_FIR_N);
    taps[0] = 1;
    uac_fir_pair(left, right, taps, UAC_FIR_N, 1, &sum_left, &sum_right);
    require(sum_left == left[UAC_FIR_N - 1u] && sum_right == right[UAC_FIR_N - 1u],
            "reversed phase uses the same explicit channel windows");
}

static void test_generated_filter(void)
{
    int16_t left[UAC_FIR_N], right[UAC_FIR_N];
    int32_t sum_left = 0, sum_right = 0;

    fill_ramps(left, right, UAC_FIR_N);
    uac_fir_pair(left, right, UAC_FIR[0], UAC_FIR_N, 0, &sum_left, &sum_right);
    require(sum_left != 0, "generated FIR phase is non-zero");
    require(sum_right == -sum_left, "generated FIR keeps the right channel sign and magnitude");
}

int main(void)
{
    test_explicit_channels();
    test_reverse_phase();
    test_generated_filter();
    puts("UAC stereo FIR test passed");
    return 0;
}
