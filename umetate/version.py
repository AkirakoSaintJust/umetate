# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate version` — print the CLI version."""

from __future__ import annotations

import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    del argv
    print(__version__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
