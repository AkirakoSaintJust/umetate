# OPM patch file format

An `.opm` patch bank is a plain-text file. VOPM and VOPMex read it as a bank of
YM2151 voices. The file has no structural header, no length field, and no checksum.
Each voice starts with an `@` line and carries five parameter lines. The parser
reads the blocks in file order. The `@` number names the slot.

The same extension is used by two unrelated formats. This page covers the text
patch bank that VOPM and VOPMex import. The other formats are described at the end.

## File shape

A bank is a sequence of voice blocks. The five comment lines below are the
conventional column guide. They are not a signature and a reader can load a file
without them. Keep them anyway, because VOPM and VOPMex write them and humans read
them.

```text
//MiOPMdrv sound bank Paramer Ver2002.04.22
//LFO: LFRQ AMD PMD WF NFRQ
//@:[Num] [Name]
//CH: PAN FL CON AMS PMS SLOT NE
//[OPname]: AR D1R D2R RR D1L TL KS MUL DT1 DT2 AMS-EN

@:0 Sine
LFO: 0 0 0 0 0
CH: 64 0 0 0 0 120 0
M1: 31 0 0 15 0 127 0 1 0 0 0
C1: 31 0 0 15 0 127 0 1 0 0 0
M2: 31 0 0 15 0 127 0 1 0 0 0
C2: 31 0 0 15 0 0 0 1 0 0 0
```

The example uses algorithm 0, so C2 is the carrier and the other three operators
are held at their quietest level. The patch is a sine at the played note.

Values are decimal integers. Spaces and tabs both separate fields. Blank lines are
ignored. `//` starts a comment that runs to the end of the line. Write ASCII without
a byte-order mark. Line endings can be LF or CRLF, though older VOPM builds are
happier with LF.

`@:n name` opens a voice. `n` is the bank slot, normally 0 to 127. The name is the
rest of the line, spaces included. Keep slots unique and write one block per used
slot. The format has no voice count, so the number of `@` blocks is the count.

After the `@` line, the conventional order is `LFO`, `CH`, `M1`, `C1`, `M2`, `C2`.
The parser assigns each line to the current voice, so a reader may accept another
order. Write this order for portability.

## LFO line

The LFO line holds five fields. They set the chip's low-frequency oscillator and the
noise generator that replaces C2 when noise is enabled.

| Field | Range | Meaning |
| --- | --- | --- |
| `LFRQ` | 0 to 255 | LFO rate. Higher values run faster. The master clock scales the rate. |
| `AMD` | 0 to 127 | Amplitude modulation depth. |
| `PMD` | 0 to 127 | Phase modulation depth. |
| `WF` | 0 to 3 | LFO waveform: 0 saw, 1 square, 2 triangle, 3 sample-and-hold noise. |
| `NFRQ` | 0 to 31 | Noise frequency for the C2 noise generator. |

`AMD` and `PMD` are global on the chip. `AMS` and `PMS` on the channel line set how
much each channel responds. The LFO line is stored per voice. A real YM2151 has one
LFO, so only one voice's line is in force. VOPMex's virtual mode can give each MIDI
channel its own LFO.

## Channel line

The channel line holds seven fields. They set pan, feedback, the connection
algorithm, the LFO sensitivities, the key-on mask, and noise.

| Field | Range | Meaning |
| --- | --- | --- |
| `PAN` | 0, 64, 128, 192 | Stereo placement in the top two bits. 192 enables both outputs. VOPM uses 64 as its default centre setting. |
| `FL` | 0 to 7 | Feedback level for M1. |
| `CON` | 0 to 7 | Connection algorithm. |
| `AMS` | 0 to 3 | Amplitude modulation sensitivity for the channel. |
| `PMS` | 0 to 7 | Phase modulation sensitivity for the channel. |
| `SLOT` | 0 to 127, shifted left by 3 | Key-on slot mask. 120 (`0x78`) enables M1, C1, M2, and C2. |
| `NE` | 0 or 1 | Noise enable. 1 replaces C2's sine with the noise generator. |

`PAN` trips up writers. The file stores the two register bits in bits 6 and 7, so
the usual values are 0, 64, 128, and 192. 192 enables both outputs. VOPM's editor
treats 64 as its centre setting, and the exact left and right mapping varies
between players and converters. Test a pan setting in the target before relying on
it.

`SLOT` is already shifted into bits 3 to 6. 120 is the common value. Writing 15
would address the channel bits rather than the four slot bits.

## Operator line

Each operator line holds eleven fields. The four lines use the same columns. The
file order is M1, C1, M2, C2.

| Field | Range | Register bits | Meaning |
| --- | --- | --- | --- |
| `AR` | 0 to 31 | `0x80` bits 4 to 0 | Attack rate. |
| `D1R` | 0 to 31 | `0xA0` bits 4 to 0 | First decay rate. |
| `D2R` | 0 to 31 | `0xC0` bits 4 to 0 | Second decay rate. |
| `RR` | 0 to 15 | `0xE0` bits 3 to 0 | Release rate. |
| `D1L` | 0 to 15 | `0xE0` bits 7 to 4 | First decay level. |
| `TL` | 0 to 127 | `0x60` bits 6 to 0 | Total level. 0 is loudest, 127 is quietest. |
| `KS` | 0 to 3 | `0x80` bits 7 to 6 | Key scaling. |
| `MUL` | 0 to 15 | `0x40` bits 3 to 0 | Frequency multiplier. 0 means 0.5 times the base. |
| `DT1` | 0 to 7 | `0x40` bits 6 to 4 | Fine detune. |
| `DT2` | 0 to 3 | `0xC0` bits 7 to 6 | Coarse detune. |
| `AME` | 0 or 1 | `0xA0` bit 7 | Amplitude modulation enable for the operator. |

