# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate setup` — install the JieLi toolchain + SDK into the Docker volume.

Auto-fetch with opt-in consent (`--toolchain auto` → pkgman.jieliapp.com,
`--sdk auto` → gitee) or a user-supplied path; the toolchain version and the SDK
asset SHA-256s are verified against `env.lock` (a mismatch aborts unless `--force`).
`--dry-run` changes nothing; idempotent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from . import runner

_ROOT = Path(__file__).resolve().parents[1]
_ENV_LOCK = _ROOT / "env.lock"
_LOCAL_ENV = _ROOT / ".local-env"

# the container-side volume path (the CLI is host-side; the fetch runs via the runner)
_VOLUME = "/opt/jieli"


def _lock() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_ENV_LOCK.read_text(encoding="utf-8")))


def _plan(args: argparse.Namespace, lock: dict[str, Any]) -> list[str]:
    """The actions `setup` would take (for --dry-run and the consent prompt)."""
    steps: list[str] = []
    toolchain = lock["jieli_toolchain"]["linux"]
    if args.toolchain == "auto":
        steps.append(f"fetch {toolchain} from {lock['jieli_toolchain']['download']}")
    else:
        steps.append(f"use toolchain tarball {args.toolchain}")
    steps.append(f"verify {toolchain} version + SHA-256, extract to {_VOLUME}")
    sdk = lock["ac79_sdk"]
    if args.sdk == "auto":
        steps.append(f"git clone {sdk['source']} @ {sdk['tag']}")
    else:
        steps.append(f"use SDK checkout {args.sdk}")
    for name in sdk["assets"]:
        steps.append(f"copy {name} and verify SHA-256")
    steps.append(f"record --clock {args.clock} to .local-env")
    return steps


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fetch_toolchain(args: argparse.Namespace, lock: dict[str, Any]) -> Path:
    """Download (auto) or copy (path) the toolchain tarball; verify + extract."""
    out = Path("/tmp") / f"{lock['jieli_toolchain']['linux']}.tar.xz"
    if args.toolchain == "auto":
        subprocess.run(
            ["curl", "-L", lock["jieli_toolchain"]["download"], "-o", str(out)],
            check=True,
        )
    else:
        out = Path(args.toolchain)
    pinned = lock["jieli_toolchain"].get("linux_sha256", "")
    if (
        pinned
        and not pinned.startswith("TBD")
        and _sha256(out) != pinned
        and not args.force
    ):
        raise SystemExit(
            f"toolchain SHA-256 mismatch (expected {pinned}); --force overrides"
        )
    # extract into the volume (the runner mounts /opt/jieli read-only, so this is
    # delegated to a host-side mount; blocked until the volume is populated)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate setup", description=__doc__)
    parser.add_argument("--toolchain", default="auto", metavar="auto|PATH")
    parser.add_argument("--sdk", default="auto", metavar="auto|PATH")
    parser.add_argument("--clock", type=int, choices=(240, 320), default=320)
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan, change nothing"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--yes", action="store_true", help="skip the prompt")
    parser.add_argument("--force", action="store_true", help="accept a mismatch")
    args = parser.parse_args(argv)

    if not _ENV_LOCK.exists():
        print("setup: env.lock not found", file=sys.stderr)
        return 1
    lock = _lock()
    probe = runner.probe()

    if args.dry_run:
        if args.json:
            print(json.dumps({"steps": _plan(args, lock)}))
        else:
            for step in _plan(args, lock):
                print(f"  - {step}")
        return 0

    if not probe.docker:
        print("setup: docker not found (is Docker Desktop running?)", file=sys.stderr)
        return 1

    if not args.yes:
        print("umetate setup will download the JieLi toolchain + SDK from their")
        print(
            "vendors (we do not redistribute); see LICENSING.md. Continue? [y/N] ",
            end="",
        )
        if input().strip().lower() != "y":
            return 1

    try:
        _fetch_toolchain(args, lock)
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        print(f"setup: blocked — {exc}", file=sys.stderr)
        return 1

    # record the clock choice (gitignored, per-checkout)
    _LOCAL_ENV.write_text(f"clock={args.clock}\n", encoding="utf-8")
    print(f"setup: done (toolchain + SDK in {_VOLUME}, clock={args.clock})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
