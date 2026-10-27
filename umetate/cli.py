# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The `umetate` CLI dispatcher (docs/roadmap.md §12.8).

One entry point, no import side effects. Each command is a module with
`main(argv) -> int`; the commands not yet implemented are registered here (so
`umetate --help` lists them) and report the phase they land in.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Sequence
from typing import cast

# command -> (one-line description, module name or None, phase)
COMMANDS: dict[str, tuple[str, str | None, str]] = {
    "quick-check": ("verify the environment per evidence layer", "quick_check", "P3-1"),
    "setup": ("install the JieLi toolchain + SDK into the Docker volume", None, "P3-2"),
    "build": ("generate + target compile + package -> .fwsc", None, "P3-2"),
    "deep-check": ("run the host tests + the checks", None, "P3-2"),
    "inspect": ("read a .fwsc (identity/CRC/model)", None, "P3-2"),
    "flash": ("write a .fwsc to a device (gated)", None, "P3-4"),
    "debrick": ("recovery write (mask-rom blocked)", None, "P3-4"),
    "scaffold": ("generate a node/macro/patch skeleton", None, "P3-3"),
    "lib": ("list the shipped nodes + templates", None, "P3-3"),
    "lint": ("the C standing checks", None, "P3-3"),
    "fmt": ("clang-format the repo", None, "P3-3"),
    "web-build": ("emscripten -> dsp.wasm + a minimal harness", None, "P3-5"),
    "web-serve": ("loopback static server", None, "P3-5"),
    "status": ("the per-layer claim ledger from the roadmap", "status", "P3-1"),
    "evidence": ("validate an evidence matrix", None, "P3-5"),
    "version": ("print the CLI version", "version", "P3-1"),
}


def _usage() -> None:
    width = max(len(name) for name in COMMANDS)
    print("usage: umetate COMMAND [ARGS]")
    print()
    print("commands:")
    for name, (desc, _, _) in COMMANDS.items():
        print(f"  {name:<{width}}  {desc}")


def _dispatch(name: str, argv: list[str]) -> int:
    desc, module, phase = COMMANDS[name]
    if module is None:
        print(f"umetate {name}: not implemented yet ({phase})", file=sys.stderr)
        return 1
    mod = importlib.import_module(f"umetate.{module}")
    return cast(Callable[[list[str]], int], mod.main)(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in ("-h", "--help"):
        _usage()
        return 0
    if args[0] == "help":
        if len(args) == 1:
            _usage()
            return 0
        return _dispatch(args[1], ["--help"])
    if args[0] not in COMMANDS:
        print(f"umetate: unknown command {args[0]!r}", file=sys.stderr)
        _usage()
        return 2
    return _dispatch(args[0], args[1:])


if __name__ == "__main__":
    sys.exit(main())
