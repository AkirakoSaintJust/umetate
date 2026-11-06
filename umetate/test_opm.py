# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host test: the OPM text parser and the OPM -> Type P.fm1 conversion."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import cast

from ._opm import (
    OpmError,
    OpmVoice,
    _attack_rate,  # pyright: ignore[reportPrivateUsage]
    _decay_rate,  # pyright: ignore[reportPrivateUsage]
    _release_rate,  # pyright: ignore[reportPrivateUsage]
    convert_bank,
    convert_voice,
    parse_opm,
)
from ._presets import as_bank, export_bank, import_bank
from ._records import PartPatch
from ._schema import as_patch
from .generate import generate_sysex_layout

_ROOT = Path(__file__).resolve().parents[1]

_TEST_BANK = """\
//MiOPMdrv sound bank Paramer Ver2002.04.22
//LFO: LFRQ AMD PMD WF NFRQ
//@:[Num] [Name]
//CH: PAN FL CON AMS PMS SLOT NE
//[OPname]: AR D1R D2R RR D1L TL KS MUL DT1 DT2 AMS-EN

@:0 Test Bass
LFO: 32 10 20 1 0
CH: 192 5 3 2 4 120 0
M1: 31 10 4 8 8 20 1 2 3 1 0
C1: 30 8 3 8 6 10 0 1 0 0 1
M2: 29 6 2 8 4 0 0 3 0 2 0
C2: 31 4 2 8 0 0 0 1 0 0 0

@:1 Simple
LFO: 0 0 0 0 0
CH: 64 0 0 0 0 120 0
M1: 31 0 0 15 0 127 0 1 0 0 0
C1: 31 0 0 15 0 127 0 1 0 0 0
M2: 31 0 0 15 0 127 0 1 0 0 0
C2: 31 0 0 15 0 0 0 1 0 0 0
"""


def _defaults() -> tuple[list[str], list[int]]:
    manifest = _ROOT / "firmware/gen/params.json"
    params = json.loads(manifest.read_text(encoding="utf-8"))["params"]
    part = [p for p in params if str(p["name"]).endswith(".p0")]
    names = [str(p["name"]) for p in part]
    values = [int(p["default"]) for p in part]
    init = json.loads(
        (_ROOT / "examples/type-p-fm1/patch.json").read_text(encoding="utf-8")
    )["init"]
    for i, name in enumerate(names):
        key = name[:-3]
        if key in init:
            values[i] = int(init[key])
        elif key == "attack" and "op1.eg.r1" in init:
            values[i] = int(init["op1.eg.r1"])
        elif key == "release" and "op1.eg.r4" in init:
            values[i] = int(init["op1.eg.r4"])
    return names, values


def _parsed() -> list[OpmVoice]:
    return parse_opm(_TEST_BANK)


def _parser() -> None:
    voices = _parsed()
    assert len(voices) == 2
    first = voices[0]
    assert first.slot == 0 and first.name == "Test Bass"
    assert (first.lfrq, first.amd, first.pmd, first.wf, first.nfrq) == (
        32,
        10,
        20,
        1,
        0,
    )
    assert (
        first.pan,
        first.fl,
        first.con,
        first.ams,
        first.pms,
        first.slot_mask,
        first.ne,
    ) == (192, 5, 3, 2, 4, 120, 0)
    assert first.ops[0].ar == 31 and first.ops[0].tl == 20
    assert first.ops[1].ame == 1
    assert first.ops[2].dt2 == 2
    print("ok: parser reads the header, LFO, CH, and the four operator lines")


def _parser_errors() -> None:
    try:
        parse_opm("@:0 broken\nLFO: 0 0 0 0 0\nCH: 64 0 0 0 0 120 0\n")
    except OpmError:
        pass
    else:
        raise AssertionError("a voice with no operators parsed")
    try:
        parse_opm(
            "@:0 broken\nLFO: 0 0 0 0 99\nCH: 64 0 0 0 0 120 0\n"
            "M1: 0 0 0 0 0 0 0 0 0 0 0\nC1: 0 0 0 0 0 0 0 0 0 0 0\n"
            "M2: 0 0 0 0 0 0 0 0 0 0 0\nC2: 0 0 0 0 0 0 0 0 0 0 0\n"
        )
    except OpmError:
        pass
    else:
        raise AssertionError("an out-of-range LFO value parsed")
    print("ok: malformed ranges and missing operators are rejected")


