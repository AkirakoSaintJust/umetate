---
name: umetate-safety
description: Security review for the umetate toolkit and RIB firmware, memory-safety and attack-surface analysis of USB/UAC/MIDI/OTA, package identity, the update loader, flash/store, the host installer, and the build supply chain, and the gate on every device write. Use for any review or change touching those surfaces, or any device-write approval decision.
version: 1.0.0
license: GPL-3.0-only
compatibility: OpenCode and Agent Skills-compatible loaders
allowed-tools: read, grep, glob, edit, shell
---

# umetate safety

Review the umetate toolkit and its RIB firmware for memory-safety and
attack-surface defects, and gate every device write. This skill replaces the
generic memory-safety/security-audit skills with one workflow that knows RIB's
actual surfaces and evidence gates.

The scope is the **FM-1 and SMK-37 family** on the JieLi AC791N/WL82, not a
general-purpose web or cloud audit. A candidate without a concrete affected
principal, buffer, endpoint, or security outcome is not a confirmed finding.

## Start here

1. Read `README.md`, `docs/roadmap.md`, and `references/platform-facts.md` in that
   order. `references/platform-facts.md` owns the evidence-tagged
   update/identity/recovery facts and the recovery taxonomy.
2. Inspect `git status --short`. Never discard or overwrite user work.
3. Treat `SEC-1` (USB endpoint `MAXP`/buffer/descriptor mismatch) and `SEC-2`
   (UAC stereo out-of-object access) as the worked examples: both have source
   fixes and host tests, and both device validations are still `blocked`.

## Evidence discipline

- Source/static, host, browser/WASM, target package, emulator, physical timing,
  and device acceptance are separate layers. A lower layer never proves a higher
  one.
- Use `pass`, `fail`, `blocked`, `not-applicable`, or `not-run`. `blocked` and
  `not-run` are not passes.
- A source fix without a target rebuild is `source-only`, "validated" requires
  the device result. The baseline is **not** security-clean while `SEC-1` device
  validation is blocked.
- Updates use CRC-16, not a signature: integrity, not authenticity. Model checks
  prevent wrong-model installs, not malicious packages. Preserve that wording.

## Surface map

For each surface, name the principal (attacker, host, or malformed package), the
boundary, and the code that owns it:

| Surface | Principal | Boundary | Source | Integrity |
| --- | --- | --- | --- | --- |
| USB EP0 (control) | Host | Control transfers | `firmware/src/usb.c` | descriptor/`MAXP` bounds |
| USB EP1/EP3 (audio) | Host | Bulk audio DMA | `firmware/src/usb.c`, `uac_fir.h` | `MAXP` = buffer/descriptor (SEC-1) |
| UAC stereo tap | Firmware | L/R window into the block | `firmware/src/uac_tap.h` | explicit L/R windows (SEC-2) |
| MIDI SysEx | Host | SysEx stream | `firmware/src/midi_uart.c` | length/parse bounds |
| Update SysEx | Host | `F0 22 24 35 …` | `firmware/tools/fm1_install.py`, loader | CRC-16 integrity, not signature |
| Mask-ROM download | Host | `… 7D F7` vs `… 7F F7` | loader | one SysEx byte, never send by hand |
| OTA parser | Host | `.fwsc` package | `firmware/src/ota.c`, `fm1_install.py` | header/file-list/file CRC |
| Update loader | Host | `ota-<identity>` | shared update library | model check on resume |
| Flash/store | Firmware | Flash map allow-list | `firmware/hal/fm1_flash_map.h`, `src/store.h` | compile-time asserted ranges |
| Package identity | Host | identity reply | `fm1_install.py` | `([^_]+)_(\d+)` + `same_keyboard` |
| Host installer | Operator | `umetate flash` | `umetate/flash.py` | `--device` confirmation |
| Build supply chain | Maintainer | toolchain/SDK | `env.lock`, `umetate/setup.py` | pinned hashes |

## Workflow

### 1. Memory-safety review

For C that manages buffers, indices, or descriptors directly:

1. Identify every buffer and its declared and actual size.
2. Trace ownership and every execution path, including error and ISR paths.
3. Check that every index, `memcpy`/`memset`, and `MAXP` write is bounded by the
   declared size, not by a value a descriptor or endpoint can change.
4. Confirm no allocation, `float`, `double`, or 64-bit division in audio paths.

Report as `CRITICAL` (overflow, use-after-free, unbounded descriptor write),
`WARNING` (missing bounds check, leak on an error path), or `INFO` (safer
pattern), each with the exact source location and the smallest fix.

### 2. Attack-surface review

Walk each surface to code, a test, or an explicit gate. A surface with no test
and no gate is a finding, not a non-issue. Re-check with `umetate lint --c`
(SEC-1 MAXP bounds, SEC-2 UAC access, ROM-address constants, HAL-only MMIO, the
flash-busy call graph, no `double`/64-bit-div/allocation in the DSP TU).

### 3. Package identity and integrity

For `.fwsc` handling, confirm the installer parses the identity as
`([^_]+)_(\d+)`, runs `same_keyboard` and the model check on install **and**
resume, and checks the header/file-list/file CRCs before writing. Identity
strings are frozen (`_990`), the artefact filename is not the identity.

### 4. Device-write gate (§8)

Before any flash, erase, force, or device write, every gate must be true plus the
operator's explicit request for that exact action:

1. **Explicit request**, by name, a build/test does not imply it.
2. **Board/revision identified**, do not assume a clock or revision.
3. **Current firmware known**, record the installed identity before writing.
4. **Package verified**, `umetate inspect` confirms identity/block/CRC.
5. **Rollback identified**, a verified stock `.fwsc` plus the applicable route.
   A full-flash backup is **not** a documented FM-1 capability, do not promise one.
6. **Recovery route named**, choose one from `references/platform-facts.md` §4
   and state its prerequisite.

Hard stops: unknown recovery route or rollback image → stop, wrong-model identity
→ stop (exit 6), no physical device → the gate is `blocked`/`not-run`, not `pass`.

### 5. Report

Record each surface as a row in the evidence vocabulary. A finding cites source,
a safe reproduction, priority, and the smallest effective fix. Do not relabel a
blocked layer as a pass, and do not write "security-clean" while `SEC-1` device
validation is blocked.

## Licence

GPL-3.0-only. Preserve SPDX headers and attribution in the firmware and in
`LICENSING.md`.
