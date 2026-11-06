# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""umetate, the toolkit package."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("umetate")
except PackageNotFoundError:  # running from a raw checkout, not installed
    __version__ = "0.0.0"

__all__ = ["__version__"]
