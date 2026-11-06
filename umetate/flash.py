# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate flash`: write a `.fwsc` to a device over USB-MIDI (docs §6.1 and §8).

It wraps the inherited `firmware/tools/fm1_install.py`, a strangler-fig
arrangement rather than a rewrite. The command is gated. `--device` is required,
the package is verified before any MIDI, and the installer's own confirmation
still applies. A wrong model exits 6.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from ._installer import load_installer
from ._schema import Installer

# §8 gates 4/5: the named recovery routes (docs/platform-facts.md §5.4).
_ROUTES = (
    "app-level USB rescue (OCT- at boot, or OCT- + OCT+ 5 s while running)",
    "update loader (ota-<identity>): an interrupted write resumes via `umetate flash`",
    "mask-ROM UBOOT (USB_KEY dongle; `umetate debrick mask-rom`)",
)


def _verify(fm1: Installer, path: Path) -> tuple[str, str] | None:
    """Verify a package's identity + CRC; return (product, model) or None."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        print(f"flash: cannot read {path}: {exc}", file=sys.stderr)
        return None
    try:
        product = fm1.product_of(raw)
        image, _blocks = fm1.deinterleave(raw)
        damage = fm1.package_damage(image)
    except Exception as exc:
        print(f"flash: not a package: {exc}", file=sys.stderr)
        return None
    if damage is not None:
        print(f"flash: damaged package: {damage}", file=sys.stderr)
        return None
    return product, fm1.model_of(product)


def flash(
    argv: list[str] | None = None,
    backend: object | None = None,
    out: TextIO = sys.stdout,
    ask: Callable[[str], bool] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="umetate flash", description=__doc__)
    parser.add_argument("package", help="the .fwsc to write")
    parser.add_argument("--port", metavar="NAME", help="MIDI port (part of its name)")
    parser.add_argument("--device", action="store_true", help="write to a device (§8)")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation")
    args = parser.parse_args(argv)

    if not args.device:
        print(
            "flash: refused, pass --device to write hardware (§8); a build, test or "
            "edit is never permission to write.",
            file=sys.stderr,
        )
        return 1

    fm1 = load_installer()
    path = Path(args.package)
    if not path.is_file():
        print(f"flash: {path} not found", file=sys.stderr)
        return 2
    verified = _verify(fm1, path)
    if verified is None:
        return 2
    product, model = verified
    print(f"flash: {product} ({model}) verified. Rollback: the stock .fwsc.", file=out)
    for route in _ROUTES:
        print(f"flash: recovery: {route}", file=out)

    install_argv = [str(path)]
    if args.port:
        install_argv += ["--port", str(args.port)]
    if args.yes:
        install_argv += ["--yes"]
    if ask is None:
        ask = fm1.ask_tty  # the interactive confirmation (§8 gate 6)
    return fm1.main(install_argv, backend=backend, out=out, ask=ask)


def main(argv: list[str] | None = None) -> int:
    return flash(argv)


if __name__ == "__main__":
    sys.exit(main())
