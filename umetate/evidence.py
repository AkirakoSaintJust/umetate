# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The evidence and status vocabulary (docs/platform-facts.md §5.5), in one
place.

`umetate evidence` validates an evidence matrix with a per-layer status (§12.8).
"""

from __future__ import annotations

import argparse
import json
import sys
from enum import StrEnum
from pathlib import Path
from typing import cast

from ._schema import as_evidence


class Status(StrEnum):
    """The status of a claimed feature. A lower layer never proves a higher one."""

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


def validate(matrix: object, *, strict: bool = False) -> list[str]:
    """Validate an untrusted evidence matrix (`{"layers": [{"layer", "status"}]}`).

    Returns the list of errors (empty = valid); `strict` also requires every layer.
    `blocked`/`not-run` are never `pass`.
    """
    if not isinstance(matrix, dict):
        return ["not an object"]
    obj = cast(dict[str, object], matrix)
    raw_layers = obj.get("layers")
    if not isinstance(raw_layers, list):
        return ["'layers' must be a list"]
    layers = cast(list[object], raw_layers)
    errors: list[str] = []
    seen: set[str] = set()
    present: set[object] = set()
    for i, entry in enumerate(layers):
        if not isinstance(entry, dict):
            errors.append(f"layers[{i}]: not an object")
            continue
        e = cast(dict[str, object], entry)
        present.add(e.get("layer"))
        try:
            layer = Layer(str(e.get("layer")))
        except ValueError:
            errors.append(f"layers[{i}]: unknown layer {e.get('layer')!r}")
            continue
        if layer.value in seen:
            errors.append(f"layers[{i}]: duplicate layer {layer.value!r}")
        seen.add(layer.value)
        try:
            Status(str(e.get("status")))
        except ValueError:
            errors.append(f"layers[{i}]: unknown status {e.get('status')!r}")
    if strict:
        for layer in Layer:
            if layer.value not in present:
                errors.append(f"missing layer {layer.value!r}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate evidence", description=__doc__)
    parser.add_argument("matrix", type=Path, help="an evidence matrix (.json)")
    parser.add_argument(
        "--strict", action="store_true", help="require every §5.5 layer"
    )
    args = parser.parse_args(argv)

    matrix_path: Path = args.matrix
    strict: bool = args.strict
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"evidence: cannot read {matrix_path}: {exc}", file=sys.stderr)
        return 1

    errors = validate(matrix, strict=strict)
    if errors:
        for error in errors:
            print(f"evidence: {error}", file=sys.stderr)
        return 1
    print(
        f"evidence: {matrix_path} valid ({len(as_evidence(matrix)['layers'])} layers)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
