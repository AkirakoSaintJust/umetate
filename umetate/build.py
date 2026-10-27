# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate build` — generate + target compile + package → `.fwsc`.

The target branch only (host/WASM are `deep-check`/`web-build`); `blocked` without
the JieLi toolchain. Wraps the inherited `firmware/tools/cmake_target.py` build
(strangler-fig, not a rewrite).
"""

from __future__ import annotations

import argparse
import sys

from . import runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate build", description=__doc__)
    parser.add_argument("--board", choices=("fm1", "smk37"), default="fm1")
    parser.add_argument("--model", choices=("pro", "elite", "mke"), default="pro")
    parser.add_argument("--dsp", choices=("integer", "float"), default="integer")
    parser.add_argument(
        "--clock",
        type=int,
        choices=(240, 320),
        default=320,
        help="360 and 396 have no FM-1 evidence and are rejected",
    )
    parser.add_argument("--profile", choices=("baseline", "perf"), default="perf")
    args = parser.parse_args(argv)

    if args.model != "pro" and args.board != "smk37":
        parser.error("non-pro models require --board smk37")

    probe = runner.probe()
    if not probe.docker or not probe.toolchain_volume:
        print(
            "build: blocked — JieLi toolchain not set up (`umetate setup`)",
            file=sys.stderr,
        )
        return 1

    profile = "performance" if args.profile == "perf" else args.profile
    cmd = [
        "python3",
        "tools/cmake_target.py",
        "build",
        "--toolchain",
        "/opt/jieli/toolchain",
        "--sdk",
        "/opt/jieli/sdk",
        "--out",
        "/work/build",
        "--board",
        args.board,
        "--model",
        args.model,
        "--profile",
        profile,
    ]
    return runner.run(cmd, cwd="/work/firmware")


if __name__ == "__main__":
    sys.exit(main())
