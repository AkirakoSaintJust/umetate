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
from typing import TypeGuard

_Main = Callable[[list[str]], int]

# command -> (one-line description, module name or "module:function")
COMMANDS: dict[str, tuple[str, str]] = {
    "quick-check": ("check the environment for each evidence layer", "quick_check"),
    "setup": ("install the toolchain, SDK, Rust, and fm1-emu", "setup"),
    "build": ("generate, compile for the target, and package the .fwsc", "build"),
    "emu": ("run the firmware in the fm1-emu GUI", "emu"),
    "deep-check": ("run the host tests and the gates", "deep_check"),
    "inspect": ("read a .fwsc and report its identity, CRC, and model", "inspect"),
    "flash": ("write a .fwsc to a device, after the gates", "flash"),
    "debrick": ("recover a bricked unit, with the mask-ROM path blocked", "debrick"),
    "scaffold": (
        "generate a node, macro, patch, or synth skeleton",
        "scaffold",
    ),
    "lib": ("list the shipped nodes and templates", "lib"),
    "preset": ("export or import the preset bank as SysEx", "preset"),
    "opm": ("convert an OPM text bank to a Type P.fm1 bank", "opm"),
    "interview": ("run the design interview", "interview"),
    "publish": ("assemble a distributable firmware repo", "publish"),
    "plugin-generate": (
        "render a synth project's plugin sources",
        "plugin_cli:generate_main",
    ),
    "plugin-build": ("build and test a plugin project", "plugin_cli:build_main"),
    "plugin-check": (
        "check generated plugin sources and tests",
        "plugin_cli:check_main",
    ),
    "budget": ("measure the polyphony budget", "budget"),
    "theme": ("check or generate a WCAG-verified palette", "theme"),
    "tokens": ("check the UI tokens and hard-coded values", "tokens"),
    "font-atlas": ("rebuild the mockup's firmware font", "font_atlas"),
    "lint": ("run the C standing checks", "lint"),
    "fmt": ("format the repo with clang-format", "fmt"),
    "web-build": ("build the FM-1 emulator with Emscripten", "web:build_main"),
    "web-serve": ("serve the emulator on loopback", "web:serve_main"),
    "status": ("show the per-layer status ledger", "status"),
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


def _is_main(fn: object) -> TypeGuard[_Main]:
    return callable(fn)


def _entry(name: str) -> _Main:
    _desc, module = COMMANDS[name]
    if ":" in module:
        mod_name, func_name = module.split(":", 1)
        fn: object = getattr(importlib.import_module(f"umetate.{mod_name}"), func_name)
    else:
        fn = importlib.import_module(f"umetate.{module}").main
    if not _is_main(fn):
        raise RuntimeError(f"umetate: {name!r} entry is not callable")
    return fn


def _dispatch(name: str, argv: list[str]) -> int:
    return _entry(name)(argv)


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
