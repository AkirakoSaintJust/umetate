# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The evidence/status vocabulary (docs/platform-facts.md §5.5), one place.

Also `umetate evidence`: validate an evidence matrix (per-layer status, §12.8).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any


class Status(StrEnum):
    """A claim's status; a lower layer never proves a higher one."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not-applicable"
    NOT_RUN = "not-run"


class Layer(StrEnum):
    """The evidence layers, lowest to highest."""

    SOURCE = "source"
    HOST = "host"
    BROWSER = "browser"
    TARGET = "target"
    EMULATOR = "emulator"
    TIMING = "timing"
    DEVICE = "device"
    RELEASE = "release"


def validate(matrix: Mapping[str, Any]) -> list[str]:
    """Validate an evidence matrix (`{"layers": [{"layer", "status", "detail"}]}`).

    Returns the list of errors (empty = valid). `blocked`/`not-run` are never `pass`.
    """
    layers = matrix.get("layers")
    if not isinstance(layers, list):
        return ["'layers' must be a list"]
    errors: list[str] = []
    seen: set[str] = set()
    for i, entry in enumerate(layers):
        if not isinstance(entry, dict):
            errors.append(f"layers[{i}]: not an object")
            continue
        try:
            layer = Layer(str(entry.get("layer")))
        except ValueError:
            errors.append(f"layers[{i}]: unknown layer {entry.get('layer')!r}")
            continue
        if layer.value in seen:
            errors.append(f"layers[{i}]: duplicate layer {layer.value!r}")
        seen.add(layer.value)
        try:
            Status(str(entry.get("status")))
        except ValueError:
            errors.append(f"layers[{i}]: unknown status {entry.get('status')!r}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate evidence", description=__doc__)
    parser.add_argument("matrix", type=Path, help="an evidence matrix (.json)")
    parser.add_argument(
        "--strict", action="store_true", help="require every §5.5 layer"
    )
    args = parser.parse_args(argv)

    try:
        matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"evidence: cannot read {args.matrix}: {exc}", file=sys.stderr)
        return 1

    errors = validate(matrix)
    if args.strict:
        present = {
            e.get("layer") for e in matrix.get("layers", []) if isinstance(e, dict)
        }
        for layer in Layer:
            if layer.value not in present:
                errors.append(f"missing layer {layer.value!r}")

    if errors:
        for error in errors:
            print(f"evidence: {error}", file=sys.stderr)
        return 1
    print(f"evidence: {args.matrix} valid ({len(matrix.get('layers', []))} layers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
