# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Convert an OPM text patch bank to Type P.fm1 part patches.

The mapping is the one measured in `docs/opm-to-type-p-fm1.md`: the same
four-operator graph, the Yamaha 0.75 dB total-level curve, the OPM index
calibration, the feedback depth law, and an envelope-rate map derived from the
two engines' stage times rather than guessed. The result is a bank whose voices
are recognisably the same kind of sound, not a bit-exact copy.

This module is pure Python and does no I/O beyond the bank helpers in
`umetate._presets`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from ._records import PartPatch

# --- YM2151 envelope rate table -------------------------------------------------


# `XRTBL` from the YM2151 envelope: the gate mask and the fractional step for
# each key-scaled rate index. It is chip data, not VOPMex code.
def _make_xrtbl() -> list[tuple[int, int]]:
    table: list[tuple[int, int]] = [(4095, 8)]
    mask = 2047
    for _ in range(11):
        for add in (5, 6, 7, 8):
            table.append((mask, add))
        mask >>= 1
    table += [
        (0, 5),
        (0, 6),
        (0, 7),
        (0, 8),
        (0, 10),
        (0, 12),
        (0, 14),
        (0, 16),
        (0, 20),
        (0, 24),
        (0, 28),
        (0, 32),
        (0, 40),
        (0, 48),
        (0, 56),
        (0, 64),
    ] + [(0, 64)] * 35
    return table


_XRTBL = _make_xrtbl()

# `D1LTBL`: the first-decay limit in 1/16 envelope steps. 3 dB per step up to 14,
# and the special full-attenuation step at 15.
_D1LTBL: list[int] = [i * 2 for i in range(15)] + [62]

# OPM EG clock: OpmRate = 3 579 545 >> 5 = 111 860. VOPMex's `EnvCounter2`
# starts at 3 and wraps on the third inner tick (`--EnvCounter2 == 0`), and the
# inner loop runs OpmRate / 2 times a second. So the EG advances OpmRate / 6
# times a second, 18 643 Hz.
_OPM_EG_HZ = (3579545 >> 5) / 6.0
_DB_PER_EL = 20.0 * math.log10(2.0) / 64.0  # one `Xr_el` unit

# Type P.fm1 control rate: CONTROL_BLOCK samples at 44.1 kHz.
_FM1_RATE_HZ = 44100.0 / 32.0

# Generated engine tables, recomputed here from the same formulas so the
# converter does not depend on a build tree.
_RATE_COEFF = [
    min(65536, max(0, round(65536.0 * 2.0 ** (-((99 - r) ** 0.5) / 0.75))))
    for r in range(100)
]
_LEVEL_GAIN = [0] + [
    max(1, min(32767, round(32767.0 * 10.0 ** (-(99 - level) * 0.75 / 20.0))))
    for level in range(1, 100)
]


class OpmError(ValueError):
    """A malformed or unsupported OPM text patch bank."""


@dataclass(frozen=True)
class OpmOperator:
    """One OPM operator line (`M1`, `C1`, `M2`, or `C2`)."""

    ar: int
    d1r: int
    d2r: int
    rr: int
    d1l: int
    tl: int
    ks: int
    mul: int
    dt1: int
    dt2: int
    ame: int


@dataclass(frozen=True)
class OpmVoice:
    """One `@:` voice block from a text patch bank."""

    slot: int
    name: str
    lfrq: int
    amd: int
    pmd: int
    wf: int
    nfrq: int
    pan: int
    fl: int
    con: int
    ams: int
    pms: int
    slot_mask: int
    ne: int
    ops: tuple[OpmOperator, OpmOperator, OpmOperator, OpmOperator]

    def op(self, name: str) -> OpmOperator:
        """The operator in file order (M1, C1, M2, C2)."""
        mapping = {
            "M1": self.ops[0],
            "C1": self.ops[1],
            "M2": self.ops[2],
            "C2": self.ops[3],
        }
        return mapping[name]


_OP_ORDER = ("M1", "C1", "M2", "C2")


