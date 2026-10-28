# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The voice-management rails (docs/roadmap.md §6.11.4): emission of the per-voice
state, the universal voice-mode params, and the note_on/off/all_off/reset
allocation.

Pure emission (like `_backend`): every function returns C source lines. The
synth-specific note→increment glue lives in `<name>_note_derived` (emitted by the
backend); this module owns the allocation semantics — poly / mono / unison — and
the per-voice base increment `voice_inc[v]` (note_to_inc × detune) that the
note-derived increments scale. Portamento (glide) ramps `voice_inc[v]` toward
`voice_target_inc[v]` at a constant rate (linear in the increment, no LUT); the
ramp lives in `glide()` and re-runs the note→increment glue each block.
"""

from __future__ import annotations

from ._ir import ParamEntry

# (cname, default, friendly name, min, max, unit) for the six universal voice-mode
# params, appended after a patch's own node params (ids N..N+5).
MODE_PARAMS: tuple[tuple[str, int, str, int, int, str], ...] = (
    ("vm_mode", 0, "mode", 0, 2, ""),  # 0=poly 1=mono 2=unison
    ("vm_unison_count", 1, "unison_count", 1, 8, ""),
    ("vm_unison_detune", 0, "unison_detune", 0, 200, "cents"),
    ("vm_legato", 0, "legato", 0, 1, ""),
    ("vm_portamento", 0, "portamento", 0, 65536, ""),  # Q16 glide rate (0 = off)
    ("vm_note_priority", 0, "note_priority", 0, 2, ""),  # 0=last 1=highest 2=lowest
)


def mode_param_entries(start_id: int) -> list[ParamEntry]:
    """The six mode params as ParamEntrys with ids `start_id`..`start_id+5`."""
    return [
        ParamEntry(
            id=start_id + i,
            name=name,
            target=cname,
            cname=cname,
            min=lo,
            max=hi,
            default=default_,
            curve="linear",
            unit=unit,
            rate="block",
            modulatable=False,
        )
        for i, (cname, default_, name, lo, hi, unit) in enumerate(MODE_PARAMS)
    ]


def voice_state_decls() -> list[str]:
    """Per-voice SoA state + the mono held-note tracker (all CPU1)."""
    return [
        "static uint8_t voice_gate[NVOICE] UMETATE_CPU1;",
        "static uint8_t voice_note[NVOICE] UMETATE_CPU1;",
        "static uint32_t voice_age[NVOICE] UMETATE_CPU1;",
        "static int32_t voice_velocity[NVOICE] UMETATE_CPU1;",
        "static uint8_t voice_trig[NVOICE] UMETATE_CPU1;",
        "static uint32_t voice_inc[NVOICE] UMETATE_CPU1; /* current base increment */",
        "static uint32_t voice_target_inc[NVOICE] UMETATE_CPU1; /* glide target */",
        "static int32_t voice_detune[NVOICE] UMETATE_CPU1;",
        "static uint8_t mono_held[128] UMETATE_CPU1;",
        "static uint32_t mono_order[128] UMETATE_CPU1;",
        "static uint32_t mono_serial;",
        "static uint32_t ages;",
    ]


def mode_param_decls() -> list[str]:
    """The six `static int32_t vm_*` backing variables (in the param slot table)."""
    return [
        f"static int32_t {cname} = {default_};" for cname, default_, *_ in MODE_PARAMS
    ]


def helpers() -> list[str]:
    """Static helpers shared by note_on/note_off."""
    return [
        "static inline uint32_t voice_mono_active(int32_t priority) {",
        "    uint32_t active = 0xFFu;",
        "    for (uint32_t n = 0; n < 128u; n++) {",
        "        if (!mono_held[n]) continue;",
        "        if (active == 0xFFu) { active = n; continue; }",
        "        if (priority == 2) { if (n < active) active = n; }",
        "        else if (priority == 1) { if (n > active) active = n; }",
        "        else { if (mono_order[n] > mono_order[active]) active = n; }",
        "    }",
        "    return active;",
        "}",
        "",
    ]


def note_on(name: str) -> list[str]:
    """The `<name>_dsp_note_on` body: mode-aware allocation + assignment, calling
    `<name>_note_derived(pick)` for the synth-specific note→increment glue."""
    return [
        f"void {name}_dsp_note_on(uint32_t note, uint32_t velocity) {{",
        "    if (note > 127u || !velocity) return;",
        "    uint8_t picked[NVOICE];",
        "    uint32_t npicked = 0;",
        "    uint8_t trig = 1; /* poly/unison retrigger; mono overrides */",
        "    uint32_t snote = note; /* the note that sounds (mono note_priority) */",
        "",
        "    if (vm_mode == 1) {",
        "        mono_held[note]++;",
        "        mono_order[note] = ++mono_serial;",
        "        trig = (uint8_t)((vm_legato && voice_gate[0]) ? 0u : 1u);",
        "        snote = voice_mono_active(vm_note_priority);",
        "        picked[0] = 0; npicked = 1;",
        "        voice_detune[0] = 65536;",
        "    } else if (vm_mode == 2) {",
        "        uint8_t chosen[NVOICE];",
        "        for (uint32_t v = 0; v < NVOICE; v++) chosen[v] = 0;",
        "        uint32_t count = (uint32_t)vm_unison_count;",
        "        if (count < 1u) count = 1u;",
        "        if (count > NVOICE) count = NVOICE;",
        "        int32_t span = vm_unison_detune;",
        "        for (uint32_t k = 0; k < count; k++) {",
        "            uint32_t best = 0xFFFFFFFFu, bp = 0;",
        "            for (uint32_t v = 0; v < NVOICE; v++) {",
        "                if (chosen[v]) continue;",
        "                uint32_t score = voice_gate[v] ? 0x80000000u + voice_age[v]",
        "                                 : voice_age[v] + 1u;",
        "                if (score < best) { best = score; bp = v; }",
        "            }",
        "            chosen[bp] = 1; picked[k] = bp;",
        "            if (count <= 1u) {",
        "                voice_detune[bp] = 65536;",
        "            } else {",
        "                int32_t step = span / (int32_t)(count - 1u);",
        "                int32_t cents = -span / 2 + (int32_t)k * step;",
        "                /* 2^(c/1200) ~= 1 + c·ln2/1200 for the small unison range */",
        "                voice_detune[bp] = 65536 + cents * 38;",
        "            }",
        "        }",
        "        npicked = count;",
        "    } else {",
        "        uint32_t best = 0xFFFFFFFFu;",
        "        for (uint32_t v = 0; v < NVOICE; v++) {",
        "            uint32_t score = (voice_note[v] == note && voice_gate[v]) ? 0u",
        "                           : voice_gate[v] ? 0x80000000u + voice_age[v]",
        "                                           : voice_age[v] + 1u;",
        "            if (score < best) { best = score; picked[0] = v; }",
        "        }",
        "        npicked = 1;",
        "        voice_detune[picked[0]] = 65536;",
        "    }",
        "",
        "    for (uint32_t k = 0; k < npicked; k++) {",
        "        uint32_t pick = picked[k];",
        "        uint8_t was = voice_gate[pick]; /* sounding before this note-on? */",
        "        voice_note[pick] = (uint8_t)snote;",
        "        voice_age[pick] = ++ages;",
        "        voice_gate[pick] = 1;",
        "        voice_trig[pick] = trig;",
        "        /* 0..127 -> q15 (32767/127 ~= 258) */",
        "        voice_velocity[pick] = (int32_t)(velocity * 258u);",
        "        voice_target_inc[pick] = (uint32_t)(((uint64_t)note_to_inc(snote) * ",
        "(uint32_t)voice_detune[pick]) >> 16);",
        "        /* a fresh voice snaps to pitch; a steal glides when portamento is on */",
        "        if (!vm_portamento || !was) voice_inc[pick] = voice_target_inc[pick];",
        f"        {name}_note_derived(pick);",
        "    }",
        "}",
        "",
    ]


def note_off(name: str) -> list[str]:
    """The `<name>_dsp_note_off` body (mono note_priority takeover, else poly)."""
    return [
        f"void {name}_dsp_note_off(uint32_t note) {{",
        "    if (note > 127u) return;",
        "    if (vm_mode == 1) {",
        "        if (mono_held[note]) mono_held[note]--;",
        "        uint32_t active = voice_mono_active(vm_note_priority);",
        "        if (active == 0xFFu) { voice_gate[0] = 0; return; }",
        "        if (active != (uint32_t)voice_note[0]) {",
        "            voice_note[0] = (uint8_t)active;",
        "            if (!vm_legato) voice_trig[0] = 1;",
        "            voice_target_inc[0] = (uint32_t)(((uint64_t)note_to_inc(active) * ",
        "(uint32_t)voice_detune[0]) >> 16);",
        "            if (!vm_portamento) voice_inc[0] = voice_target_inc[0];",
        f"            {name}_note_derived(0);",
        "        }",
        "        return;",
        "    }",
        "    for (uint32_t v = 0; v < NVOICE; v++)",
        "        if (voice_note[v] == note) voice_gate[v] = 0;",
        "}",
        "",
    ]


def glide(name: str) -> list[str]:
    """The per-block portamento ramp (indented for the render loop): move each
    gated voice's `voice_inc[v]` toward `voice_target_inc[v]` at a constant rate
    (linear in the increment, one add per voice per block), re-deriving the
    note→increment glue when the increment moves."""
    return [
        "        if (vm_portamento) {",
        "            for (uint32_t v = 0; v < NVOICE; v++) {",
        "                if (!voice_gate[v]) continue;",
        "                uint32_t cur = voice_inc[v];",
        "                uint32_t tgt = voice_target_inc[v];",
        "                if (cur != tgt) {",
        "                    uint32_t step = (uint32_t)(((uint64_t)tgt *",
        "                        (uint32_t)vm_portamento) >> 16);",
        "                    if (step < 1u) step = 1u;",
        "                    if (tgt > cur) {",
        "                        cur += step; if (cur > tgt) cur = tgt;",
        "                    } else {",
        "                        cur -= step; if (cur < tgt) cur = tgt;",
        "                    }",
        "                    voice_inc[v] = cur;",
        f"                    {name}_note_derived(v);",
        "                }",
        "            }",
        "        }",
    ]


def all_off() -> list[str]:
    """The all-notes-off (panic) body: release every voice + the mono tracker."""
    return [
        "    for (uint32_t v = 0; v < NVOICE; v++) voice_gate[v] = 0;",
        "    for (uint32_t n = 0; n < 128u; n++) mono_held[n] = 0;",
    ]


def reset() -> list[str]:
    """The reset body: all-off + age/serial zero."""
    return [
        "    for (uint32_t v = 0; v < NVOICE; v++) voice_gate[v] = 0;",
        "    for (uint32_t n = 0; n < 128u; n++) mono_held[n] = 0;",
        "    ages = 0;",
        "    mono_serial = 0;",
    ]
