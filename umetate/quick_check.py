# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate quick-check` — a fast, read-only presence/version probe (§12.8).

Reports each §5.5 layer; a missing toolchain is `blocked`, not `fail`. The deep
verification (host tests + `_checks/`) is `deep-check`, not here. The full container
probe (`runner.probe()`) lands with the runner in P3-2.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import runner
from .evidence import Layer, Status

_ROOT = Path(__file__).resolve().parents[1]


def _probe() -> list[tuple[Layer, Status, str]]:
    out: list[tuple[Layer, Status, str]] = []

    # ---- source ----
    if shutil.which("git"):
        rev = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
        if rev.returncode:
            out.append((Layer.SOURCE, Status.FAIL, "not a git repository"))
        else:
            dirty = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True
            ).stdout.strip()
            out.append(
                (
                    Layer.SOURCE,
                    Status.FAIL if dirty else Status.PASS,
                    "working tree dirty" if dirty else "clean git repository",
                )
            )
    else:
        out.append((Layer.SOURCE, Status.BLOCKED, "git not found"))

    missing = [
        name
        for name in ("params", "node", "patch", "panel")
        if not (_ROOT / "templates" / "scaffold" / f"{name}.schema.json").exists()
    ]
    out.append(
        (
            Layer.SOURCE,
            Status.FAIL if missing else Status.PASS,
            f"missing schemas: {', '.join(missing)}" if missing else "schemas present",
        )
    )

    # ---- host ----
    tools = ("cc", "cmake", "ninja", "python3", "node", "docker", "emcc")
    present = [t for t in tools if shutil.which(t)]
    out.append(
        (
            Layer.HOST,
            Status.PASS if len(present) == len(tools) else Status.BLOCKED,
            f"present: {', '.join(present)}" if present else "no host tools found",
        )
    )

    # ---- everything above host is not probe-able without the toolchain/device ----
    out.append((Layer.BROWSER, Status.BLOCKED, "emscripten wasm (P4-1)"))
    out.append((Layer.TARGET, *_target_layer()))
    out.append((Layer.EMULATOR, Status.BLOCKED, "fm1-emu (P4-2)"))
    out.append((Layer.TIMING, Status.NOT_RUN, "physical, device-only"))
    out.append((Layer.DEVICE, Status.BLOCKED, "no device connected"))
    out.append((Layer.RELEASE, Status.NOT_RUN, "release-only"))
    return out


def _target_layer() -> tuple[Status, str]:
    """The TARGET presence probe: env var, the volume, or the `.jieli/` checkout."""
    if os.environ.get("JIELI_TOOLCHAIN"):
        return Status.PASS, "$JIELI_TOOLCHAIN set"
    if runner.probe().toolchain_volume:
        return Status.PASS, "umetate-target volume present (toolchain + SDK)"
    if (_ROOT / ".jieli" / "jieli-linux-toolchains-20260730.1").is_dir():
        return Status.PASS, "local .jieli/ toolchain checkout"
    return Status.BLOCKED, "JieLi toolchain not set up (`umetate setup`)"


def _render(results: list[tuple[Layer, Status, str]]) -> str:
    width = max(len(layer.value) for layer, _, _ in results)
    lines = [
        f"{layer.value:<{width}}  {status.value:<14}  {detail}"
        for layer, status, detail in results
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate quick-check", description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict", action="store_true", help="exit non-zero on a non-device `blocked`"
    )
    args = parser.parse_args(argv)

    results = _probe()
    if args.json:
        payload = [
            {"layer": layer.value, "status": status.value, "detail": detail}
            for layer, status, detail in results
        ]
        print(json.dumps({"layers": payload}, indent=2))
    else:
        print(_render(results))

    non_device_blocked = any(
        status is Status.BLOCKED and layer is not Layer.DEVICE
        for layer, status, _ in results
    )
    any_fail = any(status is Status.FAIL for _, status, _ in results)
    return 1 if (any_fail or (args.strict and non_device_blocked)) else 0


if __name__ == "__main__":
    sys.exit(main())
