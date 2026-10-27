# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The evidence/status vocabulary (docs/platform-facts.md §5.5), one place."""

from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    """A claim's status; a lower layer never proves a higher one."""

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
