# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host test: the coarse-ratio detent ladder shared by panel.json and the plugin."""

from __future__ import annotations

from ._ratio import _Q16, _RATIO_BASES, ratio_detents  # pyright: ignore[reportPrivateUsage]

LO = 32768
HI = 1048576


def main() -> int:
    failures = 0
    detents = ratio_detents(LO, HI)

    ordered = detents == sorted(set(detents))
    in_range = all(LO <= value <= HI for value in detents)
    if ordered and in_range:
        print("ok: ratio detents are sorted, unique, and inside the range")
    else:
        print("FAIL: ratio detents are unsorted, repeated, or out of range")
        failures += 1

    # every base contributes its first multiple, within half a display step
    half_step = 0.005 * _Q16
    missing = [
        base
        for base in _RATIO_BASES
        if not any(abs(value - base * _Q16) <= half_step for value in detents)
    ]
    if not missing:
        print("ok: every ratio base is reachable at its first multiple")
    else:
        print(f"FAIL: no detent near {missing}")
        failures += 1

    # the 2-decimal readout is the contract, so each detent reads differently
    readouts = [f"{value / _Q16:.2f}" for value in detents]
    if len(set(readouts)) == len(readouts):
        print("ok: every ratio detent has its own 2-decimal readout")
    else:
        print("FAIL: two ratio detents share a readout")
        failures += 1

    # nearest-detent snapping is idempotent, so a second pass never moves
    settled = all(_snap(value, detents) == value for value in detents)
    if settled:
        print("ok: snapping a detent leaves it alone")
    else:
        print("FAIL: snapping moved a detent")
        failures += 1

    # the readout wins over the raw ratio: sqrt(2)/2 reads 0.71, not 0.70
    low = [f"{value / _Q16:.2f}" for value in detents if value < _Q16]
    if low == ["0.50", "0.71", "0.79", "0.87"]:
        print("ok: the lower range reads 0.50, 0.71, 0.79, 0.87")
    else:
        print(f"FAIL: the lower range reads {low}")
        failures += 1

    return 1 if failures else 0


def _snap(value: int, detents: list[int]) -> int:
    return min(detents, key=lambda d: abs(d - value))


if __name__ == "__main__":
    raise SystemExit(main())
