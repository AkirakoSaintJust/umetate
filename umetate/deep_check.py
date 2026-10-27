# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate deep-check` — run the host tests + the checks (`_checks/`, §12.8).

`--host` (the default) runs the host DSP/UI/unit tests; the other checks land in
their phases (`--safety`/`--skill` P3-3, `--web` P3-5, `--links` P6).
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from . import runner

# the checks not yet implemented, mapped to the phase they land in
_NOT_YET = {
    "safety": "P3-3",
    "skill": "P3-3",
    "web": "P3-5",
    "links": "P6-1",
}


def _host() -> int:
    """Run the host tests (the RIB C tests) — via the runner, or directly when there
    is no docker (a POSIX host with cc, e.g. the dev container)."""
    if not runner.probe().docker:
        cmd = ["sh", "tests/run_cmake_host.sh"]
        return subprocess.run(cmd, cwd=runner.REPO_ROOT / "firmware").returncode
    return runner.run(["sh", "tests/run_cmake_host.sh"], cwd="/work/firmware")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate deep-check", description=__doc__)
    parser.add_argument("--host", action="store_true", help="the host tests")
    parser.add_argument("--safety", action="store_true", help="the C standing checks")
    parser.add_argument("--web", action="store_true", help="the standalone-wasm check")
    parser.add_argument("--skill", action="store_true", help="the offline skills")
    parser.add_argument("--links", action="store_true", help="docs cross-references")
    parser.add_argument("--all", action="store_true", help="everything available")
    args = parser.parse_args(argv)

    if not any((args.host, args.safety, args.web, args.skill, args.links, args.all)):
        args.host = True

    failures = 0
    if args.host or args.all:
        rc = _host()
        print(f"deep-check --host: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    for flag in ("safety", "web", "skill", "links"):
        if getattr(args, flag) or args.all:
            print(
                f"deep-check --{flag}: not implemented yet ({_NOT_YET[flag]})",
                file=sys.stderr,
            )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