def _comment_strip(line: str) -> str:
    cut = line.find("//")
    return line if cut < 0 else line[:cut]


def _ints(text: str, count: int, where: str) -> list[int]:
    parts = text.split()
    if len(parts) < count:
        raise OpmError(f"{where}: expected {count} values, got {len(parts)}")
    out: list[int] = []
    for token in parts[:count]:
        try:
            out.append(int(token, 10))
        except ValueError as exc:
            raise OpmError(f"{where}: {token!r} is not an integer") from exc
    return out


def _ranged(value: int, low: int, high: int, where: str) -> int:
    if not low <= value <= high:
        raise OpmError(f"{where}: {value} is outside {low}..{high}")
    return value


def parse_opm(text: str) -> list[OpmVoice]:
    """Parse a VOPM/VOPMex text patch bank into voices, in file order.

    The parser is deliberately strict about value ranges, because a bad range
    silently produces a wrong patch. Unknown lines are ignored, which keeps the
    conventional comment header and vendor extensions harmless.
    """
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    voices: list[OpmVoice] = []
    current: dict[str, object] | None = None

    def start_voice(slot: int, name: str) -> dict[str, object]:
        return {
            "slot": slot,
            "name": name,
            "lfo": (0, 0, 0, 0, 0),
            "ch": (192, 0, 0, 0, 0, 120, 0),
            "ops": {},
        }

    for line_number, raw in enumerate(text.split("\n"), start=1):
        line = _comment_strip(raw).strip()
        if not line:
            continue
        if ":" not in line:
            raise OpmError(f"line {line_number}: expected `key: values`")
        key, body = line.split(":", 1)
        key = key.strip().upper()
        where = f"line {line_number} ({key})"
        if key == "@":
            taken = body.split(None, 1)
            if not taken:
                raise OpmError(f"{where}: expected a slot number")
            try:
                slot = int(taken[0], 10)
            except ValueError as exc:
                raise OpmError(f"{where}: bad slot {taken[0]!r}") from exc
            name = taken[1].strip() if len(taken) > 1 else ""
            if current is not None:
                voices.append(_finish(current, line_number))
            current = start_voice(_ranged(slot, 0, 999, where), name)
            continue
        if current is None:
            # The header uses `//LFO:` and other comment lines, which the strip
            # already removed. A stray parameter before the first `@:` is a
            # malformed bank, but skipping it is friendlier than failing the lot.
            continue
        if key == "LFO":
            values = _ints(body, 5, where)
            current["lfo"] = (
                _ranged(values[0], 0, 255, where),
                _ranged(values[1], 0, 127, where),
                _ranged(values[2], 0, 127, where),
                _ranged(values[3], 0, 3, where),
                _ranged(values[4], 0, 31, where),
            )
        elif key == "CH":
            values = _ints(body, 7, where)
            current["ch"] = (
                _ranged(values[0], 0, 255, where),
                _ranged(values[1], 0, 7, where),
                _ranged(values[2], 0, 7, where),
                _ranged(values[3], 0, 3, where),
                _ranged(values[4], 0, 7, where),
                _ranged(values[5], 0, 255, where),
                _ranged(values[6], 0, 1, where),
            )
        elif key in _OP_ORDER:
            values = _ints(body, 11, where)
            ops = current["ops"]
            assert isinstance(ops, dict)
            ops[key] = OpmOperator(
                ar=_ranged(values[0], 0, 31, where),
                d1r=_ranged(values[1], 0, 31, where),
                d2r=_ranged(values[2], 0, 31, where),
                rr=_ranged(values[3], 0, 15, where),
                d1l=_ranged(values[4], 0, 15, where),
                tl=_ranged(values[5], 0, 127, where),
                ks=_ranged(values[6], 0, 3, where),
                mul=_ranged(values[7], 0, 15, where),
                dt1=_ranged(values[8], 0, 7, where),
                dt2=_ranged(values[9], 0, 3, where),
                ame=1 if values[10] else 0,
            )
        # Other keys are vendor extensions, ignore them.
    if current is not None:
        voices.append(_finish(current, 0))
    return voices


