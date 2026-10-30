/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The preset store host test: the record layouts (their printed hex is the
 * cross-language parity fixture against umetate/_records.py), the CRC, the
 * empty/corrupt semantics, and the bank save/load over in-RAM storage stubs. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../src/presets.h"

#define SECT 0x1000u
static uint8_t host_slot0[4 * SECT];
static uint8_t host_slot1[4 * SECT];
static uint8_t host_set[SECT];

/* the platform storage services (platform.c on device) */
int slot_save(uint32_t i, const void *p, uint32_t n)
{
    uint8_t *dst = i == 0 ? host_slot0 : i == 1 ? host_slot1 : 0;
    if (!dst || n > 4 * SECT)
        return -1;
    memcpy(dst, p, n);
    return 0;
}
int slot_load(uint32_t i, void *p, uint32_t n)
{
    uint8_t *src = i == 0 ? host_slot0 : i == 1 ? host_slot1 : 0;
    if (!src || n > 4 * SECT)
        return -1;
    memcpy(p, src, n);
    return 0;
}
int settings_save(const void *p, uint32_t n)
{
    if (n > SECT)
        return -1;
    memcpy(host_set, p, n);
    return 0;
}
int settings_load(void *p, uint32_t n)
{
    if (n > SECT)
        return -1;
    memcpy(p, host_set, n);
    return 0;
}

#include "../src/presets.c"

static int bad;
static void check(const char *what, int ok)
{
    printf("presets: %-72s %s\n", what, ok ? "ok" : "FAIL");
    bad += !ok;
}

static void print_hex(const char *tag, const uint8_t *p, uint32_t n)
{
    uint32_t i;
    printf("%s: ", tag);
    for (i = 0; i < n; i++)
        printf("%02x", p[i]);
    printf("\n");
}

int main(void)
{
    static uint8_t rec[MP_RECORD(2)], bank[PP_BANK(4)], back[PP_BANK(4)];
    static int32_t params[4], level[2], delay[2], channel[2], low[2], high[2];
    static uint8_t slot[2];
    char name[PRESET_NAME_LEN];
    int32_t bc, mt;
    uint32_t len;

    check("crc32('123456789') = 0xCBF43926",
          preset_crc32((const uint8_t *)"123456789", 9u) == 0xCBF43926u);

    { /* the known records: their hex is the cross-language parity fixture */
        static const int32_t part[4] = {100, -5, 65536, 0};
        len = preset_part_pack(rec, "EPiano", part, 4);
        print_hex("part-hex", rec, len);
        check("part record unpacks",
              preset_part_unpack(rec, 4, name, params) && !strcmp(name, "EPiano") &&
                  params[0] == 100 && params[1] == -5 && params[2] == 65536 && params[3] == 0);
        rec[2] ^= 1u;
        check("corrupt part record rejected", !preset_part_unpack(rec, 4, name, params));
    }
    { /* multi patch (2 parts) */
        static const uint8_t slots[2] = {0, 1};
        static const int32_t lv[2] = {32768, 32768}, dl[2] = {0, 40}, ch[2] = {0, 1};
        static const int32_t lo[2] = {0, 60}, hi[2] = {127, 127};
        len = preset_multi_pack(rec, "Layers", slots, lv, dl, ch, lo, hi, 2);
        print_hex("multi-hex", rec, len);
        check("multi record unpacks",
              preset_multi_unpack(rec, 2, name, slot, level, delay, channel, low, high) &&
                  !strcmp(name, "Layers") && slot[0] == 0 && slot[1] == 1 &&
                  level[0] == 32768 && delay[1] == 40 && channel[1] == 1 && low[1] == 60 &&
                  high[1] == 127);
    }
    { /* settings */
        len = preset_settings_pack(rec, -1, 12);
        print_hex("settings-hex", rec, len);
        check("settings record unpacks",
              preset_settings_unpack(rec, &bc, &mt) && bc == -1 && mt == 12);
    }

    memset(rec, 0xFF, PP_RECORD(4));
    check("erased record is empty", !preset_part_unpack(rec, 4, name, params));

    { /* the part-patch bank: two records, save, wipe, load back */
        static const int32_t a[4] = {1, 2, 3, 4}, b[4] = {-1, -2, -3, -4};
        memset(bank, 0xFF, sizeof bank);
        preset_part_pack(bank + 0 * PP_RECORD(4), "One", a, 4);
        preset_part_pack(bank + 31 * PP_RECORD(4), "Thirty", b, 4);
        check("part bank saves", preset_part_bank_save(bank, 4) == 0);
        memset(back, 0, sizeof back);
        check("part bank loads", preset_part_bank_load(back, 4) == 0);
        check("bank round-trips (slots 0 + 31, the rest empty)",
              !memcmp(bank, back, PP_BANK(4)) &&
                  preset_part_unpack(back + 0 * PP_RECORD(4), 4, name, params) &&
                  !strcmp(name, "One") &&
                  preset_part_unpack(back + 31 * PP_RECORD(4), 4, name, params) &&
                  !strcmp(name, "Thirty") &&
                  !preset_part_unpack(back + 1 * PP_RECORD(4), 4, name, params));
    }

    { /* the settings record save/load (re-pack first: `rec` held an erased record) */
        preset_settings_pack(rec, -1, 12);
        check("settings save/load round-trips",
              preset_settings_save(rec) == 0 && preset_settings_load(rec) == 0 &&
                  preset_settings_unpack(rec, &bc, &mt) && bc == -1 && mt == 12);
    }

    { /* the multi-patch bank: save, wipe, load back (the slot follows the part bank) */
        static uint8_t mbank[MP_BANK(2)], mback[MP_BANK(2)];
        static const uint8_t slots[2] = {0, 1};
        static const int32_t lv[2] = {32768, 16384}, dl[2] = {0, 5}, ch[2] = {0, 1};
        static const int32_t lo[2] = {0, 48}, hi[2] = {127, 96};
        memset(mbank, 0xFF, sizeof mbank);
        preset_multi_pack(mbank + 0 * MP_RECORD(2), "Comp", slots, lv, dl, ch, lo, hi, 2);
        preset_multi_pack(mbank + 63 * MP_RECORD(2), "Last", slots, lv, dl, ch, lo, hi, 2);
        check("multi bank saves", preset_multi_bank_save(mbank, 4, 2) == 0);
        memset(mback, 0, sizeof mback);
        check("multi bank loads", preset_multi_bank_load(mback, 4, 2) == 0);
        check("multi bank round-trips (slots 0 + 63, the rest empty)",
              !memcmp(mbank, mback, MP_BANK(2)) &&
                  preset_multi_unpack(mback + 0 * MP_RECORD(2), 2, name, slot, level, delay,
                                      channel, low, high) &&
                  !strcmp(name, "Comp") &&
                  preset_multi_unpack(mback + 63 * MP_RECORD(2), 2, name, slot, level, delay,
                                      channel, low, high) &&
                  !strcmp(name, "Last") &&
                  !preset_multi_unpack(mback + 1 * MP_RECORD(2), 2, name, slot, level, delay,
                                       channel, low, high));
    }

    printf("%s\n", bad ? "PRESETS TEST FAILED" : "presets test passed");
    return bad != 0;
}
