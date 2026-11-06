/* SPDX-License-Identifier: GPL-3.0-only */
/* Copyright (C) 2026 P1Onken (umetate) */
/* The device-side SysEx handler implementation (synth_sysex.h): frame assembly
 * from the byte stream, envelope parse/build (CRC-16-CCITT over cmd..payload),
 * 7-bit packing, and the five-command dispatch. `midi_send_sysex` is the
 * platform's (provided by the includer: platform.c on device, a stub in tests). */
#include "synth_sysex.h"
#include "presets.h"
/* no <string.h> here: the device TU gets memset/memcpy/memcmp from the platform's
 * libc.c (included before this file); the standalone host tests include it first. */

/* ---- the incoming frame assembly (fed from the platform's SysEx byte stream) */
/* (`synth_sx_*`: the platform's usb.c owns the `sx_*` names for its boot/OTA magic) */
static uint8_t synth_sx_buf[SYNTH_SX_MAX];
static uint32_t synth_sx_len, synth_sx_on;
static volatile uint32_t synth_sx_ready; /* the USB context writes, the main loop clears */

void synth_sysex_feed(uint8_t b)
{
    if (b >= 0xF8u)
        return; /* realtime may occur anywhere in SysEx */
    if (b == 0xF0) {
        synth_sx_on = !synth_sx_ready; /* drop a new frame while the last is unread */
        synth_sx_len = 0;
    }
    if (!synth_sx_on)
        return;
    if (b != 0xF7u && synth_sx_len >= SYNTH_SX_MAX) {
        synth_sx_on = 0; /* too long: not ours */
        return;
    }
    /* USB-MIDI SysEx bytes are 8-bit (the CRC-16 trailer may set bit 7); a stray
     * status byte mid-frame only corrupts the CRC, which the poll rejects */
    synth_sx_buf[synth_sx_len++] = b;
    if (b == 0xF7u) {
        synth_sx_ready = 1;
        synth_sx_on = 0;
    }
}

/* ---- the envelope (the C mirror of umetate/_sysex.py) */

static uint32_t sx_pack7(const uint8_t *in, uint32_t n, uint8_t *out)
{
    uint32_t i = 0, o = 0;
    while (i < n) {
        uint32_t j, top = 0;
        for (j = 0; j < 7u && i < n; j++, i++) {
            out[o++] = in[i] & 0x7Fu;
            top |= (uint32_t)(in[i] >> 7) << j;
        }
        out[o++] = (uint8_t)top;
    }
    return o;
}

static uint32_t sx_unpack7(const uint8_t *in, uint32_t n, uint32_t want, uint8_t *out)
{
    uint32_t i = 0, o = 0;
    while (i < n && o < want) {
        uint32_t g = i + 8u < n ? i + 8u : n; /* the group's end: its last byte holds the top bits */
        uint8_t top = in[g - 1u];
        for (; i + 1u < g && o < want; i++)
            out[o++] = (uint8_t)((in[i] & 0x7Fu) | ((top >> (i & 7u)) & 1u) << 7);
        i = g;
    }
    return o;
}

/* parse: F0 00 21 1D model cmd ver payload… crc16 F7 -> 1 + the fields, 0 otherwise */
static int sx_parse(const uint8_t *f, uint32_t n, uint32_t *model, uint32_t *cmd,
                    uint32_t *ver, const uint8_t **payload, uint32_t *pn)
{
    if (n < 10u || f[0] != 0xF0u || f[n - 1u] != 0xF7u || f[1] != 0x00u || f[2] != 0x21u ||
        f[3] != 0x1Du)
        return 0;
    if (preset_crc16(f + 5u, n - 8u) !=
        (uint16_t)((uint16_t)f[n - 3u] | (uint16_t)f[n - 2u] << 8))
        return 0;
    *model = f[4];
    *cmd = f[5];
    *ver = f[6];
    *payload = f + 7u;
    *pn = n - 10u;
    return 1;
}

