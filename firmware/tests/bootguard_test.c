/* SPDX-License-Identifier: GPL-3.0-only */
/* Host regression for the warm-reset boot guard and the running-firmware
 * rescue chord. No hardware: bootguard.h's OCT fallback is used here. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "../src/bootguard.h"

static void require(int ok, const char *message)
{
    if (!ok) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
    printf("ok: %s\n", message);
}

int main(void)
{
    bootguard_t b = {0};
    bootguard_chord_t c = {0};

    /* Fresh RAM: the guard clears itself and the first boot is attempt 1. */
    require(bootguard_begin(&b) == BOOT_NORMAL, "fresh guard boots normally");
    require(b.magic == BOOTGUARD_MAGIC && b.failed == 0 && b.pending == 1,
            "the first boot is attempt 1");

    /* The platform clears the guard after 30 s of uptime. */
    bootguard_clear(&b);
    require(bootguard_begin(&b) == BOOT_NORMAL, "a confirmed boot starts a new count");
    require(bootguard_begin(&b) == BOOT_NORMAL, "one reset before confirmation is still normal");
    require(bootguard_begin(&b) == BOOT_RECOVERY, "two resets before confirmation enter recovery");
    require(bootguard_begin(&b) == BOOT_ROM, "a reset inside recovery falls back to ROM");
    require(bootguard_begin(&b) == BOOT_NORMAL, "the guard is clear after the ROM fallback");

    /* Boot-time trigger: OCT- alone. Both buttons are the running chord. */
    require(bootguard_manual(1u << FM1_BTN_OCT_DOWN), "OCT- alone is the boot-time rescue key");
    require(!bootguard_manual(FM1_OCT_BOTH), "both OCT keys are the running chord, not the boot key");
    require(!bootguard_manual(1u << FM1_BTN_OCT_UP), "OCT+ alone is not a rescue key");

    /* The chord must be held continuously for five seconds. */
    require(!bootguard_chord(&c, FM1_OCT_BOTH, 1000u), "the chord starts its interval");
    require(!bootguard_chord(&c, FM1_OCT_BOTH, 1000u + BOOTGUARD_CHORD_MS - 1u),
            "the chord below five seconds does not fire");
    require(bootguard_chord(&c, FM1_OCT_BOTH, 1000u + BOOTGUARD_CHORD_MS),
            "the chord fires at five seconds");

    /* Releasing either button restarts the interval. */
    require(!bootguard_chord(&c, 0, 7000u), "releasing the chord resets it");
    require(!bootguard_chord(&c, FM1_OCT_BOTH, 7100u), "a new hold starts a new interval");
    require(!bootguard_chord(&c, FM1_OCT_BOTH, 7100u + BOOTGUARD_CHORD_MS - 1u),
            "a new hold must still last five seconds");
    require(bootguard_chord(&c, FM1_OCT_BOTH, 7100u + BOOTGUARD_CHORD_MS),
            "the new hold fires at five seconds");

    require(!bootguard_chord(&c, 1u << FM1_BTN_OCT_DOWN, 13000u), "one button is not the chord");
    require(!bootguard_chord(&c, FM1_OCT_BOTH, 13001u),
            "the interval restarts when the second button returns");
    require(!bootguard_chord(&c, FM1_OCT_BOTH, 13001u + BOOTGUARD_CHORD_MS - 1u),
            "the restarted interval is still five seconds");
    require(bootguard_chord(&c, FM1_OCT_BOTH, 13001u + BOOTGUARD_CHORD_MS),
            "the restarted interval fires");

    /* A chord reset arms the next boot for recovery, not ROM. */
    bootguard_clear(&b);
    b.failed = 2;
    b.pending = 0;
    require(bootguard_begin(&b) == BOOT_RECOVERY, "a chord reset boots into recovery");
    require(bootguard_begin(&b) == BOOT_ROM, "a reset inside that recovery still falls back to ROM");

    printf("bootguard_test: all checks passed\n");
    return 0;
}
