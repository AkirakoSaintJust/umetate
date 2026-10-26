# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""umetate — the toolkit package."""

from ._ir import GenError, NodeSpec, load_library
from .generate import generate

__version__ = "0.0.0"
__all__ = ["generate", "GenError", "NodeSpec", "load_library", "__version__"]
