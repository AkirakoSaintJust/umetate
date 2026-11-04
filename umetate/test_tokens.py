# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host test for `umetate tokens` (design tokens + hard-coded UI values)."""

from __future__ import annotations

from pathlib import Path

from . import tokens


def main() -> int:
    failures = 0
    errors = tokens.check()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        failures += 1
    else:
        print("ok: design tokens, generated headers and UI sources agree")

    # The negative cases: the scanner must catch a raw colour, a raw font
    # family, and a raw firmware colour define. A linter that only passes is
    # not a linter.
    bad: list[str] = []
    tokens._scan_source(  # pyright: ignore[reportPrivateUsage]
        Path("bad.cpp"),
        'auto c = "#ff0000"; auto f = "Zen Dots";',
        bad,
    )
    if len(bad) != 2:
        print(f"FAIL: the source scanner missed a raw value: {bad}")
        failures += 1
    else:
        print("ok: the source scanner catches raw colours and fonts")

    if tokens._C_DEFINE.search("#define C_X RGB(1, 2, 3)") is None:  # pyright: ignore[reportPrivateUsage]
        print("FAIL: the firmware colour define is not parsed")
        failures += 1
    else:
        print("ok: the firmware colour define is parsed")

    print("token tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
