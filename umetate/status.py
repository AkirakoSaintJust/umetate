# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate status`: parse the roadmap's per-layer claim ledger (roadmap §12.8).

It reads the phase, step, and exit headers with a tolerant convention. A header
that does not match is skipped rather than treated as an error. The status token
after the header is one of `done`, `blocked`, `in progress`, or `met`, optionally
per layer (`done (host), blocked (target/device)`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_ROADMAP = Path(__file__).resolve().parents[1] / "docs" / "roadmap.md"

_PHASE = re.compile(r"^### Phase (\d+)\s*(?:—|,)\s*(.*?) \(P\d+\)\s*(?:—|,)\s*(.*)$")
_STEP = re.compile(r"^\*\*(P\d+-\d+)\s*(?:—|,)\s*(.*?)\.\*\*\s*(?:—|,)\s*(.*)$")
_EXIT = re.compile(r"^\*\*Exit (P\d+):\*\* (.*)$")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")

_LAYERS = {
    "source",
    "host",
    "browser",
    "target",
    "emulator",
    "timing",
    "device",
    "release",
}


@dataclass
class Claim:
    id: str
    name: str
    status: str
    layers: dict[str, str]  # layer -> status (empty key = whole-claim)


def _status(text: str) -> str:
    m = _BOLD.search(text)
    return m.group(1).strip() if m else ""


def _split_layers(status: str) -> dict[str, str]:
    """Split `done (host), blocked (target/device)` into a layer -> status map."""
    out: dict[str, str] = {}
    for token in status.split(","):
        token = token.strip()
        if "(" in token and token.endswith(")"):
            word, rest = token.rsplit("(", 1)
            rest = rest[:-1].strip()
            parts = [p.strip() for p in rest.split("/")]
            if parts and all(p in _LAYERS for p in parts):
                for p in parts:
                    out[p] = word.strip()
                continue
        out.setdefault("", token)
    return out


def _parse(text: str) -> tuple[list[Claim], list[Claim], list[Claim]]:
    phases: list[Claim] = []
    steps: list[Claim] = []
    exits: list[Claim] = []
    for line in text.splitlines():
        m = _PHASE.match(line)
        if m:
            status = _status(m.group(3))
            phases.append(
                Claim(m.group(1), m.group(2).strip(), status, _split_layers(status))
            )
            continue
        m = _STEP.match(line)
        if m:
            status = _status(m.group(3))
            steps.append(
                Claim(m.group(1), m.group(2).strip(), status, _split_layers(status))
            )
            continue
        m = _EXIT.match(line)
        if m:
            status = _status(m.group(2))
            exits.append(Claim(m.group(1), "exit", status, _split_layers(status)))
    return phases, steps, exits


def _render(phases: list[Claim], steps: list[Claim], exits: list[Claim]) -> str:
    lines: list[str] = []
    for p in phases:
        lines.append(f"Phase {p.id} — {p.name}: {p.status or '?'}")
    for e in exits:
        lines.append(f"Exit {e.id}: {e.status or '?'}")
    for s in steps:
        lines.append(f"  {s.id} — {s.name}: {s.status or '?'}")
    return "\n".join(lines)


def _to_json(phases: list[Claim], steps: list[Claim], exits: list[Claim]) -> str:
    def one(c: Claim) -> dict[str, str | dict[str, str]]:
        return {"id": c.id, "name": c.name, "status": c.status, "layers": c.layers}

    return json.dumps(
        {
            "phases": [one(p) for p in phases],
            "exits": [one(e) for e in exits],
            "steps": [one(s) for s in steps],
        },
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate status", description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--steps", action="store_true", help="include per-step detail")
    args = parser.parse_args(argv)

    if not _ROADMAP.exists():
        print(f"status: {_ROADMAP} not found", file=sys.stderr)
        return 1
    phases, steps, exits = _parse(_ROADMAP.read_text(encoding="utf-8"))
    if args.json:
        print(_to_json(phases, steps if args.steps else [], exits))
    else:
        print(_render(phases, steps if args.steps else [], exits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