The register bits in the table are offsets from the operator group base. The group
bases are below. `AME` is the field that some tables call `AMS-EN`. VOPM and VOPMex
write 0 or 1. A table that shows 128 is showing the register bit rather than the file
value. Treat any nonzero `AME` as enabled.

## Register mapping

The channel registers use the channel number directly. The operator registers add a
slot offset as well. The slot offset is the part that surprises writers.

| Register | Address | Fields |
| --- | --- | --- |
| Channel control | `0x20 + channel` | `PAN` bits 7 to 6, `FL` bits 5 to 3, `CON` bits 2 to 0 |
| LFO sensitivity | `0x38 + channel` | `PMS` bits 6 to 4, `AMS` bits 1 to 0 |
| Key-on mask | `0x08` | `SLOT` in bits 6 to 3, channel in bits 2 to 0 |
| Noise | `0x0F` | `NE` bit 7, `NFRQ` bits 4 to 0 |
| LFO rate | `0x18` | `LFRQ` bits 7 to 0 |
| LFO depth | `0x19` | `AMD` with bit 7 clear, `PMD` with bit 7 set |
| LFO waveform | `0x1B` | `WF` bits 1 to 0 |

The operator groups use these bases:

| Group | Base |
| --- | --- |
| `DT1` and `MUL` | `0x40` |
| `TL` | `0x60` |
| `KS` and `AR` | `0x80` |
| `AME` and `D1R` | `0xA0` |
| `DT2` and `D2R` | `0xC0` |
| `D1L` and `RR` | `0xE0` |

The operator address is the group base plus the slot offset plus the channel. The
file order and the chip order differ:

| File line | Chip name | Slot offset |
| --- | --- | --- |
| `M1` | OP1 | `0x00` |
| `C1` | OP2 | `0x10` |
| `M2` | OP3 | `0x08` |
| `C2` | OP4 | `0x18` |

The file order is M1, C1, M2, C2. The chip order is M1, M2, C1, C2. If you write the
file's C1 line at offset `0x08`, you have written M2. That swaps a carrier with a
modulator and is the most common conversion bug. Muting one operator at a time is a
quick way to check the mapping.

## Compatibility notes

VOPMex 2021.05.01 fixed loading CR+LF files. Older VOPM builds may reject them, so
LF is the safer line ending when a file must load everywhere.

The file has no magic number and no version field. A text patch bank starts with
`//` or `@:`. A binary file with the same extension is a different format.

VOPM and VOPMex banks use slots 0 to 127. A parser may accept a larger `@` number,
but the editor will not show it. Writer tools often pad a bank to 128 slots with
placeholder voices.

`AME` is normally 0 or 1. Treat any nonzero value as enabled. `PAN` uses the top two
bits and 192 is the value that enables both outputs. Both fields are common sources
of mismatch between converters.

The LFO line is per voice in the file. On hardware the LFO is global, so only one
voice's `LFRQ`, `AMD`, `PMD`, and `WF` are in force. VOPMex virtual mode can use a
per-channel LFO. Noise is also global on hardware, while VOPMex virtual mode can
give noise to more than one voice.

## Binary files with the same extension

The text patch bank is one of three things that use `.opm`.

The Otomata Labs OPM stream format starts with the four bytes `OPM\x1A`. It has a
binary header with a version, chip type, clock rate, frame rate, stream count, and
stream descriptors. It is a music and stream container, not a YM2151 patch bank.

OPMDRV `.opm` files are MML music data. They contain commands such as `(v...)`,
`@N`, and `cdefgab`.

A quick check: a file that starts with `//` or `@:` is the VOPM and VOPMex patch
bank. A file that starts with `OPM\x1A` is the binary stream format. A file that
starts with MML text is an OPMDRV music file.

## Sources

- VGMrips, [OPM File Format](https://vgmrips.net/wiki/OPM_File_Format).
- Tanalin, [VOPM: the unofficial manual](https://tanalin.com/en/articles/third-party/vopm-manual/).
- Picopicose, [VOPMex](https://picopicose.com/software) and the VOPMex readme.
- Vampirefrog, [`opm_file.c`](https://github.com/vampirefrog/libfmvoice/blob/master/opm_file.c).
- 8BitDev, [YM2151 Programming](https://7800.8bitdev.org/index.php/YM2151_Programming).
- Oykenkyu, [YM2151 register map](https://oykenkyu.blogspot.com/2022/05/ym2151.html).
- VGM tooling, [OPM decoding notes](https://github.com/vgmtool/vgm2pre/issues/2).
- Otomata Labs, [`opmfile.h`](https://codigo.otomatalabs.net/otomatalabs/new-horizons/src/commit/5a8385ad3d442600a87d827638c401470764174b/utils/vgm2opm/opmfile.h).
