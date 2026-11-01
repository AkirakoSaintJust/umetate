/* SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 P1Onken (umetate) */
/* The boot splash: the umetate wordmark (gen/logo.h, from assets/umetate240.png,
 * set in the "Digital Desolation Plus" typeface — see
 * assets/Digital-Desolation-Plus-LICENSE.txt). The logo is a row-major RLE stream
 * of byte-swapped RGB565 (matching gfx.c's canvas: the ST7789 takes big-endian
 * RGB565), so logo_draw() decodes it into a small RAM row buffer and blits one
 * row at a time — the panel's DMA reads RAM only, and a full 240x240 framebuffer
 * does not fit the reserved RAM. */

#include "logo.h"

#define SPLASH_MS 700u               /* how long the logo stays before the app */

static uint16_t logo_row[LOGO_W];    /* RAM: the DMA source, one row at a time */

static void logo_draw(void)
{
    const uint16_t *p = LOGO_RLE;
    uint32_t x = 0, y = 0;
    while (y < LOGO_H) {
        uint16_t n = *p++;
        if (!n)
            break;                   /* stream end (the screen is already black) */
        uint16_t c = *p++;
        while (n--) {
            if (x == 0u)
                lcd_sync();          /* the previous row's DMA still reads logo_row */
            logo_row[x++] = c;
            if (x == LOGO_W) {
                lcd_blit(0, y++, LOGO_W, 1, logo_row);
                x = 0;
            }
        }
    }
    lcd_sync();                      /* finish the last row */
}
