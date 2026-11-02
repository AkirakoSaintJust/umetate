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

The six mode params are **per-part** when the patch is multitimbral (`n_parts > 1`):
each part has its own poly/unison/legato + counts + times. Single-timbre keeps them
global. `mode_ref` emits the right accessor for the current addressing mode.
"""

from __future__ import annotations

from ._ir import ParamEntry

# The release tail: a released voice stays allocated (rendered with gate=0, so its
# envelope runs the release stage) for up to this many control blocks before it is
# freed for stealing. 8192 blocks ≈ 5.9 s at 44100/32 — long enough for the
# slowest DX rate (0 ≈ 5.7 s to −72 dB). The voice is silent (and steal-first)
# once its envelope actually reaches zero; this only bounds the hold.
RELEASE_BLOCKS = 8192

# (cname, default, friendly name, min, max, unit, display) for the six universal
# voice-mode params. Multi-timbre: per-part arrays addressed through the part
# index; the single-timbre fallback keeps them global scalars.
MODE_PARAMS: tuple[tuple[str, int, str, int, int, str, str, str], ...] = (
    ("vm_mode", 0, "mode", 0, 2, "", "mode", "linear"),  # 0=poly 1=mono 2=unison
    ("vm_unison_count", 1, "unison_count", 1, 8, "", "raw", "linear"),
    ("vm_unison_detune", 0, "unison_detune", 0, 200, "cents", "raw", "linear"),
    ("vm_legato", 0, "legato", 0, 1, "", "onoff", "linear"),
    (
        "vm_portamento",
        0,
        "portamento",
        0,
        5000,
        "",
        "porta",
        "log",
    ),  # the one-octave glide time in ms (0 = off), log-stepped
    (
        "vm_note_priority",
        0,
        "note_priority",
        0,
        2,
        "",
        "priority",
        "linear",
    ),  # 0=last 1=highest 2=lowest
)


def mode_param_entries(
    start_id: int, n_parts: int = 1, only_part: int | None = None
) -> list[ParamEntry]:
    """The six mode params as ParamEntrys. Single-timbre (n_parts == 1): global
    (part=None). Multi-timbre: per-part (part 0..n_parts-1, `.p{p}` names);
    `only_part` restricts to one part (the voice block builds them part-major)."""
    entries: list[ParamEntry] = []
    for cname, default_, name, lo, hi, unit, disp, curve in MODE_PARAMS:
        if n_parts > 1:
            parts = [only_part] if only_part is not None else list(range(n_parts))
            for p in parts:
                entries.append(
                    ParamEntry(
                        id=start_id + len(entries),
                        name=f"{name}.p{p}",
                        target=cname,
                        cname=cname,
                        part=p,
                        min=lo,
                        max=hi,
                        default=default_,
                        curve=curve,
                        unit=unit,
                        rate="block",
                        modulatable=False,
                        display=disp,
                    )
                )
        else:
            entries.append(
                ParamEntry(
                    id=start_id + len(entries),
                    name=name,
                    target=cname,
                    cname=cname,
                    part=None,
                    min=lo,
                    max=hi,
                    default=default_,
                    curve=curve,
                    unit=unit,
                    rate="block",
                    modulatable=False,
                    display=disp,
                )
            )
    return entries


def mode_param_decls(n_parts: int) -> list[str]:
    """The `static int32_t vm_*` backing variables: global scalars (single-timbre)
    or per-part arrays (multi-timbre)."""
    if n_parts > 1:
        return [
            f"static int32_t {cname}[{n_parts}] = {{ "
            + ", ".join(str(default_) for _ in range(n_parts))
            + " };"
            for cname, default_, *_ in MODE_PARAMS
        ]
    return [
        f"static int32_t {cname} = {default_};" for cname, default_, *_ in MODE_PARAMS
    ]


def mode_ref(cname: str, per_part: bool, part_expr: str) -> str:
    """The C accessor for a mode param: `cname[part_expr]` when per-part, else the
    global scalar `cname`."""
    return f"{cname}[{part_expr}]" if per_part else cname


def voice_state_decls(per_part: bool) -> list[str]:
    """Per-voice SoA state + the mono held-note tracker (all CPU1)."""
    lines = [
        "static uint8_t voice_gate[NVOICE] UMETATE_CPU1;",
        "static uint8_t voice_note[NVOICE] UMETATE_CPU1;",
        "static uint32_t voice_age[NVOICE] UMETATE_CPU1;",
        "static int32_t voice_velocity[NVOICE] UMETATE_CPU1;",
        "static uint8_t voice_trig[NVOICE] UMETATE_CPU1;",
        "static uint8_t voice_part[NVOICE] UMETATE_CPU1; /* the part a voice belongs to */",
        "static uint32_t voice_delay[NVOICE] UMETATE_CPU1; /* onset-offset samples (0 = live) */",
        "static uint16_t voice_rel[NVOICE] UMETATE_CPU1; /* release-tail blocks (0 = live or idle) */",
        "static uint32_t voice_inc[NVOICE] UMETATE_CPU1; /* current base increment */",
        "static uint32_t voice_target_inc[NVOICE] UMETATE_CPU1; /* glide target */",
        "static int32_t voice_detune[NVOICE] UMETATE_CPU1;",
    ]
    if per_part:
        lines += [
            "static uint8_t mono_held[N_PART][128] UMETATE_CPU1;",
            "static uint32_t mono_order[N_PART][128] UMETATE_CPU1;",
            "static uint32_t mono_serial[N_PART] UMETATE_CPU1;",
            "static uint8_t part_mono_voice[N_PART] UMETATE_CPU1; /* the part's mono voice */",
        ]
    else:
        lines += [
            "static uint8_t mono_held[128] UMETATE_CPU1;",
            "static uint32_t mono_order[128] UMETATE_CPU1;",
            "static uint32_t mono_serial;",
        ]
    lines.append("static uint32_t ages;")
    return lines


def helpers(per_part: bool) -> list[str]:
    """Static helpers shared by note_on/note_off. `voice_mono_active` is emitted
    into the SRAM `.dsp_text` section (it is called from the note handlers that run
    on the DSP core), so it must be `always_inline` — a compiler-chosen call would
    branch from SRAM into the XIP `.text` section (rejected by build.py)."""
    if per_part:
        return [
            "static inline __attribute__((always_inline)) uint32_t voice_mono_active(",
            "        uint32_t p, int32_t priority) {",
            "    uint32_t active = 0xFFu;",
            "    for (uint32_t n = 0; n < 128u; n++) {",
            "        if (!mono_held[p][n]) continue;",
            "        if (active == 0xFFu) { active = n; continue; }",
            "        if (priority == 2) { if (n < active) active = n; }",
            "        else if (priority == 1) { if (n > active) active = n; }",
            "        else { if (mono_order[p][n] > mono_order[p][active]) active = n; }",
            "    }",
            "    return active;",
            "}",
            "",
            "static inline __attribute__((always_inline)) uint32_t voice_highest_note(void) {",
            "    uint32_t v, max = 0u;",
            "    for (v = 0; v < NVOICE; v++)",
            "        if (voice_gate[v] && voice_note[v] > max) max = voice_note[v];",
            "    return max;",
            "}",
            "",
            "static inline __attribute__((always_inline)) uint32_t voice_highest_velocity(void) {",
            "    uint32_t v, max = 0u;",
            "    for (v = 0; v < NVOICE; v++)",
            "        if (voice_gate[v] && voice_velocity[v] > max) max = voice_velocity[v];",
            "    return max;",
            "}",
            "",
        ]
    return [
        "static inline __attribute__((always_inline)) uint32_t voice_mono_active(",
        "        int32_t priority) {",
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
        "static inline __attribute__((always_inline)) uint32_t voice_highest_note(void) {",
        "    uint32_t v, max = 0u;",
        "    for (v = 0; v < NVOICE; v++)",
        "        if (voice_gate[v] && voice_note[v] > max) max = voice_note[v];",
        "    return max;",
        "}",
        "",
        "static inline __attribute__((always_inline)) uint32_t voice_highest_velocity(void) {",
        "    uint32_t v, max = 0u;",
        "    for (v = 0; v < NVOICE; v++)",
        "        if (voice_gate[v] && voice_velocity[v] > max) max = voice_velocity[v];",
        "    return max;",
        "}",
        "",
    ]


def note_on(name: str, n_parts: int) -> list[str]:
    """The `<name>_dsp_note_on_ch` implementation (mode-aware single-timbre, or
    per-part mode/channel/keyzone routing for parts) + the frozen forwarder."""
    impl = _note_on_ch_parts(name) if n_parts > 1 else _note_on_ch_single(name)
    return impl + [
        f"UMETATE_DSP_API void {name}_dsp_note_on(uint32_t note, uint32_t velocity) {{",
        f"    {name}_dsp_note_on_ch(note, velocity, 0xFFFFFFFFu); /* omni */",
        "}",
        "",
    ]


def _note_on_ch_single(name: str) -> list[str]:
    """The mode-aware allocation (mono/unison/poly), as `<name>_dsp_note_on_ch`."""
    return [
        f"UMETATE_DSP_API void {name}_dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel) {{",
        "    (void)channel;",
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
        "        voice_rel[pick] = 0;",
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


def _note_on_ch_parts(name: str) -> list[str]:
    """The multitimbral routing: a note fires every matching part (channel +
    keyzone), each allocating per its own voice mode — poly (one voice), unison
    (count voices, detuned), or mono (the part's single voice, legato/priority)."""
    return [
        f"UMETATE_DSP_API void {name}_dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel) {{",
        "    if (note > 127u || !velocity) return;",
        "    uint8_t picked[NVOICE];",
        "    uint8_t chosen[NVOICE];",
        "    uint32_t npicked = 0;",
        "    for (uint32_t v = 0; v < NVOICE; v++) chosen[v] = 0;",
        "    for (uint32_t p = 0; p < N_PART; p++) {",
        "        if (part_channel[p] != -1 && channel != 0xFFFFFFFFu &&",
        "            part_channel[p] != (int32_t)channel) continue;",
        "        if (note < (uint32_t)part_low[p] || note > (uint32_t)part_high[p]) continue;",
        "        uint32_t m = (uint32_t)vm_mode[p];",
        "        if (m == 1u) {",
        "            /* mono: the part's single voice, with legato/priority/portamento */",
        "            mono_held[p][note]++;",
        "            mono_order[p][note] = ++mono_serial[p];",
        "            uint32_t mv = part_mono_voice[p];",
        "            if (mv == 0xFFu) {",
        "                uint32_t best = 0xFFFFFFFFu;",
        "                for (uint32_t v = 0; v < NVOICE; v++) {",
        "                    if (chosen[v]) continue;",
        "                    uint32_t score = voice_gate[v] ? 0x80000000u + voice_age[v]",
        "                                     : voice_age[v] + 1u;",
        "                    if (score < best) { best = score; mv = v; }",
        "                }",
        "                part_mono_voice[p] = (uint8_t)mv;",
        "            }",
        "            chosen[mv] = 1;",
        "            uint32_t active = voice_mono_active(p, vm_note_priority[p]);",
        "            uint8_t was = voice_gate[mv];",
        "            voice_part[mv] = (uint8_t)p;",
        "            voice_detune[mv] = 65536;",
        "            voice_delay[mv] = (uint32_t)(part_delay[p] > 0 ? part_delay[p] * 44 : 0);",
        "            voice_note[mv] = (uint8_t)active;",
        "            voice_age[mv] = ++ages;",
        "            voice_velocity[mv] = (int32_t)(velocity * 258u);",
        "            voice_gate[mv] = 1;",
        "            voice_rel[mv] = 0;",
        "            voice_trig[mv] = (uint8_t)((vm_legato[p] && was) ? 0u : 1u);",
        "            voice_target_inc[mv] = (uint32_t)(((uint64_t)note_to_inc(active) * ",
        "(uint32_t)voice_detune[mv]) >> 16);",
        "            if (!vm_portamento[p] || !was) voice_inc[mv] = voice_target_inc[mv];",
        f"            {name}_note_derived(mv);",
        "            continue;",
        "        }",
        "        uint32_t count = 1u;",
        "        int32_t span = 0;",
        "        if (m == 2u) {",
        "            count = (uint32_t)vm_unison_count[p];",
        "            if (count < 1u) count = 1u;",
        "            if (count > NVOICE) count = NVOICE;",
        "            span = vm_unison_detune[p];",
        "        }",
        "        for (uint32_t k = 0; k < count; k++) {",
        "            uint32_t best = 0xFFFFFFFFu, bp = 0;",
        "            for (uint32_t v = 0; v < NVOICE; v++) {",
        "                if (chosen[v]) continue;",
        "                uint32_t score = (voice_gate[v] || voice_delay[v] > 0u)",
        "                                 ? 0x80000000u + voice_age[v] : voice_age[v] + 1u;",
        "                if (score < best) { best = score; bp = v; }",
        "            }",
        "            chosen[bp] = 1;",
        "            voice_part[bp] = (uint8_t)p;",
        "            if (count <= 1u) {",
        "                voice_detune[bp] = 65536;",
        "            } else {",
        "                int32_t step = span / (int32_t)(count - 1u);",
        "                int32_t cents = -span / 2 + (int32_t)k * step;",
        "                voice_detune[bp] = 65536 + cents * 38;",
        "            }",
        "            voice_delay[bp] = (uint32_t)(part_delay[p] > 0 ? part_delay[p] * 44 : 0);",
        "            picked[npicked++] = bp;",
        "        }",
        "    }",
        "    uint8_t trig = 1;",
        "    uint32_t snote = note;",
        "    for (uint32_t k = 0; k < npicked; k++) {",
        "        uint32_t pick = picked[k];",
        "        uint32_t p = (uint32_t)voice_part[pick];",
        "        uint8_t was = voice_gate[pick];",
        "        voice_note[pick] = (uint8_t)snote;",
        "        voice_age[pick] = ++ages;",
        "        voice_velocity[pick] = (int32_t)(velocity * 258u);",
        "        voice_rel[pick] = 0;",
        "        if (voice_delay[pick] > 0u) {",
        "            voice_gate[pick] = 0; /* pending: the envelope attacks at expiry */",
        "        } else {",
        "            voice_gate[pick] = 1;",
        "            voice_trig[pick] = trig;",
        "            voice_target_inc[pick] = (uint32_t)(((uint64_t)note_to_inc(snote) * ",
        "(uint32_t)voice_detune[pick]) >> 16);",
        "            if (!vm_portamento[p] || !was) voice_inc[pick] = voice_target_inc[pick];",
        f"            {name}_note_derived(pick);",
        "        }",
        "    }",
        "}",
        "",
    ]


def note_off(name: str, n_parts: int) -> list[str]:
    """The `<name>_dsp_note_off` body: mode-aware (mono takeover) single-timbre, or
    per-part mode-aware release for parts."""
    if n_parts > 1:
        return [
            f"UMETATE_DSP_API void {name}_dsp_note_off(uint32_t note) {{",
            "    if (note > 127u) return;",
            "    for (uint32_t p = 0; p < N_PART; p++) {",
            "        if ((uint32_t)vm_mode[p] == 1u) {",
            "            uint32_t mv = part_mono_voice[p];",
            "            if (mono_held[p][note]) mono_held[p][note]--;",
            "            uint32_t active = voice_mono_active(p, vm_note_priority[p]);",
            "            if (mv == 0xFFu) continue;",
            f"            if (active == 0xFFu) {{ voice_gate[mv] = 0; voice_rel[mv] = {RELEASE_BLOCKS}u; continue; }}",
            "            if (active != (uint32_t)voice_note[mv]) {",
            "                voice_note[mv] = (uint8_t)active;",
            "                if (!vm_legato[p]) voice_trig[mv] = 1;",
            "                voice_target_inc[mv] = (uint32_t)(((uint64_t)note_to_inc(active) * ",
            "(uint32_t)voice_detune[mv]) >> 16);",
            "                if (!vm_portamento[p]) voice_inc[mv] = voice_target_inc[mv];",
            f"                {name}_note_derived(mv);",
            "            }",
            "        }",
            "    }",
            "    for (uint32_t v = 0; v < NVOICE; v++)",
            f"        if (voice_note[v] == note) {{ voice_gate[v] = 0; voice_rel[v] = {RELEASE_BLOCKS}u; voice_delay[v] = 0; }}",
            "}",
            "",
        ]
    return [
        f"UMETATE_DSP_API void {name}_dsp_note_off(uint32_t note) {{",
        "    if (note > 127u) return;",
        "    if (vm_mode == 1) {",
        "        if (mono_held[note]) mono_held[note]--;",
        "        uint32_t active = voice_mono_active(vm_note_priority);",
        f"        if (active == 0xFFu) {{ voice_gate[0] = 0; voice_rel[0] = {RELEASE_BLOCKS}u; return; }}",
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
        f"        if (voice_note[v] == note) {{ voice_gate[v] = 0; voice_rel[v] = {RELEASE_BLOCKS}u; }}",
        "}",
        "",
    ]


def glide(name: str, per_part: bool) -> list[str]:
    """The per-block portamento ramp (indented for the render loop): move each
    gated voice's `voice_inc[v]` toward `voice_target_inc[v]` at a constant rate
    (linear in the increment, one add per voice per block), re-deriving the
    note→increment glue when the increment moves. `vm_portamento` is the one-octave
    glide time in ms (0 = off), converted here to the increment step
    `step = tgt·23777/ms >> 16` (23777 = 32768·32·1000/44100)."""
    rate = mode_ref("vm_portamento", per_part, "voice_part[v]")
    return [
        "        for (uint32_t v = 0; v < NVOICE; v++) {",
        "            if (!voice_gate[v]) continue;",
        f"            if (!{rate}) continue;",
        "            uint32_t cur = voice_inc[v];",
        "            uint32_t tgt = voice_target_inc[v];",
        "            if (cur != tgt) {",
        "                uint32_t step = (uint32_t)(((uint64_t)tgt * 23777u /",
        f"                    (uint32_t){rate}) >> 16);",
        "                if (step < 1u) step = 1u;",
        "                if (tgt > cur) {",
        "                    cur += step; if (cur > tgt) cur = tgt;",
        "                } else {",
        "                    cur -= step; if (cur < tgt) cur = tgt;",
        "                }",
        "                voice_inc[v] = cur;",
        f"                {name}_note_derived(v);",
        "            }",
        "        }",
    ]


def delay_countdown(name: str) -> list[str]:
    """The per-block onset-offset countdown (indented for the render loop): a
    pending voice fires (gate + trigger + increment) when its delay expires."""
    return [
        "        for (uint32_t v = 0; v < NVOICE; v++) {",
        "            if (voice_delay[v] == 0u) continue;",
        "            if (voice_delay[v] > CONTROL_BLOCK) {",
        "                voice_delay[v] -= CONTROL_BLOCK;",
        "                continue;",
        "            }",
        "            voice_delay[v] = 0u;",
        "            voice_gate[v] = 1;",
        "            voice_trig[v] = 1;",
        "            voice_target_inc[v] = (uint32_t)(((uint64_t)note_to_inc(voice_note[v]) * ",
        "(uint32_t)voice_detune[v]) >> 16);",
        "            voice_inc[v] = voice_target_inc[v];",
        f"            {name}_note_derived(v);",
        "        }",
    ]


def all_off(per_part: bool) -> list[str]:
    """The all-notes-off (panic) body: hard-cut every voice + the mono tracker."""
    lines = [
        "    for (uint32_t v = 0; v < NVOICE; v++) { voice_gate[v] = 0; voice_rel[v] = 0; }",
        "    for (uint32_t v = 0; v < NVOICE; v++) voice_delay[v] = 0;",
    ]
    if per_part:
        lines += [
            "    for (uint32_t p = 0; p < N_PART; p++)",
            "        for (uint32_t n = 0; n < 128u; n++) mono_held[p][n] = 0;",
        ]
    else:
        lines.append("    for (uint32_t n = 0; n < 128u; n++) mono_held[n] = 0;")
    return lines


def reset(per_part: bool) -> list[str]:
    """The reset body: all-off + age/serial zero."""
    lines = [
        "    for (uint32_t v = 0; v < NVOICE; v++) { voice_gate[v] = 0; voice_rel[v] = 0; }",
        "    for (uint32_t v = 0; v < NVOICE; v++) voice_delay[v] = 0;",
    ]
    if per_part:
        lines += [
            "    for (uint32_t p = 0; p < N_PART; p++)",
            "        for (uint32_t n = 0; n < 128u; n++) mono_held[p][n] = 0;",
            "    for (uint32_t p = 0; p < N_PART; p++) mono_serial[p] = 0;",
            "    for (uint32_t p = 0; p < N_PART; p++) part_mono_voice[p] = 0xFFu;",
        ]
    else:
        lines.append("    for (uint32_t n = 0; n < 128u; n++) mono_held[n] = 0;")
        lines.append("    mono_serial = 0;")
    lines.append("    ages = 0;")
    return lines
