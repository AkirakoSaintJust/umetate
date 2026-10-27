# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate build` — generate + target compile + package → `.fwsc`.

The target branch only (host/WASM are `deep-check`/`web-build`); `blocked` without
the JieLi toolchain. Wraps the inherited `firmware/tools/cmake_target.py` build
(strangler-fig, not a rewrite). The toolchain/SDK come from `$JIELI_TOOLCHAIN` /
`$AC79_SDK`, the local `.jieli/` checkout, or the `umetate-target` volume.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import runner

_ROOT = Path(__file__).resolve().parents[1]
# container-side paths (the runner mounts the repo at /work); the local .jieli/ install
_TC_CONTAINER = "/work/.jieli/jieli-linux-toolchains-20260730.1"
_SDK_CONTAINER = "/work/.jieli/sdk"


def _toolchain_available() -> bool:
    """Is a toolchain reachable (env var, the .jieli/ checkout, or the volume)?"""
    if os.environ.get("JIELI_TOOLCHAIN"):
        return True
    if (_ROOT / ".jieli" / "jieli-linux-toolchains-20260730.1").is_dir():
        return True
    return runner.probe().toolchain_volume


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

    if not _toolchain_available():
        print(
            "build: blocked — JieLi toolchain not set up (`umetate setup`)",
            file=sys.stderr,
        )
        return 1

    toolchain = os.environ.get("JIELI_TOOLCHAIN") or _TC_CONTAINER
    sdk = os.environ.get("AC79_SDK") or _SDK_CONTAINER
    profile = "performance" if args.profile == "perf" else args.profile
    cmd = [
        "python3",
        "tools/cmake_target.py",
        "build",
        "--toolchain",
        toolchain,
        "--sdk",
        sdk,
        "--sdk-assets",
        f"{sdk}/cpu/wl82/tools",
        "--out",
        "/work/firmware/build",
        "--board",
        args.board,
        "--model",
        args.model,
        "--profile",
        profile,
    ]
    if runner.probe().docker:
        return runner.run(cmd, cwd="/work/firmware")
    # no docker: a POSIX host with the toolchain (e.g. the dev container)
    return subprocess.run(cmd, cwd=_ROOT / "firmware").returncode


if __name__ == "__main__":
    sys.exit(main())
