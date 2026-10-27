# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The CLI's own contract tests (docs/roadmap.md §12.8).

Run: python3 -m umetate.test_cli
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys
from collections.abc import Callable

import umetate.cli as cli
from umetate import __version__

_Tests = list[tuple[str, Callable[[], None]]]


def _no_import_side_effects() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        importlib.reload(cli)
    assert buf.getvalue() == "", "importing umetate.cli printed output"


def _help_lists_all() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(["--help"])
    assert rc == 0
    out = buf.getvalue()
    for name in cli.COMMANDS:
        assert name in out, f"--help is missing {name!r}"


def _version_command() -> None:
    from . import version

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = version.main([])
    assert rc == 0
    assert buf.getvalue().strip() == __version__


def _status_parses() -> None:
    from . import status

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = status.main([])
    assert rc == 0
    assert "Phase 0" in buf.getvalue() and "Phase 2" in buf.getvalue()


def _quick_check_json() -> None:
    from . import quick_check

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = quick_check.main(["--json"])
    assert rc in (0, 1)
    data = json.loads(buf.getvalue())
    assert "layers" in data
    for layer in data["layers"]:
        assert set(layer) == {"layer", "status", "detail"}


def _stub_reports_phase() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = cli.main(["build"])
    assert rc == 1
    assert "P3-2" in buf.getvalue()


def main() -> int:
    tests: _Tests = [
        ("no import side effects", _no_import_side_effects),
        ("--help lists all commands", _help_lists_all),
        ("version prints __version__", _version_command),
        ("status parses the roadmap", _status_parses),
        ("quick-check --json emits the layer/status shape", _quick_check_json),
        ("a stub reports its phase", _stub_reports_phase),
    ]
    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"ok: {name}")
        except AssertionError as exc:
            print(f"FAIL: {name}: {exc}")
            failures += 1
    print("cli tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
