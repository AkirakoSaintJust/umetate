# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate inspect`: read a `.fwsc` and report its identity, model, loader, and
integrity.

It wraps the inherited `firmware/tools/fm1_install.py` parsing, a strangler-fig
arrangement rather than a rewrite: `product_of`, `model_of`, `deinterleave`, and
`package_damage`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._installer import load_installer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate inspect", description=__doc__)
    parser.add_argument("package", help="the .fwsc to inspect")
    args = parser.parse_args(argv)

    fm1 = load_installer()
    try:
        raw = Path(args.package).read_bytes()
    except OSError as exc:
        print(f"inspect: cannot read {args.package}: {exc}", file=sys.stderr)
        return 1

    try:
        product = fm1.product_of(raw)
    except Exception as exc:  # InstallError ("too short", ...)
        print(f"inspect: {exc}", file=sys.stderr)
        return 2

    model = fm1.model_of(product)
    has_loader = bool(fm1.LOADER_MARK in raw)
    try:
        image, blocks = fm1.deinterleave(raw)
        damage = fm1.package_damage(image)
    except Exception as exc:
        print(f"inspect: {exc}", file=sys.stderr)
        return 2

    print(f"identity:  {product}")
    print(f"model:     {model}")
    print(f"loader:    {'present' if has_loader else 'absent'}")
    print(f"blocks:    {blocks}")
    print(f"integrity: {'ok' if damage is None else 'damaged: ' + str(damage)}")
    return 0 if damage is None else 1


if __name__ == "__main__":
    sys.exit(main())
