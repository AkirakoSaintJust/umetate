/* SPDX-License-Identifier: GPL-3.0-only */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/rib_dsp.h"

static void require(int ok, const char *message)
{
    if (!ok) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
    printf("ok: %s\n", message);
}

static uint32_t render_nonzero(int32_t *block)
{
    uint32_t i, any = 0;
    rib_dsp_render(block, 256);
    for (i = 0; i < 2u * 256u; i++)
        any |= block[i] != 0;
    return any;
}

int main(void)
{
    int32_t block[2 * 256] = {0};
    uint32_t i;

    rib_dsp_reset();
    require(rib_dsp_quiet(), "reset begins silent");
    rib_dsp_note_on(60, 100);
    require(!rib_dsp_quiet(), "note-on makes voice active");
    require(rib_dsp_lit(53) == (1u << 7), "key illumination follows active note");
    require(render_nonzero(block), "render produces non-silent stereo output");
    require(block[0] == block[1], "left and right channels are identical");

    rib_dsp_note_off(60);
    require(!rib_dsp_quiet(), "note-off retains release tail");
    for (i = 0; i < 64u; i++) {
        memset(block, 0, sizeof block);
        render_nonzero(block);
    }
    require(rib_dsp_quiet(), "release reaches silence");
    require(rib_dsp_lit(53) == 0, "released note is no longer illuminated");

    rib_dsp_note_on(200, 100);
    rib_dsp_note_on(60, 0);
    require(rib_dsp_quiet(), "out-of-range and zero-velocity notes are ignored");
    rib_dsp_note_on(127, 127);
    require(rib_dsp_lit(101) == (1u << 26), "highest MIDI note remains in the visible range");
    rib_dsp_set_bend_q16(65536u);
    require(render_nonzero(block), "center bend renders the high note");
    rib_dsp_set_bend_q16(70000u);
    require(render_nonzero(block), "positive bend remains active");
    rib_dsp_note_off(127);
    for (i = 0; i < 64u; i++) {
        memset(block, 0, sizeof block);
        render_nonzero(block);
    }
    require(rib_dsp_quiet(), "bent note releases to silence");

    rib_dsp_reset();
    require(rib_dsp_quiet() && rib_dsp_lit(53) == 0, "reset clears active notes and display state");
    puts("DSP test passed");
    return 0;
}
