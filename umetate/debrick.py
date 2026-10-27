# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate debrick` — name the recovery routes + prerequisites (docs §5.4, §8).

A route selector, not a writer: each route's prerequisite is stated, and `mask-rom`
is `blocked` (the USB_KEY dongle is at hand but pending a USB solder). The actual
writes are `umetate flash` (update loader) or the firmware's own boot guard.
"""

from __future__ import annotations

import argparse
import sys

_ROUTES: dict[str, tuple[str, bool]] = {
    "app-rescue": (
        "app-level USB rescue (OCT- at boot, or OCT- + OCT+ 5 s while running)",
        False,
    ),
    "update-loader": (
        "update loader (ota-<identity>): resumes via `umetate flash`",
        False,
    ),
    "mask-rom": (
        "mask-ROM UBOOT — needs the USB_KEY dongle + jl-uboot-tool",
        True,
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate debrick", description=__doc__)
    parser.add_argument("--route", choices=tuple(_ROUTES), help="name one route")
    parser.add_argument("--device", action="store_true", help="the actual write")
    args = parser.parse_args(argv)

    if args.route is None:
        for route, (prereq, blocked) in _ROUTES.items():
            mark = " [blocked]" if blocked else ""
            print(f"debrick: {route:<14}{mark}  {prereq}")
        return 0

    prereq, blocked = _ROUTES[args.route]
    if blocked:
        print(
            f"debrick: {args.route} is blocked — {prereq} (pending a USB solder)",
            file=sys.stderr,
        )
        return 1
    print(f"debrick: {args.route} — {prereq}")
    if not args.device:
        print("debrick: pass --device to write hardware (§8)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
