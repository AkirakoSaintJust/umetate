/* SPDX-License-Identifier: GPL-3.0-only */
/* A fake FM-1 in the browser: the app (src/rib.c) runs unchanged in WebAssembly.
 * platform.c includes this file instead of tests/host.c when UMETATE_WEB is set.
 * The page sends input (buttons/keys/encoders) and reads the screen (the 240x240
 * RGB565 framebuffer) and the audio (a ring the worklet drains) back through the
 * web_* exports. Audio is pull-based: the worklet calls web_render(n), which steps
 * the app one millisecond at a time until n frames exist, exactly as on the FM-1. */
#include <stdint.h>
#include <string.h>

#ifndef APP_NAME
#define APP_NAME "RIB"
#endif
#ifndef APP_VER
#define APP_VER "0.0"
#endif
#define FS 44100u
#define HALF_FRAMES 256u

static volatile uint32_t fm1_ms;
static uint32_t splash_left;            /* frames of logo to show before app_init */

/* ---- input (the FM-1 matrix, driven from JS) ---- */
#define HOST_NENC 7u
static struct { uint32_t notes, buttons; } fm1_in;
static uint32_t host_edges, host_rel;
static uint32_t fm1_input_edges(uint32_t *released)
{
    uint32_t b = host_edges;
    host_edges = 0;
    *released = host_rel;
    host_rel = 0;
    return b;
}
static uint32_t fm1_input_note_edges(void) { return 0; }
static int32_t host_enc[HOST_NENC];
static int32_t fm1_enc_take(uint32_t e) { int32_t v = host_enc[e % HOST_NENC]; host_enc[e % HOST_NENC] = 0; return v; }

static uint64_t host_leds;
static void fm1_irq_off(void) {}
static void fm1_irq_on(void) {}
static void fm1_led_key(uint32_t id, int on) { if (on) host_leds |= (uint64_t)1 << id; else host_leds &= ~((uint64_t)1 << id); }
static uint64_t host_glow;
static void fm1_led_key_glow(uint32_t id, int on) { if (on) host_glow |= (uint64_t)1 << id; else host_glow &= ~((uint64_t)1 << id); }

/* ---- the screen: 240 x 240 RGB565, as the ST7789 gets it (gfx.c sends bytes swapped) ---- */
static uint16_t fb[240 * 240];
static uint32_t blits;                              /* incremented on each lcd_blit: the page's dirty counter */
static void lcd_sync(void) {}
static void lcd_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t c)
{
    uint32_t i, j;
    for (j = y; j < y + h && j < 240u; j++)
        for (i = x; i < x + w && i < 240u; i++)
            fb[j * 240u + i] = c;
}
static void lcd_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *px)
{
    uint32_t i, j;
    for (j = 0; j < h; j++)
        for (i = 0; i < w; i++)
            if (x + i < 240u && y + j < 240u) {
                uint16_t c = px[j * w + i];
                fb[(y + j) * 240u + x + i] = (uint16_t)(c >> 8 | c << 8);
            }
    blits++;
}
#ifndef CV_MAX
#define CV_MAX (240u * 124u)
#endif
#include "gfx.c"
#include "logo.c"

/* ---- storage in RAM (lost at reload; the page could mirror it to localStorage) ---- */
#include "store.h"
static uint8_t host_set[SECTOR_MAX + 4], host_blob[NBLOB][SECTOR_MAX + 4], host_slot[NSLOT][SLOT_MAX + 4];
static int host_load(uint8_t *a, uint32_t max, void *p, uint32_t n)
{
    if (!a[0] || n > max || (uint32_t)(a[1] | a[2] << 8 | a[3] << 16) != n) return -1;
    memcpy(p, a + 4, n);
    return 0;
}
static int host_save(uint8_t *a, uint32_t max, const void *p, uint32_t n, const char *what, uint32_t i)
{
    (void)what; (void)i;
    if (n > max) return -1;
    a[0] = 1; a[1] = (uint8_t)n; a[2] = (uint8_t)(n >> 8); a[3] = (uint8_t)(n >> 16);
    memcpy(a + 4, p, n);
    return 0;
}
static int settings_load(void *p, uint32_t n) { return host_load(host_set, SECTOR_MAX, p, n); }
static int settings_save(const void *p, uint32_t n) { return host_save(host_set, SECTOR_MAX, p, n, "settings", 0); }
static int blob_load(uint32_t i, void *p, uint32_t n) { return i < NBLOB ? host_load(host_blob[i], SECTOR_MAX, p, n) : -1; }
static int blob_save(uint32_t i, const void *p, uint32_t n) { return i < NBLOB ? host_save(host_blob[i], SECTOR_MAX, p, n, "blob", i) : -1; }
static int slot_load(uint32_t i, void *p, uint32_t n) { return i < NSLOT ? host_load(host_slot[i], SLOT_MAX, p, n) : -1; }
static int slot_save(uint32_t i, const void *p, uint32_t n) { return i < NSLOT ? host_save(host_slot[i], SLOT_MAX, p, n, "slot", i) : -1; }