def _finish(current: dict[str, object], line_number: int) -> OpmVoice:
    ops = current["ops"]
    assert isinstance(ops, dict)
    missing = [name for name in _OP_ORDER if name not in ops]
    if missing:
        raise OpmError(
            f"voice {current['slot']!r} (line {line_number}): "
            f"missing {', '.join(missing)}"
        )
    lfo = current["lfo"]
    ch = current["ch"]
    assert isinstance(lfo, tuple) and isinstance(ch, tuple)
    lfo_values = cast(tuple[int, int, int, int, int], lfo)
    ch_values = cast(tuple[int, int, int, int, int, int, int], ch)
    op_values = cast(dict[str, OpmOperator], ops)
    op_list = [op_values[name] for name in _OP_ORDER]
    slot_value = current["slot"]
    assert isinstance(slot_value, int)
    return OpmVoice(
        slot=slot_value,
        name=str(current["name"]),
        lfrq=lfo_values[0],
        amd=lfo_values[1],
        pmd=lfo_values[2],
        wf=lfo_values[3],
        nfrq=lfo_values[4],
        pan=ch_values[0],
        fl=ch_values[1],
        con=ch_values[2],
        ams=ch_values[3],
        pms=ch_values[4],
        slot_mask=ch_values[5],
        ne=ch_values[6],
        ops=(op_list[0], op_list[1], op_list[2], op_list[3]),
    )


# --- OPM envelope timing --------------------------------------------------------


