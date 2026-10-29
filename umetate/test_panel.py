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

from ._ir import GenError
from ._panel import check_sources, generate_panel
from ._schema import PanelBinding, PanelManifest, as_panel

ROOT = Path(__file__).resolve().parents[1]


def _compile(panel: PanelManifest) -> tuple[bool, str]:
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
    panel = as_panel(
        json.loads((ROOT / "firmware" / "panel.json").read_text(encoding="utf-8"))
    )
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

    bad: PanelManifest = {
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

    # generate_panel(panel, param_ids) shares the DSP set_param id space
    bound: PanelManifest = {
        "name": "demo",
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [{"type": "param_row", "row": 1, "param": "cutoff"}],
                    }
                ],
                "bindings": [
                    {"source": "ENC_KNOB1", "target": "cutoff", "behavior": "absolute"}
                ],
            }
        },
        "global": [],
    }
    ids = {"env.attack": 0, "env.release": 1, "lp.cutoff": 2, "cutoff": 2}
    bound_src = generate_panel(bound, ids)
    if "P_cutoff = 2" in bound_src and "N_PARAMS = 3" in bound_src:
        print("ok: the panel shares the DSP set_param id space (P_cutoff = 2)")
    else:
        print("FAIL: the panel did not bind to the DSP set_param id")
        failures += 1

    try:
        generate_panel(
            {
                "name": "demo",
                "contexts": {
                    "home": {
                        "pages": [
                            {
                                "id": "home",
                                "widgets": [
                                    {"type": "param_row", "row": 1, "param": "ghost"}
                                ],
                            }
                        ]
                    }
                },
                "global": [],
            },
            ids,
        )
        print("FAIL: unknown panel param not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: unknown panel param rejected ({exc})")

    # the real FM-1 controls resolve + compile (the source vocabulary covers the board)
    fm1_binds: list[PanelBinding] = [
        {"source": s, "target": "cutoff", "behavior": "relative"}
        for s in (
            "ENC_ALGORITHM",
            "BTN_GLO",
            "BTN_FX",
            "BTN_SEL",
            "BTN_ENV",
            "BTN_LFO",
            "BTN_ARP",
        )
    ]
    fm1_panel: PanelManifest = {
        "name": "fm1",
        "contexts": {
            "home": {"pages": [{"id": "home", "widgets": []}], "bindings": fm1_binds}
        },
        "global": [],
    }
    ok, msg = _compile(fm1_panel)
    print(
        ("ok: " if ok else "FAIL: ")
        + ("the real FM-1 sources resolve + compile" if ok else msg)
    )
    failures += 0 if ok else 1

    try:
        generate_panel(
            {
                "name": "demo",
                "contexts": {"home": {"pages": [{"id": "home", "widgets": []}]}},
                "global": [{"source": "BTN_WOBBLE", "action": "pop_home"}],
            }
        )
        print("FAIL: unknown source not rejected")
        failures += 1
    except GenError as exc:
        print(f"ok: unknown source rejected ({exc})")

    # the source-vocabulary check: a panel must bind only the target board's controls.
    ffm = as_panel(
        json.loads(
            (ROOT / "examples" / "fourop-fm" / "panel.json").read_text(encoding="utf-8")
        )
    )
    bad_sources = check_sources(ffm, "fm1")
    print(
        ("ok: " if not bad_sources else "FAIL: ")
        + (
            "the fourop-fm panel binds only FM-1 controls"
            if not bad_sources
            else f"non-FM-1 sources {bad_sources}"
        )
    )
    failures += 0 if not bad_sources else 1

    phantom: PanelManifest = {
        "name": "phantom",
        "contexts": {
            "home": {
                "pages": [{"id": "home", "widgets": []}],
                "bindings": [{"source": "ENC_KNOB5", "target": "cutoff"}],
            }
        },
        "global": [],
    }
    bad_sources = check_sources(phantom, "fm1")
    print(
        ("ok: " if bad_sources == ["ENC_KNOB5"] else "FAIL: ")
        + "the source-vocabulary check flags a phantom source"
    )
    failures += 0 if bad_sources == ["ENC_KNOB5"] else 1

    # the scope + spectro widgets generate (and compile against ui.h)
    vis: PanelManifest = {
        "name": "vis",
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [
                            {"type": "scope", "row": 1, "span": 3},
                            {"type": "spectro", "row": 4, "span": 3},
                        ],
                    }
                ]
            }
        },
        "global": [],
    }
    vis_src = generate_panel(vis)
    if "UI_SCOPE" in vis_src and "UI_SPECTRO" in vis_src:
        print("ok: scope/spectro widgets map to UI_SCOPE/UI_SPECTRO")
    else:
        print("FAIL: scope/spectro widgets did not map")
        failures += 1

    print("panel tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
