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
# container-side paths: the runner mounts the repo at /work, the volume at /opt/jieli
_TC_VOLUME = "/opt/jieli/toolchain"
_SDK_VOLUME = "/opt/jieli/sdk"
_TC_CHECKOUT = "/work/.jieli/jieli-linux-toolchains-20260730.1"
_SDK_CHECKOUT = "/work/.jieli/sdk"


def _volume_populated() -> bool:
    """Does the `umetate-target` volume hold the toolchain + SDK (`setup` ran)?"""
    if not runner.probe().docker:
        return (
            Path(f"{_TC_VOLUME}/pi32v2/bin/clang").is_file()
            and Path(f"{_SDK_VOLUME}/cpu/wl82/tools/uboot.boot").is_file()
        )
    return (
        runner.run(["test", "-x", f"{_TC_VOLUME}/pi32v2/bin/clang"]) == 0
        and runner.run(["test", "-f", f"{_SDK_VOLUME}/cpu/wl82/tools/uboot.boot"]) == 0
    )


def _resolve() -> tuple[str, str] | None:
    """The (toolchain, sdk) container-side paths, or `None` when nothing is set up.

    Precedence: explicit `$JIELI_TOOLCHAIN`/`$AC79_SDK`, then the `umetate-target`
    volume (the canonical `setup` location), then the local `.jieli/` checkout.
    """
    tc_env, sdk_env = os.environ.get("JIELI_TOOLCHAIN"), os.environ.get("AC79_SDK")
    if tc_env and sdk_env:
        return tc_env, sdk_env
    if _volume_populated():
        return _TC_VOLUME, _SDK_VOLUME
    if (_ROOT / ".jieli" / "jieli-linux-toolchains-20260730.1").is_dir():
        return _TC_CHECKOUT, _SDK_CHECKOUT
    return None


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

    resolved = _resolve()
    if resolved is None:
        print(
            "build: blocked — JieLi toolchain not set up (`umetate setup`)",
            file=sys.stderr,
        )
        return 1
    toolchain, sdk = resolved
    profile = "performance" if args.profile == "perf" else str(args.profile)
    cmd: list[str] = [
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
        str(args.board),
        "--model",
        str(args.model),
        "--profile",
        profile,
    ]
    if runner.probe().docker:
        return runner.run(cmd, cwd="/work/firmware")
    # no docker: a POSIX host with the toolchain (e.g. the dev container)
    return subprocess.run(cmd, cwd=_ROOT / "firmware").returncode


if __name__ == "__main__":
    sys.exit(main())
