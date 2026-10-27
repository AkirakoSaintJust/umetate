# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate scaffold` — generate a node/macro/patch skeleton (§12.7.4).

`--template T` copies a shipped example (e.g. `pocket-drone`) instead of the empty
skeleton. A generated `patch` is verified to build (generate + host compile).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .generate import generate

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = _ROOT / "examples"
_FW = _ROOT / "firmware"

_NODE_C = """/* TODO: the per-sample body (${in.*} ${out.*} ${state.*} ${param.*}). */
int32_t ${out.audio} = ${in.in};
"""


def _minimal_patch(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "voices": 4,
        "voice": {
            "nodes": [
                {"id": "ph", "type": "phasor"},
                {"id": "osc", "type": "osc"},
                {"id": "env", "type": "env"},
                {"id": "vca", "type": "vca"},
            ],
            "wires": [
                {"from": "ph.phase", "to": "osc.phase"},
                {"from": "osc.audio", "to": "vca.audio"},
                {"from": "env.cv", "to": "vca.cv"},
            ],
            "voice_out": "vca.audio",
        },
        "global": {"nodes": [], "wires": []},
    }


def _minimal_panel(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "home": "home",
        "contexts": {
            "home": {
                "pages": [
                    {
                        "id": "home",
                        "widgets": [{"type": "label", "row": 1, "text": name}],
                    }
                ]
            }
        },
    }


def _write(directory: Path, name: str, data: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _builds(patch: dict[str, Any]) -> bool:
    """Does the patch generate + compile on the host?"""
    src = generate(patch)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "dsp.c").write_text(src, encoding="utf-8")
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-I",
                str(_FW / "hal"),
                "-I",
                str(_FW / "gen"),
                "-c",
                "-o",
                str(d / "dsp.o"),
                str(d / "dsp.c"),
            ],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0


def _node(name: str, out: Path) -> int:
    _write(
        out,
        "node.json",
        {
            "name": name,
            "summary": "",
            "ins": {"in": "audio"},
            "outs": {"audio": "audio"},
            "params": {},
            "state": {},
        },
    )
    (out / "node.c").write_text(_NODE_C, encoding="utf-8")
    print(f"scaffolded node {out / 'node.json'} (+ node.c)")
    return 0


def _macro(name: str, out: Path) -> int:
    _write(
        out,
        "macro.json",
        {
            "name": name,
            "ins": {},
            "outs": {},
            "params": {},
            "nodes": [],
            "wires": [],
        },
    )
    print(f"scaffolded macro {out / 'macro.json'}")
    return 0


def _patch(name: str, out: Path, template: str | None) -> int:
    if template:
        src = _EXAMPLES / template
        if not (src / "patch.json").exists():
            print(
                f"scaffold: no template {template!r} (looked in {src})",
                file=sys.stderr,
            )
            return 2
        patch = json.loads((src / "patch.json").read_text(encoding="utf-8"))
        panel = json.loads((src / "panel.json").read_text(encoding="utf-8"))
        patch["name"] = name
        panel["name"] = name
    else:
        patch = _minimal_patch(name)
        panel = _minimal_panel(name)

    _write(out, "patch.json", patch)
    _write(out, "panel.json", panel)
    if _builds(patch):
        print(f"scaffolded patch {out / 'patch.json'} (+ panel.json); it builds")
        return 0
    print("scaffold: the generated patch does not build", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate scaffold", description=__doc__)
    parser.add_argument("kind", choices=("node", "macro", "patch"))
    parser.add_argument("--name", required=True, help="the node/macro/patch name")
    parser.add_argument("--template", help="a shipped example to copy (patch only)")
    parser.add_argument("--out", type=Path, help="output dir (default: ./<name>)")
    args = parser.parse_args(argv)

    out = args.out or Path(args.name)
    if args.kind == "node":
        return _node(args.name, out)
    if args.kind == "macro":
        return _macro(args.name, out)
    return _patch(args.name, out, args.template)


if __name__ == "__main__":
    sys.exit(main())
