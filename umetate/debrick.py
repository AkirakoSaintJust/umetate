# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate debrick` — name the recovery routes and their actual procedures.

A route dispatcher, not a writer: `app-rescue`/`update-loader` recover through the
boot chord + `umetate flash` (the `.fwsc` installer), so there is no separate host
write here. The one distinct recovery write — `mask-rom`, a raw-NOR write over the
USB_KEY dongle + `jl-uboot-tool` — is `blocked` (the dongle needs a USB solder).
"""

from __future__ import annotations

import argparse
import sys

# route -> (the actual procedure, blocked)
_ROUTES: dict[str, tuple[str, bool]] = {
    "app-rescue": (
        "boot the chord (OCT- at boot, or OCT- + OCT+ held 5 s) to enter USB rescue, "
        "then `umetate flash`",
        False,
    ),
    "update-loader": (
        "the device is in update mode; `umetate flash` finishes the interrupted write",
        False,
    ),
    "mask-rom": (
        "raw-NOR write via the USB_KEY dongle + jl-uboot-tool (uboot.boot + app.bin)",
        True,
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate debrick", description=__doc__)
    parser.add_argument("--route", choices=tuple(_ROUTES), help="name one route")
    args = parser.parse_args(argv)

    if args.route is None:
        for route, (procedure, blocked) in _ROUTES.items():
            mark = " [blocked]" if blocked else ""
            print(f"debrick: {route:<14}{mark}  {procedure}")
        return 0

    procedure, blocked = _ROUTES[args.route]
    print(f"debrick: {args.route} — {procedure}")
    if blocked:
        print(
            "debrick: mask-rom is blocked (the USB_KEY dongle needs a USB solder)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
