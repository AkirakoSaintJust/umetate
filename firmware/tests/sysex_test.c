/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The device-side SysEx handler host test, which feeds frames (synth_sysex_feed) and
 * checks the dispatched responses (the stub midi_send_sysex captures them). The
 * identity + part-patch-read response hex is the cross-language parity fixture
 * against umetate/_sysex.py. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../src/synth_sysex.h"

/* the platform's SysEx send, captured for the checks */
static uint8_t tx[SYNTH_SX_MAX];
static uint32_t tx_len, tx_n;
void midi_send_sysex(const uint8_t *frame, uint32_t n)
{
    if (n <= SYNTH_SX_MAX) {
        memcpy(tx, frame, n);
        tx_len = n;
        tx_n++;
    }
}

/* the storage services (unused here; presets.c's bank functions need them) */
int slot_save(uint32_t i, const void *p, uint32_t n) { (void)i; (void)p; (void)n; return 0; }
int slot_load(uint32_t i, void *p, uint32_t n) { (void)i; (void)p; (void)n; return 0; }
int settings_save(const void *p, uint32_t n) { (void)p; (void)n; return 0; }
int settings_load(void *p, uint32_t n) { (void)p; (void)n; return 0; }

#include "../src/presets.c"
#include "../src/synth_sysex.c"

static uint8_t part_bank[PP_BANK(4)], multi_bank[MP_BANK(2)], settings[ST_RECORD];
static int32_t params[4] = {10, -20, 30, 40};

static int32_t get_param_stub(uint32_t id)
{
    return id < 4u ? params[id] : 0;
}

static synth_sysex_ctx ctx = {0x42, 4, 2, get_param_stub, part_bank, multi_bank, settings};

static int bad;
static void check(const char *what, int ok)
{
    printf("sysex: %-72s %s\n", what, ok ? "ok" : "FAIL");
    bad += !ok;
}

static void feed_frame(const uint8_t *f, uint32_t n)
{
    uint32_t i;
    for (i = 0; i < n; i++)
        synth_sysex_feed(f[i]);
}

static void print_hex(const char *tag, const uint8_t *p, uint32_t n)
{
    uint32_t i;
    printf("%s: ", tag);
    for (i = 0; i < n; i++)
        printf("%02x", p[i]);
    printf("\n");
}

/* a response's unpacked payload -> raw (returns the byte count) */
static uint32_t response_payload(uint8_t *raw, uint32_t want)
{
    return sx_unpack7(tx + 7u, tx_len - 10u, want, raw);
}

int main(void)
{
    static uint8_t buf[SYNTH_SX_MAX], raw[SYNTH_SX_MAX];
    static char name_buf[PRESET_NAME_LEN];
    static int32_t params_buf[4];
    static const int32_t rec3[4] = {7, 8, 9, 10};
    static const int32_t rec5[4] = {1, 1, 2, 3};
    uint32_t n, i, model, cmd, ver, pn;
    const uint8_t *pl;

    memset(part_bank, 0xFF, sizeof part_bank);
    memset(multi_bank, 0xFF, sizeof multi_bank);
    memset(settings, 0xFF, sizeof settings);
    preset_part_pack(part_bank + 3u * PP_RECORD(4), "Slot3", rec3, 4);
    preset_settings_pack(settings, -1, 12);

    /* identity request -> 0x81 with [model ver n_lo n_hi n_parts] */
    tx_n = 0;
    feed_frame(buf, sx_build(buf, 0x42, 0x01, 1, raw, 0));
    synth_sysex_poll(&ctx);
    check("identity request answered", tx_n == 1 && sx_parse(tx, tx_len, &model, &cmd, &ver, &pl, &pn) &&
              model == 0x42 && cmd == 0x81 &&
              response_payload(raw, 5) == 5 && raw[0] == 0x42 && raw[1] == 1 && raw[2] == 4 &&
              raw[3] == 0 && raw[4] == 2);
    print_hex("identity-hex", tx, tx_len);

    /* param dump -> 0x82 with the current params */
    tx_n = 0;
    feed_frame(buf, sx_build(buf, 0x42, 0x02, 1, raw, 0));
    synth_sysex_poll(&ctx);
    {
        int ok = tx_n == 1 && sx_parse(tx, tx_len, &model, &cmd, &ver, &pl, &pn) && cmd == 0x82 &&
                 response_payload(raw, 16) == 16;
        for (i = 0; ok && i < 4; i++)
            ok = (int32_t)((uint32_t)raw[4 * i] | (uint32_t)raw[4 * i + 1] << 8 |
                           (uint32_t)raw[4 * i + 2] << 16 | (uint32_t)raw[4 * i + 3] << 24) ==
                 params[i];
        check("param dump returns the current params", ok);
    }

    /* part-patch read (slot 3) -> 0x83 with slot + the record */
    tx_n = 0;
    raw[0] = 3;
    feed_frame(buf, sx_build(buf, 0x42, 0x03, 1, raw, 1));
    synth_sysex_poll(&ctx);
    check("part-patch read returns the slot's record",
          tx_n == 1 && sx_parse(tx, tx_len, &model, &cmd, &ver, &pl, &pn) && cmd == 0x83 &&
              response_payload(raw, 1 + PP_RECORD(4)) == 1 + PP_RECORD(4) && raw[0] == 3 &&
              preset_part_unpack(raw + 1, 4, name_buf, params_buf) && !strcmp(name_buf, "Slot3") &&
              !memcmp(params_buf, rec3, sizeof rec3));
    print_hex("partread-hex", tx, tx_len);

    /* part-patch write (slot 5) -> 0x83 ACK + the bank updated */
    tx_n = 0;
    raw[0] = 5;
    preset_part_pack(raw + 1, "Five", rec5, 4);
    feed_frame(buf, sx_build(buf, 0x42, 0x03, 1, raw, 1 + PP_RECORD(4)));
    synth_sysex_poll(&ctx);
    check("part-patch write updates the bank",
          tx_n == 1 && response_payload(raw, 1) == 1 && raw[0] == 5 &&
              preset_part_unpack(part_bank + 5u * PP_RECORD(4), 4, name_buf, params_buf) &&
              !strcmp(name_buf, "Five") && !memcmp(params_buf, rec5, sizeof rec5));

    /* settings read -> 0x85 with the record */
    tx_n = 0;
    feed_frame(buf, sx_build(buf, 0x42, 0x05, 1, raw, 0));
    synth_sysex_poll(&ctx);
    {
        int32_t bc = 0, mt = 0;
        check("settings read returns the record",
              tx_n == 1 && sx_parse(tx, tx_len, &model, &cmd, &ver, &pl, &pn) && cmd == 0x85 &&
                  response_payload(raw, ST_RECORD) == ST_RECORD &&
                  preset_settings_unpack(raw, &bc, &mt) && bc == -1 && mt == 12);
    }

    /* a bad CRC and a wrong model are ignored */
    tx_n = 0;
    n = sx_build(buf, 0x42, 0x01, 1, raw, 0);
    buf[n / 2u] ^= 1u;
    feed_frame(buf, n);
    synth_sysex_poll(&ctx);
    check("a bad-CRC frame is ignored", tx_n == 0);
    tx_n = 0;
    feed_frame(buf, sx_build(buf, 0x41, 0x01, 1, raw, 0));
    synth_sysex_poll(&ctx);
    check("a wrong-model frame is ignored", tx_n == 0);

    printf("%s\n", bad ? "SYSEX TEST FAILED" : "sysex test passed");
    return bad != 0;
}
