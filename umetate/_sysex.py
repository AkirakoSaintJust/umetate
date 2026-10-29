# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The shared SysEx envelope (docs/roadmap.md §6.11.4): framing, the five commands,
CRC-16-CCITT, and the 7-bit packing of payloads.

```
F0 00 21 1D <model> <cmd> <ver> <payload…> <crc16-lo> <crc16-hi> F7
```

The CRC covers `<cmd>…<payload>` (the packed body, as transmitted); the receiver
checks it before unpacking. Responses echo the command with the high bit set;
`0x7F` is the unknown-command reply.
"""

from __future__ import annotations

from ._records import crc16

MANUFACTURER = b"\x00\x21\x1d"
START = 0xF0
END = 0xF7
VERSION = 1
RESPONSE = 0x80

CMD_IDENTITY = 0x01
CMD_PARAM_DUMP = 0x02
CMD_PART_DUMP = 0x03
CMD_MULTI_DUMP = 0x04
CMD_SETTINGS_DUMP = 0x05
CMD_UNKNOWN = 0x7F

_COMMANDS = (
    CMD_IDENTITY,
    CMD_PARAM_DUMP,
    CMD_PART_DUMP,
    CMD_MULTI_DUMP,
    CMD_SETTINGS_DUMP,
)


def known(cmd: int) -> bool:
    """Whether `cmd` (with or without the response bit) is a defined command."""
    return cmd & ~RESPONSE in _COMMANDS


def pack7(data: bytes) -> bytes:
    """7-bit-pack a payload: each group of 7 data bytes -> 7 low-7-bit bytes +
    one collected top-bits byte (every output byte is a MIDI data byte, <= 0x7F)."""
    out = bytearray()
    for i in range(0, len(data), 7):
        chunk = data[i : i + 7]
        top = 0
        for j, b in enumerate(chunk):
            out.append(b & 0x7F)
            top |= ((b >> 7) & 1) << j
        out.append(top)
    return bytes(out)


def unpack7(data: bytes, n: int) -> bytes:
    """Unpack exactly `n` original bytes from a 7-bit-packed stream."""
    out = bytearray()
    for i in range(0, len(data), 8):
        group = data[i : i + 8]
        for j in range(7):
            if len(out) == n:
                return bytes(out)
            if j < len(group) - 1:
                out.append((group[j] & 0x7F) | (((group[-1] >> j) & 1) << 7))
    return bytes(out)


def encode(model: int, cmd: int, payload: bytes, version: int = VERSION) -> bytes:
    """Frame a request/response into the full SysEx message bytes."""
    body = bytes([cmd, version]) + pack7(payload)
    return (
        bytes([START])
        + MANUFACTURER
        + bytes([model])
        + body
        + crc16(body).to_bytes(2, "little")
        + bytes([END])
    )


def decode(frame: bytes) -> tuple[int, int, int, bytes] | None:
    """Parse + CRC-check a frame -> `(model, cmd, version, packed payload)`; None
    when malformed (bad framing, truncated, or CRC mismatch)."""
    if (
        len(frame) < 10
        or frame[0] != START
        or frame[-1] != END
        or frame[1:4] != MANUFACTURER
    ):
        return None
    body = frame[5:-3]
    if crc16(body) != int.from_bytes(frame[-3:-1], "little"):
        return None
    return frame[4], body[0], body[1], body[2:]
