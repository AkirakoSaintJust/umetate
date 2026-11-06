# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host performance regression guard (docs/roadmap.md §12.7.3).

It generates and compiles the `examples/type-p-fm1` test project (20 voices), then
times a worst-case `render(256)` on host. The figure is a *relative* measure,
because the device fit is the emulator's job (`umetate emu --check --mhz 320`),
though a gross slowdown in the generator's emitted code shows up here too. The
budget is ~2.8x the measured baseline, so it catches algorithmic regressions
without flaking on wall-clock noise.

Run: python3 -m umetate.test_perf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ._schema import as_patch
from .budget import measure

_ROOT = Path(__file__).resolve().parents[1]
_PATCH = _ROOT / "examples" / "type-p-fm1" / "patch.json"

# The pinned-container baseline is ~140 us (`umetate budget examples/type-p-fm1`).
# The min of a few process runs keeps the figure honest under load, the 2.8x
# headroom tolerates wall-clock noise + a slower host while still tripping on a
# real algorithmic regression (which is usually 2-10x).
_RUNS = 3
_BUDGET_US = 400.0


def main() -> int:
    try:
        patch = as_patch(json.loads(_PATCH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: cannot read {_PATCH}: {exc}")
        return 1

    try:
        best = min(measure(patch) for _ in range(_RUNS))
    except SystemExit as exc:
        print(f"FAIL: type-p-fm1 perf guard could not measure: {exc}")
        return 1

    if best >= _BUDGET_US:
        print(
            f"FAIL: type-p-fm1 render(256) regressed: {best:.1f} us "
            f"(budget {_BUDGET_US:.0f} us)"
        )
        return 1
    print(f"ok: type-p-fm1 render(256) = {best:.1f} us (budget {_BUDGET_US:.0f} us)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
