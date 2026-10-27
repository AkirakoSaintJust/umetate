# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate setup` — install the JieLi toolchain + SDK into the `/opt/jieli` volume.

Auto-fetch with opt-in consent (`--toolchain auto` → pkgman.jieliapp.com, `--sdk
auto` → gitee) or a user-supplied, container-visible path. The toolchain tarball
SHA-256 and the three SDK asset SHA-256s are verified against `env.lock` (a mismatch
aborts unless `--force`); the toolchain is smoke-tested (`clang --version`).
`--dry-run` changes nothing; re-running overwrites the volume. Runs in a throwaway
container with `umetate-target` mounted read-write (the only legitimate writer).
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any, cast

from . import runner

_ROOT = Path(__file__).resolve().parents[1]
_ENV_LOCK = _ROOT / "env.lock"
_LOCAL_ENV = _ROOT / ".local-env"

_VOLUME = "/opt/jieli"
_TC_DIR = f"{_VOLUME}/toolchain"
_SDK_DIR = f"{_VOLUME}/sdk"


def _lock() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_ENV_LOCK.read_text(encoding="utf-8")))


def _plan(args: argparse.Namespace, lock: dict[str, Any]) -> list[str]:
    """The actions `setup` will take (for `--dry-run` and the consent prompt)."""
    tc = lock["jieli_toolchain"]
    sdk = lock["ac79_sdk"]
    steps = [
        f"fetch {tc['linux']} from {tc['download']}"
        if args.toolchain == "auto"
        else f"use toolchain tarball {args.toolchain}",
        f"verify {tc['linux']} SHA-256, extract to {_TC_DIR}",
        "smoke-test the toolchain (clang --version)",
        f"git clone {sdk['tag']} from {sdk['source']}"
        if args.sdk == "auto"
        else f"use SDK checkout {args.sdk}",
    ]
    steps.extend(f"verify SDK asset {name} SHA-256" for name in sdk["assets"])
    steps.append(f"record --clock {args.clock} to .local-env")
    return steps


def _script(args: argparse.Namespace, lock: dict[str, Any]) -> str:
    """The POSIX script the writable container runs (fetch + verify + install)."""
    tc = lock["jieli_toolchain"]
    sdk = lock["ac79_sdk"]
    verify = not args.force
    clang = f"{_TC_DIR}/pi32v2/bin/clang"
    lines = ["set -e"]

    # ---- toolchain ----
    lines.append(f"mkdir -p {shlex.quote(_TC_DIR)}")
    if args.toolchain == "auto":
        tarball = "/tmp/tc.tar.xz"
        lines.append(f"curl -fsSL {shlex.quote(tc['download'])} -o {tarball}")
    else:
        tarball = args.toolchain
    pinned = tc.get("linux_sha256", "")
    if verify and pinned and not pinned.startswith("TBD"):
        lines.append(
            f"echo {shlex.quote(pinned)} {shlex.quote(tarball)} | sha256sum -c -"
        )
    tar = f"tar -xJf {shlex.quote(tarball)} -C {shlex.quote(_TC_DIR)}"
    lines.append(f"{tar} --strip-components=1")
    lines.append(f"{shlex.quote(clang)} --version >/dev/null")
    lines.append(f"echo 'toolchain ok:' $({shlex.quote(clang)} --version | head -1)")

    # ---- sdk ----
    if args.sdk == "auto":
        lines.append(
            f"[ -d {shlex.quote(_SDK_DIR)} ] && rm -rf {shlex.quote(_SDK_DIR)}"
        )
        clone = (
            f"git clone --depth 1 --branch {shlex.quote(sdk['tag'])} "
            f"{shlex.quote(sdk['source'])} {shlex.quote(_SDK_DIR)}"
        )
        lines.append(clone)
    else:
        lines.append(f"cp -a {shlex.quote(args.sdk)} {shlex.quote(_SDK_DIR)}")
    assets = f"{_SDK_DIR}/cpu/wl82/tools"
    for name, expected in sdk["assets"].items():
        path = f"{assets}/{name}"
        if verify:
            lines.append(
                f"echo {shlex.quote(expected)} {shlex.quote(path)} | sha256sum -c -"
            )
        else:
            lines.append(f"test -f {shlex.quote(path)}")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate setup", description=__doc__)
    parser.add_argument("--toolchain", default="auto", metavar="auto|PATH")
    parser.add_argument("--sdk", default="auto", metavar="auto|PATH")
    parser.add_argument("--clock", type=int, choices=(240, 320), default=320)
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan, change nothing"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--yes", action="store_true", help="skip the consent prompt")
    parser.add_argument("--force", action="store_true", help="accept a hash mismatch")
    args = parser.parse_args(argv)

    if not _ENV_LOCK.exists():
        print("setup: env.lock not found", file=sys.stderr)
        return 1
    lock = _lock()

    if args.dry_run:
        if args.json:
            print(json.dumps({"steps": _plan(args, lock)}))
        else:
            for step in _plan(args, lock):
                print(f"  - {step}")
        return 0

    if not args.yes:
        print("umetate setup downloads the JieLi toolchain + SDK from their vendors")
        print("(never redistributed by umetate; see LICENSING.md).")
        print("Continue? [y/N] ", end="")
        if input().strip().lower() != "y":
            return 1

    rc = runner.run_writable(["sh", "-ec", _script(args, lock)])
    if rc != 0:
        print(
            "setup: blocked — the container install failed (see output above)",
            file=sys.stderr,
        )
        return 1

    _LOCAL_ENV.write_text(f"clock={args.clock}\n", encoding="utf-8")
    print(f"setup: done (toolchain + SDK in {_VOLUME}, clock={args.clock})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