def _convert_con3() -> None:
    names, defaults = _defaults()
    voices = _parsed()
    patch, warnings = convert_voice(voices[0], names=names, defaults=defaults)
    value = dict(zip(names, patch["params"], strict=True))
    assert value["algorithm.p0"] == 2, "CON 3 must remap to algorithm 2"
    # O1 = M2 (TL 0, MUL 3), O2 = M1 (TL 20, MUL 2 with DT2 sqrt2),
    # O3 = C1 (TL 10, MUL 1), O4 = C2 (TL 0, MUL 1).
    assert value["op1_level.p0"] == 99
    assert value["op2_level.p0"] == 79
    assert value["op3_level.p0"] == 89
    assert value["op4_level.p0"] == 99
    assert value["op1_ratio.p0"] == round(3 * (math.pi / 2) * 65536)
    assert value["op2_ratio.p0"] == round(2 * math.sqrt(2) * 65536)
    assert value["op1_feedback.p0"] == 0
    assert value["op2_feedback.p0"] == 8192, "CON 3 puts the M1 feedback on O2"
    assert value["op1.eg.l2.p0"] == 99 - 4 * 4
    assert value["op2.eg.l2.p0"] == 99 - 4 * 8
    assert value["op3.eg.l2.p0"] == 99 - 4 * 6
    assert value["op4.eg.l2.p0"] == 99
    assert value["op1.eg.l3.p0"] == 0
    assert value["op2.eg.l3.p0"] == 0
    assert value["op1_mute.p0"] == 0 and value["op4_mute.p0"] == 0
    assert value["pitch_wave.p0"] == 10, "an OPM square LFO maps to the square wave"
    assert value["pitch_depth.p0"] > 0
    assert warnings == ()
    print("ok: CON 3 remaps the graph, levels, ratio, feedback, and levels")


def _convert_con0() -> None:
    names, defaults = _defaults()
    voices = _parsed()
    patch, _warnings = convert_voice(voices[1], names=names, defaults=defaults)
    value = dict(zip(names, patch["params"], strict=True))
    assert value["algorithm.p0"] == 0
    assert value["op1_level.p0"] == 0, "TL 127 is silent"
    assert value["op2_level.p0"] == 0
    assert value["op3_level.p0"] == 0
    assert value["op4_level.p0"] == 99
    assert value["op1_feedback.p0"] == 0
    print("ok: CON 0 keeps the file order and puts the feedback on O1")


def _bank() -> None:
    names, defaults = _defaults()
    voices = _parsed()
    patch = as_patch(
        json.loads(
            (_ROOT / "examples/type-p-fm1/patch.json").read_text(encoding="utf-8")
        )
    )
    layout = generate_sysex_layout(patch)
    bank, report = convert_bank(
        voices, names=names, defaults=defaults, record_count=int(layout["n_params"])
    )
    assert len(report) == 2
    parts = cast(list[PartPatch | None], bank["part_patches"])
    assert len(parts) == 128
    first = parts[0]
    assert first is not None
    assert len(first["params"]) == int(layout["n_params"])
    stream = export_bank(layout, as_bank(bank), int(layout["model"]))
    again = import_bank(stream, layout, int(layout["model"]))
    assert again is not None
    assert again["part_patches"][0] == first
    _packed, packed_report = convert_bank(
        voices,
        names=names,
        defaults=defaults,
        start=4,
        record_count=int(layout["n_params"]),
        pack=True,
    )
    assert [slot for slot, _name, _warnings in packed_report] == [4, 5]
    print(
        "ok: the bank is 128 slots, the record uses the layout n_params, "
        "the SysEx round-trips, and --pack fills from the start slot"
    )


def _timing() -> None:
    # Fast attacks hit the top rate, and a slow attack is mapped to a slow rate.
    assert _attack_rate(31, 0) == 99
    assert _attack_rate(23, 0) == 91
    assert _attack_rate(9, 0) == 35
    assert _attack_rate(1, 0) == 0
    # The first decay gets slower as the rate falls and as D1L asks for a
    # shorter trip; the second decay tracks D2R.
    assert _decay_rate(8, 10, 0, "decay1") == 46
    assert _decay_rate(8, 4, 0, "decay1") == 8
    assert _decay_rate(8, 20, 0, "decay1") == 87
    # RR 8 is the common pluck release.
    assert _release_rate(8, 0) == 76
    assert _release_rate(4, 0) == 38
    print("ok: the measured envelope map has the expected rates")


def main() -> int:
    failures = 0
    checks = (
        _parser,
        _parser_errors,
        _convert_con3,
        _convert_con0,
        _bank,
        _timing,
    )
    for check in checks:
        try:
            check()
        except (AssertionError, OpmError) as exc:
            print(f"FAIL: {check.__name__}: {exc}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
