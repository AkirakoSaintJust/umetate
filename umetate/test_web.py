# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Host tests for the WASM parity lab (docs/roadmap.md P4-1).

The generated `dsp.c` compiles to a standalone `dsp.wasm` (no import section), and
the wasm (node) output matches the host (gcc) output exactly.
Run: python3 -m umetate.test_web
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from . import web

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures = 0
    patch = json.loads(
        (ROOT / "examples" / "pocket-drone" / "patch.json").read_text(encoding="utf-8")
    )
    name = "pocket_drone"

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        if web.build(patch, out, name) != 0:
            print("FAIL: web-build failed")
            return 1

        wasm = (out / "dsp.wasm").read_bytes()
        if web.wasm_import_count(wasm) != 0:
            print("FAIL: dsp.wasm has an import section")
            failures += 1
        else:
            print("ok: dsp.wasm is standalone (no import section)")

        for harness in ("index.html", "main.js", "worklet.js"):
            if not (out / harness).is_file():
                print(f"FAIL: {harness} not written")
                failures += 1
        if "pocket_drone" not in (out / "worklet.js").read_text(encoding="utf-8"):
            print("FAIL: worklet.js does not carry the synth name")
            failures += 1

        ok, msg = web.check_parity(out, name)
        print(("ok: " if ok else "FAIL: ") + ("parity: " + msg))
        failures += 0 if ok else 1

    print("web tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
