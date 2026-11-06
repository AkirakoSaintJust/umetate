# Persistence, presets, and SysEx

The stored patch and part structure, the SysEx message format, and the parameter
semantics are design deliverables rather than implementation details, so decide
them in the design interview and write them down before authoring. The shipped
framework (`firmware/src/`: `presets.c`, `synth_sysex`, `synth_runtime`) implements
them, so the project only declares its params and their ranges.

## Parameter semantics (decide first)

Every parameter is defined with its full meaning and its bounds. For each
parameter in the manifest, state:

- the flattened `<instance>.<param>` target (the generated `set_param` id order).
- min, max, and default, in the parameter's own units.
- the curve (linear or log) the panel and CC use to step it.
- the unit and what it means to a player (a Q15 fraction, a 0..99 level, a ratio,
  a rate in hertz, a level in semitones).
- the rate (sample or block) and whether it is modulatable.

A parameter without a unit and a meaning is a bug waiting for a player to find it,
because the manifest is the only reference for the generated `params.json` and the
CC map.

## Preset formats (little-endian, self-validating)

Every record is a `u8 version` (`0xFF` = empty slot), a body, and a CRC-32 (poly
`0xEDB88320`, init `0xFFFFFFFF`, reflected) over version + body, so a corrupt
record is skipped and never the whole bank. `N` is the per-part voice-param count,
and `N_PART` is the part count.

- Part patch (one timbre):

  ```
  u8 version | char name[16] | i32 params[N] | u32 crc32
  ```

- Multi patch (a composition):

  ```
  u8 version | char name[16] | u8 part_slot[N_PART] | i32 level[N_PART] |
  i32 delay[N_PART] | i32 channel[N_PART] | i32 low[N_PART] | i32 high[N_PART] |
  u32 crc32
  ```

  `part_slot[i]` is the part-patch slot each part uses, `0xFF` = none.

- Settings (one global record):

  ```
  u8 version | i32 base_channel | i32 master_tune | u32 crc32
  ```

The default banks are 128 single parts and 64 multi patches, chunked across the
slot area, so the record size must fit the measured `SLOT_MAX` (16 372 B per slot).
Check the fit with the per-part count in the consistency gate. Record the measured
number.

## SysEx envelope (shared base)

```
F0 00 21 1D <model> <cmd> <ver> <payload...> <crc16-lo> <crc16-hi> F7
```

- Manufacturer id `00 21 1D`, then the firmware's `<model>` byte.
- CRC-16-CCITT (poly `0x1021`, init `0xFFFF`, no reflect) over `<cmd>...<payload>`,
  little-endian bytes.
- Five commands, every firmware answers them: `0x01` identity request, `0x02`
  param dump, `0x03` part-patch dump (with a slot byte), `0x04` multi-patch dump
  (with a slot byte), `0x05` settings dump. Responses echo the command with the
  high bit set. `0x7F` = unknown command.
- Multi-byte payload values are 7-bit packed (7 data bytes to 8 MIDI bytes with the
  collected top bits), unpacked before CRC and parse.

The payload layout, param order, count, and Q-format are per-firmware and emitted
as the generated `sysex-layout` alongside `params.json`.

## Writes are gated

Writes happen only when the engine is silent (`dsp_quiet`) and only on an explicit
save, never on a knob step. A fresh bank reads all-empty, a cut save is caught by
the area CRC, and a flipped bit by the record CRC. Flash is the persistence. RAM is
a per-boot working copy in `.pool`.
