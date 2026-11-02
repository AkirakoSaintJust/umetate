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
import re
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
            (ROOT / "examples" / "type-p-fm1" / "panel.json").read_text(
                encoding="utf-8"
            )
        )
    )
    bad_sources = check_sources(ffm, "fm1")
    print(
        ("ok: " if not bad_sources else "FAIL: ")
        + (
            "the type-p-fm1 panel binds only FM-1 controls"
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

    # the scope + spectro widgets generate (and compile against ui.h); the
    # `channel` field selects the op index (0..3 -> "op N of the active part"),
    # `active` selects the active operator (0x40), and `mix_part` selects a part
    # mix (0x80|part).
    vis: PanelManifest = {
        "name": "vis",
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [
                            {"type": "scope", "row": 1, "span": 3, "channel": 2},
                            {"type": "spectro", "row": 4, "span": 3, "mix_part": 1},
                            {"type": "scope", "row": 7, "span": 3, "active": True},
                        ],
                    }
                ]
            }
        },
        "global": [],
    }
    vis_src = generate_panel(vis)
    if (
        "UI_SCOPE" in vis_src
        and "UI_SPECTRO" in vis_src
        and ", 2," in vis_src
        and ", 129," in vis_src  # 0x80 | 1 = the part-1 mix selector
        and ", 64," in vis_src  # 0x40 = the active operator
    ):
        print(
            "ok: scope/spectro widgets map to UI_SCOPE/UI_SPECTRO + "
            "op/part/active selector"
        )
    else:
        print("FAIL: scope/spectro widgets did not map")
        failures += 1

    # the subheader widget maps to UI_SUBHEADER with the op/part selector, and the
    # panel carries the algorithm + part count for the always-visible header.
    sub: PanelManifest = {
        "name": "sub",
        "alg": "algorithm",
        "parts": 2,
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [
                            {"type": "subheader", "row": 2, "text": "A-ENV"},
                            {
                                "type": "subheader",
                                "row": 3,
                                "text": "P-LFO",
                                "part": True,
                            },
                        ],
                    }
                ]
            }
        },
        "global": [],
    }
    sub_src = generate_panel(sub)
    if "UI_SUBHEADER" in sub_src and ", 0," in sub_src and ", 1," in sub_src:
        print("ok: subheader widgets map to UI_SUBHEADER (op + part)")
    else:
        print("FAIL: subheader widgets did not map")
        failures += 1

    # ratio + semi params carry sorted landmark tables, and every emitted table is
    # referenced from DISP_TBL (no orphan tables). The ratio first entries pin the
    # 0.5 / 0.71 / 0.78 / 0.87 series; the semi ones pin integer-semitone detents.
    lms: PanelManifest = {
        "name": "lms",
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [
                            {"type": "param_row", "row": 1, "param": "op1.ratio"},
                            {"type": "param_row", "row": 2, "param": "penv.base"},
                        ],
                    }
                ]
            }
        },
        "global": [],
    }
    lm_ids = {"op1.ratio": 0, "penv.base": 1}
    lm_meta = {
        0: ("ratio", 32768, 1048576, "linear"),
        1: ("semi", -32768, 32767, "linear"),
    }
    lm_src = generate_panel(lms, lm_ids, lm_meta)
    ratio_ok = (
        "UI_DISP_RATIO, 0, 32768, 1048576, 1, 92, LM_" in lm_src
        and "32768, 46531, 51119, 57017, 65536" in lm_src
    )
    semi_ok = (
        "UI_DISP_SEMI, 0, -32768, 32767, 1, 25, LM_" in lm_src
        and "-32768" in lm_src
        and "2731" in lm_src
        and "32767" in lm_src
    )
    tables = re.findall(r"static const int32_t (LM_\d+)\[", lm_src)
    referenced = bool(tables) and all(lm_src.count(name) > 1 for name in tables)
    if ratio_ok and semi_ok and referenced:
        print("ok: ratio/semi params carry sorted landmark tables (no orphans)")
    else:
        print("FAIL: ratio/semi landmarks missing or orphaned")
        failures += 1

    # the operator/mute/part-relative tables are per-part (part-major), so the
    # runtime can index them by ui_selected_part (§13.3 item 33: the active part
    # must drive the editor + mutes). Part 0 = the unsuffixed id, part 1 = `.p1`.
    part_panel: PanelManifest = {
        "name": "part",
        "alg": "algorithm",
        "parts": 2,
        "operators": ["op1"],
        "mute": ["op1_mute"],
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [
                            {
                                "type": "param_row",
                                "row": 0,
                                "param": "op1.tl.level",
                                "text": "LEVEL",
                            },
                            {
                                "type": "param_row",
                                "row": 1,
                                "param": "level",
                                "part": True,
                                "text": "P LEVEL",
                            },
                        ],
                    }
                ]
            }
        },
        "global": [],
    }
    part_ids = {
        "algorithm": 0,
        "op1.tl.level": 1,
        "op1.tl.level.p0": 1,
        "op1.tl.level.p1": 7,
        "op1_mute": 2,
        "op1_mute.p0": 2,
        "op1_mute.p1": 8,
        "level": 3,
        "level.p0": 3,
        "level.p1": 9,
    }
    part_src = generate_panel(part_panel, part_ids)
    part_ok = (
        "OP_PARAM[2] = { 1, 7 }" in part_src
        and "MUTE_TBL[8] = { 2, 0xFFFF, 0xFFFF, 0xFFFF, 8," in part_src
        and "PART_PARAM[2] = { 3, 9 }" in part_src
    )
    if part_ok:
        print("ok: operator/mute/part-relative tables are per-part (part-major)")
    else:
        print("FAIL: per-part tables did not resolve part 0 then part 1")
        failures += 1

    # a `part: true` binding emits UI_BIND_PART_PARAM, and the algorithm's per-part
    # stride (`.p1` - `.p0`) is emitted into the ui_tables, so the header + the
    # ENC_ALGORITHM knob resolve the algorithm through the active part.
    alg_panel: PanelManifest = {
        "name": "alg",
        "alg": "algorithm",
        "parts": 2,
        "global": [
            {
                "source": "ENC_ALGORITHM",
                "target": "algorithm",
                "behavior": "relative",
                "part": True,
            }
        ],
        "contexts": {"home": {"pages": [{"id": "home", "widgets": []}]}},
    }
    alg_src = generate_panel(alg_panel, {"algorithm": 5, "algorithm.p1": 15})
    if "UI_BIND_PART_PARAM" in alg_src and ", 10, 2, " in alg_src:
        print("ok: part-relative bindings + the algorithm stride emit")
    else:
        print("FAIL: part-relative binding or algorithm stride missing")
        failures += 1

    print("panel tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