/* ---- MIDI: nothing in, nothing out (the browser has no device) ---- */
static int midi_get(uint8_t *st, uint8_t *d1, uint8_t *d2) { (void)st; (void)d1; (void)d2; return 0; }
static void midi_send(uint32_t st, uint32_t d1, uint32_t d2) { (void)st; (void)d1; (void)d2; }
static void midi_send_sysex(const uint8_t *frame, uint32_t n) { (void)frame; (void)n; }

static void app_audio(int32_t *out, uint32_t n);
static void app_init(void);
static void app_step(void);

/* ---- audio: a ring the worklet drains; platform_poll fills it, web_render empties it ---- */
#define RING 4096u
static float ring[RING * 2];
static uint32_t ring_frames, ring_read;

static void push_ring(const int32_t *blk, uint32_t n)
{
    uint32_t k;
    for (k = 0; k < n; k++) {
        uint32_t i = (ring_frames % RING) * 2u;
        ring[i] = (float)blk[2 * k] / 32768.0f;
        ring[i + 1] = (float)blk[2 * k + 1] / 32768.0f;
        ring_frames++;
    }
}

static void platform_poll(void)                    /* one call = one millisecond */
{
    static int32_t blk[2u * HALF_FRAMES];
    static uint32_t owed;
    fm1_ms++;
    owed += FS;
    while (owed >= 1000u * HALF_FRAMES) {
        owed -= 1000u * HALF_FRAMES;
        memset(blk, 0, sizeof blk);
        app_audio(blk, HALF_FRAMES);
        scope_push(blk, HALF_FRAMES);           /* ch 0: the final mix (the POST-FX scope) */
        push_ring(blk, HALF_FRAMES);
    }
}

/* ---- the exports the page calls ---- */
static float out_l[1024], out_r[1024];
__attribute__((used, visibility("default"))) float *web_out_l(void) { return out_l; }
__attribute__((used, visibility("default"))) float *web_out_r(void) { return out_r; }
__attribute__((used, visibility("default"))) void web_boot(void)
{
    uint32_t i;
    for (i = 0; i < 240u * 240u; i++)
        fb[i] = 0;                                  /* black until the first draw */
    logo_draw();                                    /* the boot splash */
    splash_left = SPLASH_MS * FS / 1000u;           /* ~0.7 s of logo before the app */
}
__attribute__((used, visibility("default"))) void web_step(void) { app_step(); }

/* n frames (<= 1024) into out_l / out_r: the device runs until they exist */
__attribute__((used, visibility("default"))) void web_render(uint32_t n)
{
    uint32_t k;
    if (n > 1024u)
        n = 1024u;
    if (splash_left) {                              /* hold the logo, silent, then boot */
        if (n > splash_left)
            n = splash_left;
        splash_left -= n;
        for (k = 0; k < n; k++) {
            out_l[k] = 0.0f;
            out_r[k] = 0.0f;
        }
        if (!splash_left)
            app_init();
        return;
    }
    while (ring_frames - ring_read < n)
        app_step();
    for (k = 0; k < n; k++) {
        uint32_t i = (ring_read % RING) * 2u;
        out_l[k] = ring[i];
        out_r[k] = ring[i + 1];
        ring_read++;
    }
}
__attribute__((used, visibility("default"))) uint16_t *web_fb(void) { return fb; }
__attribute__((used, visibility("default"))) uint32_t web_blits(void) { return blits; }
__attribute__((used, visibility("default"))) void web_buttons(uint32_t m)
{
    uint32_t prev = fm1_in.buttons;
    host_edges |= m & ~prev;                        /* press edges */
    host_rel |= ~m & prev;                          /* release edges */
    fm1_in.buttons = m;
}
__attribute__((used, visibility("default"))) void web_keys(uint32_t m) { fm1_in.notes = m; }
__attribute__((used, visibility("default"))) void web_enc(uint32_t role, int32_t n)
{
    if (role < HOST_NENC)
        host_enc[role] += n;
}
__attribute__((used, visibility("default"))) uint32_t web_lit_buttons(void) { return (uint32_t)(host_leds & 0x3FFFu); }
__attribute__((used, visibility("default"))) uint32_t web_lit_keys(void) { return (uint32_t)(host_leds >> 14); }
__attribute__((used, visibility("default"))) uint32_t web_dim_keys(void) { return (uint32_t)((host_glow >> 14) & ~(host_leds >> 14)); }
