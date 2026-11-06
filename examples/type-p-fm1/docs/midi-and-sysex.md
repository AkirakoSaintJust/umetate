# Type P.fm1 MIDI and SysEx reference

## MIDI in

- **Receive channels:** one channel per part. Part 0 listens on channel 1 and part
  1 on channel 2 by default, and both are set by the part routing.
- **Note on and off** carry velocity. Velocity zero is note off.
- **Sustain** is CC 64.
- **Panic, all notes off** is CC 123. It hard-cuts every voice.
- **Pitch bend** bends the whole voice.
- **Program change** selects a patch.
- **Continuous controllers** map to parameters, with each exposed parameter
  getting a CC assigned in order from a base, and the parameter list is the same one
  the panel edits: algorithm, filter cutoff and resonance, wavefolder, the operator
  ratios, levels, waveforms, feedback, mutes, and the envelopes, plus the voice
  modes.

The CC map is fixed rather than user-assignable, and the exact CC numbers are in
the firmware's generated map, in the same order the panel walks the parameters.

## SysEx

Every message uses this envelope.

```
F0 00 21 1D <model> <cmd> <ver> <payload> <crc-lo> <crc-hi> F7
```

- `00 21 1D` is the manufacturer id.
- `<model>` is the firmware's model byte.
- `<cmd>` is one of the five commands below.
- `<ver>` is a version byte.
- The two CRC bytes are a CRC-16-CCITT over the command through the payload,
  little-endian, checked before anything is parsed.

The firmware answers five commands.

| Command | Function |
| --- | --- |
| `0x01` | Identity request. The reply names the firmware. |
| `0x02` | Parameter dump. Reads or writes the live parameters. |
| `0x03` | Part-patch dump. Reads or writes one single-part patch, with a slot byte. |
| `0x04` | Multi-patch dump. Reads or writes one multi patch, with a slot byte. |
| `0x05` | Settings dump. Reads or writes the global settings. |

Responses echo the command with the high bit set. An unknown command answers
`0x7F`.

Multi-byte values in the payload are 7-bit packed, seven data bytes to eight MIDI
bytes, and unpacked before the CRC.

## Backing up and restoring

Use any SysEx librarian that can send and receive raw SysEx. Request a parameter
or part-patch dump and record the reply, then send it back to restore. The bank is
128 single-part patches and 64 multi patches.

The host tool also converts an OPM text bank into single-part patches:

```sh
umetate opm convert voices.opm --out voices.bank.json --syx voices.syx
```

Load a converted part from the `GLO` browser. The
[OPM mapping page](https://github.com/AkirakoSaintJust/umetate/blob/main/docs/opm-to-type-p-fm1.md)
carries the mapping, the bank geometry, and the measured tolerance.

A Type P.fm1 patch is a four-operator FM patch, so a DX7 sysex file will not
load, because DX7 is a six-operator format.