/* build a response frame; returns its length (the payload is 7-bit packed inside) */
static uint32_t sx_build(uint8_t *out, uint32_t model, uint32_t cmd, uint32_t ver,
                         const uint8_t *payload, uint32_t pn)
{
    uint32_t pl = sx_pack7(payload, pn, out + 7u);
    uint16_t c;
    out[0] = 0xF0u;
    out[1] = 0x00u;
    out[2] = 0x21u;
    out[3] = 0x1Du;
    out[4] = (uint8_t)model;
    out[5] = (uint8_t)cmd;
    out[6] = (uint8_t)ver;
    c = preset_crc16(out + 5u, 2u + pl);
    out[7u + pl] = (uint8_t)c;
    out[8u + pl] = (uint8_t)(c >> 8);
    out[9u + pl] = 0xF7u;
    return 10u + pl;
}

/* ---- the dispatch */

void synth_sysex_poll(const synth_sysex_ctx *ctx)
{
    static uint8_t frame[SYNTH_SX_MAX], out[SYNTH_SX_MAX], raw[SYNTH_SX_MAX];
    uint32_t model, cmd, ver, pn, n, i, rn, rec;
    const uint8_t *payload;
    uint8_t *bank;

    if (!synth_sx_ready)
        return;
    n = synth_sx_len;
    memcpy(frame, synth_sx_buf, n); /* copy: the feed may already assemble the next frame */
    synth_sx_ready = 0;
    if (!sx_parse(frame, n, &model, &cmd, &ver, &payload, &pn) || model != ctx->model)
        return;

    if (cmd == 0x01u) { /* identity request -> the firmware identity */
        uint8_t id[5] = {(uint8_t)ctx->model, (uint8_t)ver, (uint8_t)ctx->n_params,
                         (uint8_t)(ctx->n_params >> 8), (uint8_t)ctx->n_parts};
        midi_send_sysex(out, sx_build(out, ctx->model, 0x81u, ver, id, 5u));
    } else if (cmd == 0x02u) { /* param dump: the current timbre params */
        if (ctx->n_params <= SYNTH_PARAM_MAX && ctx->get_param) {
            for (i = 0; i < ctx->n_params; i++) {
                uint32_t v = (uint32_t)ctx->get_param(i);
                raw[4u * i] = (uint8_t)v;
                raw[4u * i + 1u] = (uint8_t)(v >> 8);
                raw[4u * i + 2u] = (uint8_t)(v >> 16);
                raw[4u * i + 3u] = (uint8_t)(v >> 24);
            }
            midi_send_sysex(out, sx_build(out, ctx->model, 0x82u, ver, raw, 4u * ctx->n_params));
        }
    } else if (cmd == 0x03u || cmd == 0x04u) { /* single-part / multi-patch dump */
        uint32_t max_slot = cmd == 0x03u ? PRESET_PART_SLOTS : PRESET_MULTI_SLOTS;
        rec = cmd == 0x03u ? PP_RECORD(ctx->n_params) : MP_RECORD(ctx->n_parts);
        bank = cmd == 0x03u ? ctx->part_bank : ctx->multi_bank;
        rn = sx_unpack7(payload, pn, 1u + rec, raw);
        if (rn == 1u && raw[0] < max_slot && bank) { /* a read: the slot's record */
            memcpy(raw + 1u, bank + (uint32_t)raw[0] * rec, rec);
            midi_send_sysex(out, sx_build(out, ctx->model, cmd | 0x80u, ver, raw, 1u + rec));
        } else if (rn == 1u + rec && raw[0] < max_slot && bank) { /* a write */
            memcpy(bank + (uint32_t)raw[0] * rec, raw + 1u, rec);
            midi_send_sysex(out, sx_build(out, ctx->model, cmd | 0x80u, ver, raw, 1u));
        }
    } else if (cmd == 0x05u) { /* settings dump / write */
        rn = sx_unpack7(payload, pn, ST_RECORD, raw);
        if (rn == ST_RECORD && ctx->settings) { /* a write */
            memcpy(ctx->settings, raw, ST_RECORD);
            midi_send_sysex(out, sx_build(out, ctx->model, 0x85u, ver, raw, 1u));
        } else if (rn == 0u && ctx->settings) { /* a read */
            midi_send_sysex(out, sx_build(out, ctx->model, 0x85u, ver, ctx->settings, ST_RECORD));
        }
    } else { /* unknown command */
        midi_send_sysex(out, sx_build(out, ctx->model, 0xFFu, ver, raw, 0u));
    }
}
