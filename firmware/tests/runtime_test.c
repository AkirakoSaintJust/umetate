/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The synth runtime host test: a multi patch applies its part-patch refs (the
 * timbre params) + its routing (channel/low/high/level/delay) through set_param. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../src/synth_runtime.h"

/* the storage services (unused here; presets.c's bank functions need them) */
int slot_save(uint32_t i, const void *p, uint32_t n) { (void)i; (void)p; (void)n; return 0; }
int slot_load(uint32_t i, void *p, uint32_t n) { (void)i; (void)p; (void)n; return 0; }
int settings_save(const void *p, uint32_t n) { (void)p; (void)n; return 0; }
int settings_load(void *p, uint32_t n) { (void)p; (void)n; return 0; }

#include "../src/presets.c"
#include "../src/synth_runtime.c"

static uint8_t part_bank[PP_BANK(4)], multi_bank[MP_BANK(2)];
static uint32_t set_n;
static uint32_t set_id[32];
static int32_t set_val[32];

static int st_set_param(uint32_t id, int32_t v)
{
    set_id[set_n] = id;
    set_val[set_n] = v;
    set_n++;
    return 0;
}

static int bad;
static void check(const char *what, int ok)
{
    printf("runtime: %-70s %s\n", what, ok ? "ok" : "FAIL");
    bad += !ok;
}

int main(void)
{
    static const int32_t rec2[4] = {10, 20, 30, 40};
    static const int32_t lv[2] = {32768, 16384}, dl[2] = {0, 5}, ch[2] = {0, 1};
    static const int32_t lo[2] = {0, 48}, hi[2] = {127, 96};
    static const uint8_t slots[2] = {2, 31};
    synth_runtime_ctx ctx = {4, 2, 8, st_set_param, part_bank, multi_bank};
    uint32_t n0;

    memset(part_bank, 0xFF, sizeof part_bank);
    memset(multi_bank, 0xFF, sizeof multi_bank);
    preset_part_pack(part_bank + 2u * PP_RECORD(4), "Two", rec2, 4);
    preset_multi_pack(multi_bank + 5u * MP_RECORD(2), "Five", slots, lv, dl, ch, lo, hi, 2);

    synth_preset_apply(&ctx, 5);
    /* part 0: slot 2's timbre (ids 0..3) + routing channel/low/high/level/delay
       (ids 8, 10, 12, 14, 16); part 1: slot 31 is empty -> no timbre, just routing
       (ids 9, 11, 13, 15, 17) */
    check("the multi patch applies part patches + routing",
          set_n == 14u && set_id[0] == 0 && set_val[0] == 10 && set_id[3] == 3 &&
              set_val[3] == 40 && set_id[4] == 8 && set_val[4] == 0 && set_id[5] == 10 &&
              set_val[5] == 0 && set_id[6] == 12 && set_val[6] == 127 && set_id[7] == 14 &&
              set_val[7] == 32768 && set_id[8] == 16 && set_val[8] == 0 &&
              set_id[9] == 9 && set_val[9] == 1 && set_id[10] == 11 && set_val[10] == 48 &&
              set_id[11] == 13 && set_val[11] == 96 && set_id[12] == 15 &&
              set_val[12] == 16384 && set_id[13] == 17 && set_val[13] == 5);

    /* a bad slot is a no-op */
    n0 = set_n;
    synth_preset_apply(&ctx, 64);
    check("a bad slot is a no-op", set_n == n0);

    printf("%s\n", bad ? "RUNTIME TEST FAILED" : "runtime test passed");
    return bad != 0;
}
