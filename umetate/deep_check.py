# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate deep-check` — run the host tests + the checks (§12.8).

`--host` (the default) runs the host DSP/UI/unit tests; `--safety` runs the C
standing checks (lint); `--web` builds the standalone wasm + proves host == wasm
(P4-1); `--python` runs the Python layer (ruff + mypy + the four test modules);
`--skill` verifies the offline skill bundles (P5); `--links` checks the docs'
cross-references (P6); `--roadmap` keeps the roadmap dashboard under 500 lines;
`--pyright` runs the strict Python type-check. `--all` is
the complete gate — the single deterministic "is this increment done" check.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from . import runner


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
    from ._schema import as_patch

    try:
        patch = as_patch(json.loads(web.DEFAULT_PATCH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"deep-check --web: {exc}", file=sys.stderr)
        return 1
    name = patch["name"].replace("-", "_").replace(".", "_")
    if web.build(patch, web.OUT, name) != 0:
        return 1
    ok, msg = web.check_parity(web.OUT, name)
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
    print("deep-check --skill: ok (four skills, references in sync)")
    return 0


def _lib() -> int:
    """The module-library table is generated from the manifests and in sync."""
    from . import lib

    errors = lib.check()
    if errors:
        for error in errors:
            print(f"deep-check --lib: {error}", file=sys.stderr)
        return 1
    print("deep-check --lib: ok (module library in sync)")
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


def _pyright() -> int:
    """The Python type-check (pyright strict, §6.8; reads `[tool.pyright]`)."""
    if runner.probe().docker:
        return runner.run(["pyright"], cwd="/work")
    try:
        return subprocess.run(["pyright"], cwd=runner.REPO_ROOT).returncode
    except FileNotFoundError:
        print(
            "deep-check --pyright: pyright not found — rebuild the image "
            "(docker/build.sh) and recreate `umetate-host`",
            file=sys.stderr,
        )
        return 1


def _memory() -> int:
    """The memory-safety gate (host-side): boot the built firmware on the emulator
    with FM1_STRICT (the hardware guard + the misaligned-access fault) and fail on a
    CPU exception. Skipped inside the container, where the host emulator is absent."""
    from . import _emu, emu

    if not runner.probe().docker:
        # inside the container there is no host emulator to run
        print(
            "deep-check --memory: skipped in the container "
            "(run `umetate emu --memory` on the host)",
        )
        return 0
    if not _emu.emulator_built():
        print(
            "deep-check --memory: fm1-emu not built - run `umetate setup` first",
            file=sys.stderr,
        )
        return 1
    fwsc = emu._default_fwsc("fm1")  # pyright: ignore[reportPrivateUsage]
    if not fwsc.is_file():
        print(
            "deep-check --memory: no built .fwsc - run `umetate build --synth` first",
            file=sys.stderr,
        )
        return 1
    return emu._memory_check(fwsc)  # pyright: ignore[reportPrivateUsage]


# the Python layer: lint + format + types + the owned test modules. One list, so
# a new test module is a one-line addition (and the gate stays deterministic).
_PYTHON_STEPS: tuple[tuple[str, list[str]], ...] = (
    ("ruff check", ["ruff", "check", "umetate/", "plugin/tools/"]),
    ("ruff format", ["ruff", "format", "--check", "umetate/", "plugin/tools/"]),
    ("mypy", ["mypy", "--strict"]),
    ("test_generate", ["python3", "-m", "umetate.test_generate"]),
    ("test_panel", ["python3", "-m", "umetate.test_panel"]),
    ("test_ratio", ["python3", "-m", "umetate.test_ratio"]),
    ("test_web", ["python3", "-m", "umetate.test_web"]),
    ("test_cli", ["python3", "-m", "umetate.test_cli"]),
    ("test_theme", ["python3", "-m", "umetate.test_theme"]),
    ("test_tokens", ["python3", "-m", "umetate.test_tokens"]),
    ("test_font_atlas", ["python3", "-m", "umetate.test_font_atlas"]),
    ("test_perf", ["python3", "-m", "umetate.test_perf"]),
)


def _python() -> int:
    """The Python layer: ruff (check + format) + mypy --strict + the test modules."""
    failures = 0
    for label, cmd in _PYTHON_STEPS:
        if runner.probe().docker:
            rc = runner.run(list(cmd), cwd="/work")
        else:
            rc = subprocess.run(list(cmd), cwd=runner.REPO_ROOT).returncode
        print(f"deep-check --python {label}: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    return 1 if failures else 0


def _links() -> int:
    """The docs' cross-references resolve (no dead Markdown links)."""
    from . import _links

    errors = _links.check()
    if errors:
        for error in errors:
            print(f"deep-check --links: {error}", file=sys.stderr)
        return 1
    print("deep-check --links: ok")
    return 0


_ROADMAP = runner.REPO_ROOT / "docs" / "roadmap.md"
_ROADMAP_LIMIT = 500


def _roadmap() -> int:
    """The roadmap stays a current dashboard, not a growing history."""
    try:
        lines = _ROADMAP.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"deep-check --roadmap: {exc}", file=sys.stderr)
        return 1
    if len(lines) > _ROADMAP_LIMIT:
        print(
            f"deep-check --roadmap: {len(lines)} lines, limit {_ROADMAP_LIMIT}. "
            "Compact it with the procedure in AGENTS.md.",
            file=sys.stderr,
        )
        return 1
    print(f"deep-check --roadmap: ok ({len(lines)} lines)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate deep-check", description=__doc__)
    parser.add_argument("--host", action="store_true", help="the host tests")
    parser.add_argument("--safety", action="store_true", help="the C standing checks")
    parser.add_argument("--web", action="store_true", help="the standalone-wasm check")
    parser.add_argument(
        "--python", action="store_true", help="ruff + mypy + the test modules"
    )
    parser.add_argument("--skill", action="store_true", help="the offline skills")
    parser.add_argument("--links", action="store_true", help="docs cross-references")
    parser.add_argument(
        "--roadmap", action="store_true", help="the 500-line roadmap cap"
    )
    parser.add_argument("--lib", action="store_true", help="the generated node library")
    parser.add_argument("--pyright", action="store_true", help="the strict type-check")
    parser.add_argument(
        "--memory", action="store_true", help="the memory-safety gate (host-side)"
    )
    parser.add_argument("--all", action="store_true", help="everything available")
    args = parser.parse_args(argv)

    if not any(
        (
            args.host,
            args.safety,
            args.web,
            args.python,
            args.skill,
            args.links,
            args.roadmap,
            args.lib,
            args.pyright,
            args.memory,
            args.all,
        )
    ):
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
    if args.python or args.all:
        failures += 0 if _python() == 0 else 1
    if args.skill or args.all:
        rc = _skill()
        print(f"deep-check --skill: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.lib or args.all:
        rc = _lib()
        print(f"deep-check --lib: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.links or args.all:
        rc = _links()
        print(f"deep-check --links: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.roadmap or args.all:
        rc = _roadmap()
        print(f"deep-check --roadmap: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.pyright or args.all:
        rc = _pyright()
        print(f"deep-check --pyright: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    if args.memory or args.all:
        rc = _memory()
        print(f"deep-check --memory: {'ok' if rc == 0 else 'failed'}")
        failures += 0 if rc == 0 else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
