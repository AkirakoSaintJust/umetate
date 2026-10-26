# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host tests for the panel generator (docs/roadmap.md §12.6 verification).

- the demo panel generates deterministically (the checked-in firmware/src/panel.h is
  exactly what panel.json produces);
- the generated header compiles against the UI runtime types;
- an unknown source/action is rejected with a GenError.
Run: python3 -m umetate.test_panel
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ._ir import GenError
from ._panel import generate_panel

ROOT = Path(__file__).resolve().parents[1]


def _compile(panel: dict[str, Any]) -> tuple[bool, str]:
    """Compile the generated panel.h against ui.h (object check only)."""
    src = generate_panel(panel)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "panel.h").write_text(src)
        (d / "main.c").write_text(
            '#include "panel.h"\nint main(void){ return (int)PANEL.n_params; }\n'
        )
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-I",
                str(ROOT / "firmware" / "src"),
                "-c",
                "-o",
                str(d / "main.o"),
                str(d / "main.c"),
            ],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.stderr


def main() -> int:
    failures = 0
    panel = json.loads((ROOT / "firmware" / "panel.json").read_text(encoding="utf-8"))
    src = generate_panel(panel)

    # determinism: the checked-in header is exactly what panel.json produces
    checked_in = (ROOT / "firmware" / "src" / "panel.h").read_text(encoding="utf-8")
    if src == checked_in:
        print("ok: firmware/src/panel.h is up to date with panel.json")
    else:
        print("FAIL: firmware/src/panel.h is stale — regenerate it")
        failures += 1

    ok, msg = _compile(panel)
    print(
        ("ok: " if ok else "FAIL: ")
        + ("generated panel.h compiles against ui.h" if ok else msg)
    )
    failures += 0 if ok else 1

    bad: dict[str, Any] = {
        "name": "bad",
        "contexts": {
            "home": {"pages": [{"id": "home", "widgets": []}]},
        },
        "global": [{"source": "KEY", "action": "wobble"}],
    }
    try:
        generate_panel(bad)
        print("FAIL: unknown action not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: unknown action rejected ({exc})")

    print("panel tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
