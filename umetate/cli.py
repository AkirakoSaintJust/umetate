# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The `umetate` CLI dispatcher (docs/roadmap.md §12.8).

One entry point, no import side effects. Each command is a module with
`main(argv) -> int` (or a named function for the `web:` pair).
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Sequence
from typing import cast

# command -> (one-line description, module name or "module:function")
COMMANDS: dict[str, tuple[str, str]] = {
    "quick-check": ("verify the environment per evidence layer", "quick_check"),
    "setup": ("install the toolchain + SDK, Rust + fm1-emu", "setup"),
    "build": ("generate + target compile + package -> .fwsc", "build"),
    "emu": ("run your firmware in the fm1-emu GUI", "emu"),
    "deep-check": ("run the host tests + the checks", "deep_check"),
    "inspect": ("read a .fwsc (identity/CRC/model)", "inspect"),
    "flash": ("write a .fwsc to a device (gated)", "flash"),
    "debrick": ("recovery write (mask-rom blocked)", "debrick"),
    "scaffold": ("generate a node/macro/patch skeleton", "scaffold"),
    "lib": ("list the shipped nodes + templates", "lib"),
    "lint": ("the C standing checks", "lint"),
    "fmt": ("clang-format the repo", "fmt"),
    "web-build": ("emscripten -> standalone dsp.wasm", "web:build_main"),
    "web-serve": ("loopback static server", "web:serve_main"),
    "status": ("the per-layer claim ledger from the roadmap", "status"),
    "evidence": ("validate an evidence matrix", "evidence"),
    "version": ("print the CLI version", "version"),
}


def _usage() -> None:
    width = max(len(name) for name in COMMANDS)
    print("usage: umetate COMMAND [ARGS]")
    print()
    print("commands:")
    for name, (desc, _) in COMMANDS.items():
        print(f"  {name:<{width}}  {desc}")


def _dispatch(name: str, argv: list[str]) -> int:
    _desc, module = COMMANDS[name]
    if ":" in module:
        mod_name, func_name = module.split(":", 1)
        mod = importlib.import_module(f"umetate.{mod_name}")
        return cast(Callable[[list[str]], int], getattr(mod, func_name))(argv)
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
