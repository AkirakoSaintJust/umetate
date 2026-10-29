/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The preset store (docs/roadmap.md §6.11.4): the record byte layouts + the bank
 * save/load over the platform's storage services. The layouts are byte-exact
 * little-endian and must match `umetate/_records.py` (proven by the parity test).
 *
 * A record is a self-validating unit: a version byte (0xFF = empty), a body, and
 * a CRC-32 (poly 0xEDB88320 — the platform's crc32) over version+body. The banks
 * live in slot 0 (part patches) and slot 1 (multi patches); the settings record
 * in the settings sector. Save only when silent (the platform's area_save erases
 * with interrupts off). */
#pragma once
#include <stdint.h>

#define PRESET_NAME_LEN 16u
#define PRESET_VERSION 1u
#define PRESET_EMPTY 0xFFu
#define PRESET_SLOTS 64u

#define PP_RECORD(N) (1u + PRESET_NAME_LEN + (N) * 4u + 4u)
#define MP_RECORD(P) (1u + PRESET_NAME_LEN + (P) + (P) * 5u * 4u + 4u)
#define ST_RECORD (1u + 4u + 4u + 4u)
#define PP_BANK(N) (PRESET_SLOTS * PP_RECORD(N))
#define MP_BANK(P) (PRESET_SLOTS * MP_RECORD(P))

uint32_t preset_crc32(const uint8_t *p, uint32_t n);

/* pack -> the record length; the name is truncated to PRESET_NAME_LEN-1 chars. */
uint32_t preset_part_pack(uint8_t *out, const char *name, const int32_t *params, uint32_t n);
uint32_t preset_multi_pack(uint8_t *out, const char *name, const uint8_t *part_slot,
                           const int32_t *level, const int32_t *delay, const int32_t *channel,
                           const int32_t *low, const int32_t *high, uint32_t p);
uint32_t preset_settings_pack(uint8_t *out, int32_t base_channel, int32_t master_tune);

/* unpack -> 1 and fills the outputs; 0 when the slot is empty or the CRC fails
 * (the outputs are then left untouched). */
int preset_part_unpack(const uint8_t *raw, uint32_t n, char *name, int32_t *params);
int preset_multi_unpack(const uint8_t *raw, uint32_t p, char *name, uint8_t *part_slot,
                        int32_t *level, int32_t *delay, int32_t *channel, int32_t *low,
                        int32_t *high);
int preset_settings_unpack(const uint8_t *raw, int32_t *base_channel, int32_t *master_tune);

/* banks: slot 0 / slot 1 / the settings sector, over the platform's services. */
int preset_part_bank_save(const uint8_t *bank, uint32_t n);
int preset_part_bank_load(uint8_t *bank, uint32_t n);
int preset_multi_bank_save(const uint8_t *bank, uint32_t p);
int preset_multi_bank_load(uint8_t *bank, uint32_t p);
int preset_settings_save(const uint8_t *rec);
int preset_settings_load(uint8_t *rec);
