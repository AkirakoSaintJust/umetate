# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The preset record formats + CRCs (docs/roadmap.md §6.11.4): the shared data
layer of the preset store, the SysEx envelope, and the CLI's export/import.

The byte layouts are fixed here (little-endian); both the host tools and the
device C store implement them. Every record is a self-validating unit — a `u8
version` (`0xFF` = empty slot), a body, and a **CRC-32** (poly `0xEDB88320` —
the platform's `crc32`) over version+body, so a corrupt record is skipped, never
the whole bank. The SysEx envelope's **CRC-16-CCITT** (poly `0x1021`, init
`0xFFFF`, no reflect) is here too.
"""

from __future__ import annotations

from typing import TypedDict

NAME_LEN = 16
RECORD_VERSION = 1
EMPTY = 0xFF
# Part patches and multi patches: 32 slots each. The slot area's measured ceiling
# is 16 372 B (store.h SLOT_MAX); the fourop-fm 317 B part record would fit 51
# slots, 32 keeps the classic count and headroom (roadmap §6.11.4).
SLOTS = 32


def crc32(data: bytes | bytearray) -> int:
    """CRC-32, poly 0xEDB88320, init 0xFFFFFFFF, reflected — the platform's crc32."""
    c = 0xFFFFFFFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
    return ~c & 0xFFFFFFFF


def crc16(data: bytes | bytearray) -> int:
    """CRC-16-CCITT, poly 0x1021, init 0xFFFF, no reflect — the SysEx envelope CRC."""
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


class PartPatch(TypedDict):
    """One timbre — the part's own param block (a part patch)."""

    name: str
    params: list[int]


class MultiPatch(TypedDict):
    """A composition — which part patch each part uses + routing/gain/timing."""

    name: str
    part_slot: list[int]  # per-part part-patch slot index (EMPTY = none)
    level: list[int]  # q15
    delay: list[int]  # ms
    channel: list[int]  # -1 = omni
    low: list[int]
    high: list[int]


class Settings(TypedDict):
    """The one global system record."""

    base_channel: int  # -1 = omni
    master_tune: int  # cents


def _name_bytes(name: str) -> bytes:
    """A name as NAME_LEN bytes (NUL-padded; ASCII, truncated at NAME_LEN-1)."""
    b = name.encode("ascii", "replace")[: NAME_LEN - 1]
    return b + b"\x00" * (NAME_LEN - len(b))


def _unpack_name(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def _u32(raw: bytes) -> int:
    return int.from_bytes(raw, "little")


def _i32(raw: bytes) -> int:
    return int.from_bytes(raw, "little", signed=True)


def _i32s(raw: bytes, off: int, n: int) -> list[int]:
    return [_i32(raw[off + 4 * i : off + 4 * i + 4]) for i in range(n)]


def _seal(body: bytes) -> bytes:
    return body + crc32(body).to_bytes(4, "little")


def part_patch_size(n_params: int) -> int:
    """The on-the-wire size of a part patch with `n_params` params."""
    return 1 + NAME_LEN + 4 * n_params + 4


def pack_part_patch(rec: PartPatch, n_params: int) -> bytes:
    """Encode a part patch (validated) into its on-the-wire bytes."""
    if len(rec["params"]) != n_params:
        raise ValueError(
            f"part patch: {len(rec['params'])} params, expected {n_params}"
        )
    body = bytes([RECORD_VERSION]) + _name_bytes(rec["name"])
    body += b"".join(v.to_bytes(4, "little", signed=True) for v in rec["params"])
    return _seal(body)


def unpack_part_patch(raw: bytes, n_params: int) -> PartPatch | None:
    """Decode + verify a part patch; None when empty, truncated, or corrupt."""
    if len(raw) != part_patch_size(n_params) or raw[0] == EMPTY:
        return None
    if crc32(raw[:-4]) != _u32(raw[-4:]):
        return None
    base = 1 + NAME_LEN
    return {
        "name": _unpack_name(raw[1:base]),
        "params": _i32s(raw, base, n_params),
    }


def multi_patch_size(n_parts: int) -> int:
    """The on-the-wire size of a multi patch with `n_parts` parts."""
    return 1 + NAME_LEN + n_parts + 5 * n_parts * 4 + 4


def pack_multi_patch(rec: MultiPatch, n_parts: int) -> bytes:
    """Encode a multi patch (validated) into its on-the-wire bytes."""
    if (
        len(rec["part_slot"]) != n_parts
        or len(rec["level"]) != n_parts
        or len(rec["delay"]) != n_parts
        or len(rec["channel"]) != n_parts
        or len(rec["low"]) != n_parts
        or len(rec["high"]) != n_parts
    ):
        raise ValueError(f"multi patch: expected {n_parts} entries per field")
    body = bytes([RECORD_VERSION]) + _name_bytes(rec["name"]) + bytes(rec["part_slot"])
    for values in (rec["level"], rec["delay"], rec["channel"], rec["low"], rec["high"]):
        body += b"".join(v.to_bytes(4, "little", signed=True) for v in values)
    return _seal(body)


def unpack_multi_patch(raw: bytes, n_parts: int) -> MultiPatch | None:
    """Decode + verify a multi patch; None when empty, truncated, or corrupt."""
    if len(raw) != multi_patch_size(n_parts) or raw[0] == EMPTY:
        return None
    if crc32(raw[:-4]) != _u32(raw[-4:]):
        return None
    base = 1 + NAME_LEN
    part_slot = list(raw[base : base + n_parts])
    off = base + n_parts
    level = _i32s(raw, off, n_parts)
    off += 4 * n_parts
    delay = _i32s(raw, off, n_parts)
    off += 4 * n_parts
    channel = _i32s(raw, off, n_parts)
    off += 4 * n_parts
    low = _i32s(raw, off, n_parts)
    off += 4 * n_parts
    high = _i32s(raw, off, n_parts)
    return {
        "name": _unpack_name(raw[1:base]),
        "part_slot": part_slot,
        "level": level,
        "delay": delay,
        "channel": channel,
        "low": low,
        "high": high,
    }


def settings_size() -> int:
    """The on-the-wire size of the settings record."""
    return 1 + 4 + 4 + 4


def empty_part_patch(n_params: int) -> bytes:
    """An empty part-patch slot on the wire (version 0xFF, zeroed body, valid CRC)."""
    return _seal(bytes([EMPTY]) + b"\x00" * (NAME_LEN + 4 * n_params))


def empty_multi_patch(n_parts: int) -> bytes:
    """An empty multi-patch slot on the wire (version 0xFF, zeroed body, valid CRC)."""
    return _seal(bytes([EMPTY]) + b"\x00" * (NAME_LEN + n_parts + 5 * n_parts * 4))


def pack_settings(rec: Settings) -> bytes:
    """Encode the settings record into its on-the-wire bytes."""
    body = bytes([RECORD_VERSION])
    body += rec["base_channel"].to_bytes(4, "little", signed=True)
    body += rec["master_tune"].to_bytes(4, "little", signed=True)
    return _seal(body)


def unpack_settings(raw: bytes) -> Settings | None:
    """Decode + verify the settings record; None when empty, truncated, or corrupt."""
    if len(raw) != settings_size() or raw[0] == EMPTY:
        return None
    if crc32(raw[:-4]) != _u32(raw[-4:]):
        return None
    return {"base_channel": _i32(raw[1:5]), "master_tune": _i32(raw[5:9])}
