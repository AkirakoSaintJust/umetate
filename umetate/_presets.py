# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The preset bank ↔ SysEx export/import (docs/roadmap.md §6.11.4): the host-side
half of the preset store — a 64+64-slot bank, exchanged as a sequence of
part-patch / multi-patch dump frames (the `.syx` stream). The device store (F4d)
uses the same records.

A dump frame's payload is `slot byte + record` (7-bit packed by the envelope).
Export emits every slot in order (empty slots as version-0xFF records); import
requires the same strict sequence — a wrong-model, corrupt, or truncated stream
parses to None (a rejected import, never a partial bank).
"""

from __future__ import annotations

from typing import TypedDict

from ._records import (
    SLOTS,
    MultiPatch,
    PartPatch,
    empty_multi_patch,
    empty_part_patch,
    multi_patch_size,
    pack_multi_patch,
    pack_part_patch,
    part_patch_size,
    unpack_multi_patch,
    unpack_part_patch,
)
from ._schema import SysexLayout
from ._sysex import (
    CMD_MULTI_DUMP,
    CMD_PART_DUMP,
    decode,
    encode,
    unpack7,
)


class Bank(TypedDict):
    """The host-side preset bank: 64 part patches + 64 multi patches (None = empty)."""

    part_patches: list[PartPatch | None]
    multi_patches: list[MultiPatch | None]


def _packed_len(n: int) -> int:
    """The 7-bit-packed length of `n` payload bytes (7 data bytes -> 8 MIDI bytes)."""
    return n + (n + 6) // 7


def _frame_len(n_payload: int) -> int:
    """The full frame length for a payload of `n_payload` unpacked bytes."""
    # F0 + manuf(3) + model + cmd + ver + crc(2) + F7
    return 10 + _packed_len(n_payload)


def export_bank(layout: SysexLayout, bank: Bank, model: int) -> bytes:
    """The bank as a `.syx` stream: a part-patch dump frame per slot (0..63) in
    order, then a multi-patch dump frame per slot in order."""
    n_params, n_parts = layout["n_params"], layout["n_parts"]
    frames = bytearray()
    for slot in range(SLOTS):
        part_rec = bank["part_patches"][slot]
        payload = (
            pack_part_patch(part_rec, n_params)
            if part_rec is not None
            else empty_part_patch(n_params)
        )
        frames += encode(model, CMD_PART_DUMP, bytes([slot]) + payload)
    for slot in range(SLOTS):
        multi_rec = bank["multi_patches"][slot]
        payload = (
            pack_multi_patch(multi_rec, n_parts)
            if multi_rec is not None
            else empty_multi_patch(n_parts)
        )
        frames += encode(model, CMD_MULTI_DUMP, bytes([slot]) + payload)
    return bytes(frames)


def import_bank(data: bytes, layout: SysexLayout, model: int) -> Bank | None:
    """Parse a `.syx` stream back into a bank; None on any bad frame, record, slot
    order, model mismatch, or trailing garbage."""
    n_params, n_parts = layout["n_params"], layout["n_parts"]
    part_len = _frame_len(1 + part_patch_size(n_params))
    multi_len = _frame_len(1 + multi_patch_size(n_parts))
    total = SLOTS * (part_len + multi_len)
    if len(data) != total:
        return None

    part: list[PartPatch | None] = [None] * SLOTS
    multi: list[MultiPatch | None] = [None] * SLOTS
    i = 0
    for slot in range(SLOTS):
        got = decode(data[i : i + part_len])
        if got is None or got[0] != model or got[1] != CMD_PART_DUMP:
            return None
        raw = unpack7(got[3], 1 + part_patch_size(n_params))
        if raw[0] != slot:
            return None
        part_rec = unpack_part_patch(raw[1:], n_params)
        if part_rec is not None:
            part[slot] = part_rec
        i += part_len
    for slot in range(SLOTS):
        got = decode(data[i : i + multi_len])
        if got is None or got[0] != model or got[1] != CMD_MULTI_DUMP:
            return None
        raw = unpack7(got[3], 1 + multi_patch_size(n_parts))
        if raw[0] != slot:
            return None
        multi_rec = unpack_multi_patch(raw[1:], n_parts)
        if multi_rec is not None:
            multi[slot] = multi_rec
        i += multi_len
    return {"part_patches": part, "multi_patches": multi}
