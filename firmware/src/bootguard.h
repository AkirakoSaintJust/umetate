/* SPDX-License-Identifier: GPL-3.0-only */
/* Warm-reset guard, retained in RAM only. Never writes the bootloader/flash.
 * This cannot rescue an image that fails before reaching the application. */
#ifndef FELUCCA_BOOTGUARD_H
#define FELUCCA_BOOTGUARD_H
#include <stdint.h>
#define BOOTGUARD_MAGIC 0x42475232u
#define BOOTGUARD_CHORD_MS 5000u
typedef struct { uint32_t magic, failed, pending; } bootguard_t;
enum { BOOT_NORMAL, BOOT_RECOVERY, BOOT_ROM };
static void bootguard_clear(bootguard_t *b)
{
    b->magic = BOOTGUARD_MAGIC;
    b->failed = b->pending = 0;
}
static uint32_t bootguard_begin(bootguard_t *b)
{
    if (b->magic != BOOTGUARD_MAGIC || b->failed > 2u || b->pending > 2u)
        bootguard_clear(b);
    if (b->pending == 2u) {           /* recovery itself reset: keep ROM fallback */
        bootguard_clear(b);
        return BOOT_ROM;
    }
    if (b->pending && b->failed < 2u) b->failed++;
    b->pending = b->failed >= 2u ? 2u : 1u;
    return b->pending == 2u ? BOOT_RECOVERY : BOOT_NORMAL;
}
#ifndef FM1_OCT_BOTH                  /* (host test without a HAL: the FM-1's OCT- = 0, OCT+ = 1) */
#define FM1_BTN_OCT_DOWN 0
#define FM1_BTN_OCT_UP 1
#define FM1_OCT_BOTH 3u
#endif
static int bootguard_manual(uint32_t buttons)
{
    return (buttons & FM1_OCT_BOTH) == 1u << FM1_BTN_OCT_DOWN;     /* physical OCT- alone; both keep calibration */
}

/* Running-firmware rescue chord: OCT- and OCT+ held together for
 * BOOTGUARD_CHORD_MS. `now` is a millisecond clock; releasing either button
 * starts the interval again. The caller reboots into BOOT_RECOVERY. */
typedef struct { uint32_t since; uint8_t held; } bootguard_chord_t;
static int bootguard_chord(bootguard_chord_t *c, uint32_t buttons, uint32_t now)
{
    if ((buttons & FM1_OCT_BOTH) != FM1_OCT_BOTH) {
        c->held = 0;
        return 0;
    }
    if (!c->held) {
        c->held = 1;
        c->since = now;
        return 0;
    }
    return (uint32_t)(now - c->since) >= BOOTGUARD_CHORD_MS;
}
#endif
