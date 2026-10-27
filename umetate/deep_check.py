# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate deep-check` — run the host tests + the checks (§12.8).

`--host` (the default) runs the host DSP/UI/unit tests; `--safety` runs the C
standing checks (lint); `--web` builds the standalone wasm + proves host == wasm
(P4-1); `--skill` verifies the offline skill bundles (P5); `--links` lands in P6.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from . import runner

# the checks not yet implemented, mapped to the phase they land in
_NOT_YET = {
    "links": "P6-1",
}


def _host() -> int:
    """Run the host tests (the RIB C tests) — via the runner, or directly when there
    is no docker (a POSIX host with cc, e.g. the dev container)."""
    if not runner.probe().docker:
        cmd = ["sh", "tests/run_cmake_host.sh"]
        return subprocess.run(cmd, cwd=runner.REPO_ROOT / "firmware").returncode
    return runner.run(["sh", "tests/run_cmake_host.sh"], cwd="/work/firmware")


def _web() -> int:
    """Build the standalone `dsp.wasm` and prove host == wasm (the parity check)."""
    import json

    from . import web

    try:
        patch = json.loads(web._DEFAULT_PATCH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"deep-check --web: {exc}", file=sys.stderr)
        return 1
    name = str(patch["name"]).replace("-", "_").replace(".", "_")
    if web.build(patch, web._OUT, name) != 0:
        return 1
    ok, msg = web.check_parity(web._OUT, name)
    print(f"deep-check --web parity: {'ok' if ok else 'FAIL'} ({msg})")
    return 0 if ok else 1


def _skill() -> int:
    """Verify the offline skill bundles: `SKILL.md` + generated `references/` in
    sync with the canonical docs (fail on drift)."""
    from . import _skill

    errors = _skill.check()
    if errors:
        for error in errors:
            print(f"deep-check --skill: {error}", file=sys.stderr)
        return 1
    print("deep-check --skill: ok (two skills, references in sync)")
    return 0


def _safety() -> int:
    """The C standing checks (SEC-1/SEC-2, ROM, MMIO, no-double-in-DSP)."""
    from . import lint

    errors = lint.c_checks()
    if errors:
        for error in errors:
            print(f"deep-check --safety: {error}", file=sys.stderr)
        return 1
    print("deep-check --safety: ok")
    return 0


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
    if args.safety or args.all:
        rc = _safety()
        print(f"deep-check --safety: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.web or args.all:
        rc = _web()
        print(f"deep-check --web: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.skill or args.all:
        rc = _skill()
        print(f"deep-check --skill: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    for flag in ("links",):
        if getattr(args, flag) or args.all:
            print(
                f"deep-check --{flag}: not implemented yet ({_NOT_YET[flag]})",
                file=sys.stderr,
            )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
