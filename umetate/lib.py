# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate lib` — list the shipped nodes + templates (local only, no registry)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MODULES = _ROOT / "modules"
_EXAMPLES = _ROOT / "examples"


def _list_nodes() -> list[str]:
    lines: list[str] = []
    for manifest in sorted(_MODULES.glob("*/node.json")):
        name = manifest.parent.name
        summary = json.loads(manifest.read_text(encoding="utf-8")).get("summary", "")
        lines.append(f"node     {name:<12} {summary}")
    return lines


def _list_templates() -> list[str]:
    lines: list[str] = []
    for template in sorted(p for p in _EXAMPLES.glob("*/") if p.is_dir()):
        lines.append(f"template {template.name}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate lib", description=__doc__)
    parser.add_argument("action", choices=("list",), default="list", nargs="?")
    args = parser.parse_args(argv)

    if args.action == "list":
        for line in _list_nodes():
            print(line)
        for line in _list_templates():
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
