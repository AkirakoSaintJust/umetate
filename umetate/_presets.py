# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The preset bank ↔ SysEx export/import (docs/roadmap.md §6.11.4): the host-side
half of the preset store — a SLOTS+SLOTS-slot bank (32 each; the slot area's
measured ceiling), exchanged as a sequence of part-patch / multi-patch dump
frames (the `.syx` stream). The device store (F4d) uses the same records.

A dump frame's payload is `slot byte + record` (7-bit packed by the envelope).
Export emits every slot in order (empty slots as version-0xFF records); import
requires the same strict sequence — a wrong-model, corrupt, or truncated stream
parses to None (a rejected import, never a partial bank).
"""

from __future__ import annotations

from typing import TypedDict, cast

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
    """The host-side preset bank: SLOTS part patches + SLOTS multi patches
    (None entries = empty)."""

    part_patches: list[PartPatch | None]
    multi_patches: list[MultiPatch | None]


def as_bank(raw: object) -> Bank:
    """Narrow a JSON object to a Bank (SLOTS slots each; None entries = empty)."""
    if not isinstance(raw, dict):
        raise ValueError("bank: expected a JSON object")
    obj = cast(dict[str, object], raw)
    part = obj.get("part_patches")
    multi = obj.get("multi_patches")
    if not isinstance(part, list) or not isinstance(multi, list):
        raise ValueError("bank: 'part_patches'/'multi_patches' must be lists")
    part_list = cast(list[object], part)
    multi_list = cast(list[object], multi)
    if len(part_list) != SLOTS or len(multi_list) != SLOTS:
        raise ValueError(f"bank: each list must have {SLOTS} entries")

    def _part(r: object) -> PartPatch | None:
        if r is None:
            return None
        if not isinstance(r, dict):
            raise ValueError("bank: bad part-patch entry")
        entry = cast(dict[str, object], r)
        name = entry.get("name")
        params = entry.get("params")
        if not isinstance(name, str) or not isinstance(params, list):
            raise ValueError("bank: bad part-patch entry")
        values = cast(list[object], params)
        if not all(isinstance(v, int) for v in values):
            raise ValueError("bank: bad part-patch entry")
        return {"name": name, "params": cast(list[int], values)}

    def _multi(r: object) -> MultiPatch | None:
        if r is None:
            return None
        if not isinstance(r, dict):
            raise ValueError("bank: bad multi-patch entry")
        entry = cast(dict[str, object], r)
        name = entry.get("name")
        if not isinstance(name, str):
            raise ValueError("bank: bad multi-patch entry")
        fields: dict[str, list[int]] = {}
        for key in ("part_slot", "level", "delay", "channel", "low", "high"):
            vals = entry.get(key)
            if not isinstance(vals, list):
                raise ValueError(f"bank: bad multi-patch '{key}'")
            values = cast(list[object], vals)
            if not all(isinstance(v, int) for v in values):
                raise ValueError(f"bank: bad multi-patch '{key}'")
            fields[key] = cast(list[int], values)
        return {
            "name": name,
            "part_slot": fields["part_slot"],
            "level": fields["level"],
            "delay": fields["delay"],
            "channel": fields["channel"],
            "low": fields["low"],
            "high": fields["high"],
        }

    return {
        "part_patches": [_part(r) for r in part_list],
        "multi_patches": [_multi(r) for r in multi_list],
    }


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