def _midi_key_code(midi: int) -> int:
    """The OPM key code the renderer feeds to `SetKC`, plus the `++Kc`."""
    table = (0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14)
    n = midi - 1
    return ((table[n % 12] + (n // 12) * 16 - 16) & 127) + 1


def _opm_ticks(
    rate: int,
    kind: str,
    *,
    d1l: int,
    ks: int,
    midi: int,
    start_el: int = 0,
) -> list[int]:
    """One OPM envelope stage, sampled at every EG tick, with the real XRTBL."""
    kc_shift = 5 - ks
    key = _midi_key_code(midi) >> kc_shift
    if kind == "attack":
        if rate == 0:
            return [start_el] * 2
        index = (rate << 1) + key
        mask, add = _XRTBL[index]
        if index >= 62:
            add = 128
        limit = 0
    elif kind == "release":
        index = (rate << 2) + 2 + key
        mask, add = _XRTBL[index]
        limit = 63
    else:
        index = (rate << 1) + key
        mask, add = _XRTBL[index]
        limit = _D1LTBL[d1l] if kind == "decay1" else 63
    cmp = mask >> 1
    el = start_el
    step = 0
    ticks: list[int] = []
    counter = 1
    # The slowest stage (rate 0, maximum key scaling) is about 2.4 minutes, a
    # hard cap keeps a malformed table from looping forever.
    for _ in range(4_000_000):
        if (counter & mask) == cmp:
            if kind == "attack":
                step += add
                el += ((~el) * (step >> 3)) >> 4
                step &= 7
                ticks.append(el if el > 0 else 0)
                if el <= 0:
                    return ticks
            else:
                step += add
                el += step >> 3
                step &= 7
                e = el >> 4
                if e >= 63:
                    ticks.append(1024)
                    return ticks
                ticks.append(el)
                if e == limit:
                    return ticks
        else:
            ticks.append(el)
        counter += 1
    return ticks


def _opm_time_to(ticks: Sequence[int], *, start_el: int, target_el: int) -> float:
    """The time to reach `target_el` in a stage, or the stage end."""
    direction = 1 if target_el > start_el else -1
    for index, el in enumerate(ticks):
        if (direction > 0 and el >= target_el) or (direction < 0 and el <= target_el):
            return index / _OPM_EG_HZ
    return (len(ticks) - 1) / _OPM_EG_HZ if ticks else 0.0


def _fm1_time(rate: int, start_level: int, end_level: int, aim: int | None) -> float:
    """The time for one Type P.fm1 stage, with the engine's one-unit floor.

    `aim` is a gain value to reach on the way to `end_level`; None means the
    whole stage, which ends within 8 units of the target (where the engine
    snaps). The aim is clamped to the target so a request past the end is the
    full stage.
    """
    coeff = _RATE_COEFF[rate]
    gain = _LEVEL_GAIN[start_level]
    target = _LEVEL_GAIN[end_level]
    start_gain = gain
    if aim is not None and (
        (target > start_gain and aim > target) or (target < start_gain and aim < target)
    ):
        aim = None
    for tick in range(1, 200_000):
        d = target - gain
        u = (d * coeff + (1 << 15)) >> 16
        if u == 0:
            if d > 0:
                u = 1
            elif d < 0:
                u = -1
            else:
                return tick / _FM1_RATE_HZ
        gain += u
        if gain < 0:
            gain = 0
        elif gain > 32767:
            gain = 32767
        if aim is None:
            if abs(gain - target) <= 8:
                return tick / _FM1_RATE_HZ
        elif (aim >= start_gain and gain >= aim) or (aim < start_gain and gain <= aim):
            return tick / _FM1_RATE_HZ
    return 200_000 / _FM1_RATE_HZ


def _nearest_rate(opm_time: float, candidates: Sequence[tuple[int, float]]) -> int:
    if opm_time <= 0:
        return 99
    best_rate = 99
    best = float("inf")
    for rate, time in candidates:
        if time <= 0:
            continue
        score = abs(math.log(time / opm_time))
        if score < best:
            best = score
            best_rate = rate
    return best_rate


# How far into a decay the rate map aims. A larger drop shortens the one-pole
# tail at the cost of a faster first few dB. Eight matches the early body, the
# converter defaults to a little more so the stage does not read long.
_DECAY_DROP_DB = 12.0
# No extra rate offset. With the corrected OPM EG clock, the 12 dB target is
# enough to keep the early body and the tail in the same region.
_DECAY_BIAS = 0

_ATTACK_CACHE: dict[tuple[int, int, int], int] = {}
_DECAY_CACHE: dict[tuple[int, int, int, str, int], int] = {}
_RELEASE_CACHE: dict[tuple[int, int, int], int] = {}


def _attack_rate(ar: int, ks: int, midi: int = 60) -> int:
    """The Type P.fm1 rate whose rise to -12 dB takes the OPM's time."""
    key = (ar, ks, midi)
    cached = _ATTACK_CACHE.get(key)
    if cached is not None:
        return cached
    if ar == 0:
        result = 0
    else:
        ticks = _opm_ticks(ar, "attack", d1l=0, ks=ks, midi=midi, start_el=1024)
        # -12 dB below full is Xr_el 128.
        opm_time = _opm_time_to(ticks, start_el=1024, target_el=128)
        aim = round(32767.0 * 10.0 ** (-12.0 / 20.0))
        candidates = [(rate, _fm1_time(rate, 0, 99, aim)) for rate in range(100)]
        result = _nearest_rate(opm_time, candidates)
    _ATTACK_CACHE[key] = result
    return result


def _decay_rate(d1l: int, rate: int, ks: int, kind: str, midi: int = 60) -> int:
    """The Type P.fm1 rate for a first or second OPM decay stage."""
    key = (d1l, rate, ks, kind, midi)
    cached = _DECAY_CACHE.get(key)
    if cached is not None:
        return cached
    if rate == 0:
        result = 0
    else:
        start_level = 99 if kind == "decay1" else _d1l_level(d1l)
        end_level = _d1l_level(d1l) if kind == "decay1" else 0
        span_db = (start_level - end_level) * 0.75
        start_el = 0 if kind == "decay1" else 16 * _D1LTBL[d1l]
        ticks = _opm_ticks(rate, kind, d1l=d1l, ks=ks, midi=midi, start_el=start_el)
        if span_db >= _DECAY_DROP_DB:
            # Aim a little past the first few dB so the one-pole tail does not
            # make the whole stage read long. A larger drop is a faster rate,
            # at the cost of a faster early slope.
            drop = _DECAY_DROP_DB
            opm_time = _opm_time_to(
                ticks,
                start_el=start_el,
                target_el=start_el + int(round(drop / _DB_PER_EL)),
            )
            aim = round(_LEVEL_GAIN[start_level] * 10.0 ** (-drop / 20.0))
        else:
            opm_time = (len(ticks) - 1) / _OPM_EG_HZ if ticks else 0.0
            aim = None
        candidates = [
            (r, _fm1_time(r, start_level, end_level, aim)) for r in range(100)
        ]
        result = min(99, _nearest_rate(opm_time, candidates) + _DECAY_BIAS)
    _DECAY_CACHE[key] = result
    return result


def _release_rate(rr: int, ks: int, midi: int = 60) -> int:
    """The Type P.fm1 rate whose audible release takes the OPM's time."""
    key = (rr, ks, midi)
    cached = _RELEASE_CACHE.get(key)
    if cached is not None:
        return cached
    ticks = _opm_ticks(rr, "release", d1l=0, ks=ks, midi=midi, start_el=0)
    # Match the audible part of the release. The OPM runs down in a straight
    # dB line, so its -20 dB point is a fifth of the stage. Type P.fm1's
    # one-pole has a long, quiet tail, matching the tail would make the note
    # seem to hang after the OPM has gone.
    opm_time = _opm_time_to(ticks, start_el=0, target_el=round(20.0 / _DB_PER_EL))
    aim = round(32767.0 * 10.0 ** (-20.0 / 20.0))
    candidates = [(r, _fm1_time(r, 99, 0, aim)) for r in range(100)]
    result = _nearest_rate(opm_time, candidates)
    _RELEASE_CACHE[key] = result
    return result


# --- OPM LFO and levels ---------------------------------------------------------


def lfo_hz(lfrq: int) -> float:
    """The YM2151 LFO frequency for `LFRQ` (0..255)."""
    high = lfrq >> 4
    low = lfrq & 15
    if high < 15:
        return 55928.0 * (16 + low) / (1 << (30 - high))
    return 1.7068 * (16 + low)


_PMS_MUL: tuple[int, ...] = (0, 1, 2, 4, 8, 16, 32, 32)
_PMS_SHL: tuple[int, ...] = (0, 0, 0, 0, 0, 0, 1, 2)
_WAVE_MAP: tuple[int, ...] = (11, 10, 1, 10)  # OPM saw/square/triangle/S&H


def _pitch_depth(pmd: int, pms: int, wf: int) -> int:
    if pmd == 0 or pms == 0:
        return 0
    peak = 128 if wf == 1 else 127
    # `PmValue` is in 1/64 semitone steps, so one unit is 100/64 cents.
    units = ((peak * pmd * _PMS_MUL[pms]) >> 12) << _PMS_SHL[pms]
    cents = units * (100.0 / 64.0)
    depth: int = round(32768.0 * (2.0 ** (cents / 1200.0) - 1.0))
    return max(0, min(3277, depth))


def _trem_depth(amd: int, ams: int, ame: int, wf: int) -> int:
    if amd == 0 or ams == 0 or not ame:
        return 0
    peak = 256 if wf == 1 else 255
    units = ((peak * amd) >> 7) << (ams - 1)
    attenuation = units * _DB_PER_EL
    fraction = 1.0 - 10.0 ** (-attenuation / 20.0)
    depth: int = round(32767.0 * fraction)
    return max(0, min(32767, depth))


def _dt1_cents(dt1: int) -> int:
    """The OPM fine-detune step in cents at middle C (DT1 bit 2 is the sign)."""
    if dt1 == 0 or dt1 == 4:
        return 0
    sign = -1 if dt1 & 4 else 1
    step = dt1 & 3
    # The four small values per key-code group, middle C is group 15.
    row = (0, 8, 16, 22)
    base = 1299 * 4  # STEPTBL_O2[0] << 2, the middle-C phase step
    cents = 1200.0 * math.log2(1.0 + sign * row[step] / base)
    return round(cents)


def _ratio_q16(op: OpmOperator) -> int:
    mul = 0.5 if op.mul == 0 else float(op.mul)
    dt2 = (1.0, math.sqrt(2.0), math.pi / 2.0, math.sqrt(3.0))[op.dt2]
    value = round(65536.0 * mul * dt2)
    return max(32768, min(1048576, value))


def _level(op: OpmOperator) -> int:
    return max(0, min(99, 99 - op.tl))


def _d1l_level(d1l: int) -> int:
    """The Type P.fm1 level for an OPM `D1L`.

    The first 15 steps are 3 dB each, so one step is four Type P.fm1 levels.
    `D1L` 15 is the special full-attenuation step, 93 dB, which is silence.
    """
    if d1l >= 15:
        return 0
    return max(0, 99 - 4 * d1l)


def _feedback(fl: int) -> int:
    return (0, 512, 1024, 2048, 4096, 8192, 16384, 32767)[fl]


# --- conversion -----------------------------------------------------------------


def _params_dict(names: Sequence[str], defaults: Sequence[int]) -> dict[str, int]:
    if len(names) != len(defaults):
        raise OpmError("parameter names and defaults differ in length")
    return dict(zip(names, defaults, strict=True))


def _key_follow(voice: OpmVoice, op: OpmOperator) -> tuple[int, int]:
    """Fit the OPM `KS` rate change to Type P.fm1's envelope key-follow.

    The comparison keys stay inside the playable keyboard (the panel is F3 to
    G5), because the OPM key code wraps at the top of its 7-bit register range
    and a full 0..127 fit would read that wrap as a change of direction.
    """
    ks = op.ks
    if ks == 0:
        return 0, 0
    stages = (
        ("attack", op.ar, 0),
        ("decay1", op.d1r, op.d1l),
        ("decay2", op.d2r, op.d1l),
        ("release", op.rr, 0),
    )
    low_values: list[float] = []
    high_values: list[float] = []
    for kind, rate, d1l in stages:
        if rate == 0:
            continue
        if kind == "attack":
            ref = _attack_rate(op.ar, ks, 60)
            low = _attack_rate(op.ar, ks, 36)
            high = _attack_rate(op.ar, ks, 84)
        elif kind == "release":
            ref = _release_rate(op.rr, ks, 60)
            low = _release_rate(op.rr, ks, 36)
            high = _release_rate(op.rr, ks, 84)
        else:
            ref = _decay_rate(d1l, rate, ks, kind, 60)
            low = _decay_rate(d1l, rate, ks, kind, 36)
            high = _decay_rate(d1l, rate, ks, kind, 84)
        if ref <= 0 or ref >= 99:
            continue

        def percent(target: int, ref_rate: int, low_side: bool) -> float:
            span = ref_rate if target < ref_rate else 99 - ref_rate
            if span <= 0:
                return 0.0
            # The key-follow factor is 0.40 of LO at note 36 and 0.358 of HI at
            # note 84 (the breakpoint is 60, the MIDI range is 0..127).
            share = 0.400 if low_side else 0.358
            return (target - ref_rate) / span * 100.0 / share

        low_values.append(percent(low, ref, True))
        high_values.append(percent(high, ref, False))
    if not low_values:
        return 0, 0

    def average(values: list[float]) -> int:
        if not values:
            return 0
        return max(-60, min(60, round(sum(values) / len(values))))

    return average(low_values), average(high_values)


def convert_voice(
    voice: OpmVoice,
    *,
    names: Sequence[str],
    defaults: Sequence[int],
) -> tuple[PartPatch, tuple[str, ...]]:
    """Convert one OPM voice to a Type P.fm1 part patch and a warning list.

    The operator order is the file order: `M1` is `op1`, `C1` is `op2`, `M2`
    is `op3`, `C2` is `op4`. That is also the chip's routing order, so the
    algorithm number carries over unchanged for all eight connections.
    """
    values = _params_dict(names, defaults)
    warnings: list[str] = []

    # OPM CON 3 is `M1 -> C1` and `C1 + M2 -> C2`. Type P.fm1 algorithm 3 is
    # `O1 -> O2` and `O1 -> O3` and `O2 + O3 -> O4`, which is a different graph,
    # so use algorithm 2 (`O1 + (O2 -> O3) -> O4`) with O1 = M2, O2 = M1,
    # O3 = C1, O4 = C2. The other seven connections carry over unchanged.
    file_ops = list(voice.ops)
    if voice.con == 3:
        ordered = [file_ops[2], file_ops[0], file_ops[1], file_ops[3]]
        source_index = [2, 0, 1, 3]
        algorithm = 2
        feedback_index = 2
    else:
        ordered = file_ops
        source_index = [0, 1, 2, 3]
        algorithm = voice.con
        feedback_index = 1
    keyed = [bool(voice.slot_mask & (0x08 << i)) for i in range(4)]

    values["algorithm.p0"] = algorithm
    values["level.p0"] = 99
    values["channel.p0"] = 0
    values["low.p0"] = 0
    values["high.p0"] = 127
    values["delay.p0"] = 0
    values["mode.p0"] = 0
    values["unison_count.p0"] = 1
    values["unison_detune.p0"] = 0
    values["detune.p0"] = 0
    values["legato.p0"] = 0
    values["portamento.p0"] = 0
    values["note_priority.p0"] = 0
    values["penv_on.p0"] = 0

    rate = _lfo_rate_code(voice.lfrq)
    values["pitch_rate.p0"] = rate
    values["pitch_depth.p0"] = _pitch_depth(voice.pmd, voice.pms, voice.wf)
    values["pitch_wave.p0"] = _WAVE_MAP[voice.wf]
    if values["pitch_depth.p0"] == 3277 and voice.pmd > 0:
        warnings.append("pitch LFO depth clamps at the Type P.fm1 maximum")

    if voice.ne:
        warnings.append(
            "C2 uses the OPM noise generator; Type P.fm1 has no noise, C2 stays a sine"
        )
    if voice.pan not in (64, 192):
        warnings.append(f"pan {voice.pan} has no single-part counterpart")

    for index, op in enumerate(ordered, start=1):
        prefix = f"op{index}"
        values[f"{prefix}_ratio.p0"] = _ratio_q16(op)
        values[f"{prefix}_detune.p0"] = max(-50, min(50, _dt1_cents(op.dt1)))
        values[f"{prefix}_waveform.p0"] = 0
        values[f"{prefix}_level.p0"] = _level(op)
        values[f"{prefix}_feedback.p0"] = (
            _feedback(voice.fl) if index == feedback_index else 0
        )
        mute = 0 if keyed[source_index[index - 1]] else 1
        if op.ar == 0 and _level(op) > 0:
            # OPM AR 0 has no attack step. A fresh note stays at the release
            # level, so the operator is silent. Type P.fm1 has no "never
            # attack" rate, so mute it rather than swell in over 15 seconds.
            mute = 1
            warnings.append(f"op{index} has AR 0 (no attack) and is muted")
        values[f"{prefix}_mute.p0"] = mute

        l1 = 99
        l2 = 99 if op.d1r == 0 else _d1l_level(op.d1l)
        l3 = 0 if op.d2r > 0 else l2
        r1 = _attack_rate(op.ar, op.ks)
        r2 = _decay_rate(op.d1l, op.d1r, op.ks, "decay1") if op.d1r else 99
        r3 = _decay_rate(op.d1l, op.d2r, op.ks, "decay2") if op.d2r else 99
        r4 = _release_rate(op.rr, op.ks)
        if index == 1:
            values["attack.p0"] = r1
            values["release.p0"] = r4
        else:
            values[f"{prefix}.eg.r1.p0"] = r1
            values[f"{prefix}.eg.r4.p0"] = r4
        values[f"{prefix}.eg.r2.p0"] = r2
        values[f"{prefix}.eg.r3.p0"] = r3
        values[f"{prefix}.eg.l1.p0"] = l1
        values[f"{prefix}.eg.l2.p0"] = l2
        values[f"{prefix}.eg.l3.p0"] = l3

        trem = _trem_depth(voice.amd, voice.ams, op.ame, voice.wf)
        values[f"{prefix}_trem_rate.p0"] = rate
        values[f"{prefix}_trem_depth.p0"] = trem
        values[f"{prefix}_trem_wave.p0"] = _WAVE_MAP[voice.wf]
        lo, hi = _key_follow(voice, op)
        values[f"{prefix}_aenv_ks_lo.p0"] = lo
        values[f"{prefix}_aenv_ks_hi.p0"] = hi

        if op.mul * (1.0, math.sqrt(2.0), math.pi / 2.0, math.sqrt(3.0))[op.dt2] > 16.0:
            warnings.append(f"op{index} ratio exceeds 16.00 and is clamped")

    missing = [name for name in names if name not in values]
    if missing:
        raise OpmError(f"defaults are missing parameters: {', '.join(missing[:4])}")
    name = voice.name.strip() or f"OPM {voice.slot}"
    if len(name) > 15:
        warnings.append("name is longer than 15 characters and is truncated")
    if any(ord(char) > 127 for char in name):
        warnings.append("name is not ASCII, the bank stores a replacement character")
    return {"name": name[:15], "params": [values[n] for n in names]}, tuple(warnings)


def _lfo_rate_code(lfrq: int) -> int:
    hz = lfo_hz(lfrq)
    return max(0, min(20_000_000, round(hz * (2**32) / 44100.0)))


def convert_bank(
    voices: Sequence[OpmVoice],
    *,
    names: Sequence[str],
    defaults: Sequence[int],
    start: int = 0,
    limit: int = 128,
    record_count: int | None = None,
    pack: bool = False,
) -> tuple[dict[str, object], list[tuple[int, str, tuple[str, ...]]]]:
    """Convert voices to a 128-slot bank and return the per-slot warnings.

    The source slot number is kept when it is free and inside the bank; a
    duplicate or out-of-range slot takes the next free slot in file order.
    `pack` ignores the source slot and fills the bank from `start` upwards,
    which is what a partial selection usually wants.

    `record_count` keeps only that many leading parameters in each stored
    patch. The device's part record carries the 134 timbre parameters; the
    five routing parameters (`channel`, `low`, `high`, `level`, `delay`) live
    in the multi patch. Pass the SysEx layout's `n_params` here.
    """
    from ._records import MULTI_SLOTS, PART_SLOTS

    if not 0 <= start < PART_SLOTS:
        raise OpmError(f"start slot {start} is outside 0..{PART_SLOTS - 1}")
    parts: list[PartPatch | None] = [None] * PART_SLOTS
    used: set[int] = set()
    report: list[tuple[int, str, tuple[str, ...]]] = []
    next_slot = start
    for voice in voices:
        if len(report) >= limit:
            break
        preferred = voice.slot
        if (
            pack
            or not (0 <= preferred < PART_SLOTS)
            or preferred in used
            or preferred < start
        ):
            while next_slot in used or next_slot < start:
                next_slot += 1
            if next_slot >= PART_SLOTS:
                break
            slot = next_slot
        else:
            slot = preferred
        patch, warnings = convert_voice(voice, names=names, defaults=defaults)
        stored: PartPatch = patch
        if record_count is not None:
            stored = {
                "name": patch["name"],
                "params": patch["params"][:record_count],
            }
        parts[slot] = stored
        used.add(slot)
        report.append((slot, stored["name"], warnings))
        next_slot = max(next_slot, slot + 1)
    return {
        "part_patches": parts,
        "multi_patches": [None] * MULTI_SLOTS,
    }, report
