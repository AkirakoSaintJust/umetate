---
name: umetate-development
description: Design, plan, build, and safely validate a custom M-VAVE FM-1 or SMK-37 synthesizer on the umetate framework — interview the player, author nodes/macros/patches, prove each evidence layer, and never write the device without an explicit, gated request. Use for authoring a synth, the first audible slice, DSP work, panel/controls, or evidence verification.
version: 1.0.0
license: GPL-3.0-only
compatibility: OpenCode and Agent Skills-compatible loaders
allowed-tools: read, grep, glob, edit, shell
---

# umetate synthesizer development

Use this skill when the user wants to design, implement, test, or review a custom
synthesizer for the M-VAVE FM-1 or SMK-37 on the umetate framework. Run from the
repository root; every command and path below is relative to it.

Act as a collaborative embedded-synth engineer, not an autonomous feature
factory. Preserve the user's product decisions, repository state, and control
over every device write.

## Start here

1. Read `README.md`, `docs/roadmap.md`, `docs/tutorial.md`, and `LICENSING.md` in
   that order. `docs/roadmap.md` is the single source of truth for status.
2. Inspect `git status --short` and any project instructions before editing.
   Never discard or overwrite user work.
3. Read `references/platform-facts.md` (hardware facts) and
   `references/code-conventions.md` (the app contract + numeric rules) before
   touching source.

## Operating contract

- Ask what the user wants to make. Do not assume a fixed voice architecture.
- Do not start broad implementation until the brief and plan are confirmed.
  After that, work in small audible increments without re-asking settled questions.
- Keep one brief, one plan, one load profile, and one evidence matrix. Update
  them in place; delete superseded text instead of adding another spec.
- Treat source/static, host, browser/WASM, target package, emulator, physical
  timing, and device acceptance as separate evidence layers. A lower layer never
  proves a higher one.
- Use `pass`, `fail`, `blocked`, `not-applicable`, or `not-run` for every layer.
  `blocked` is a recorded limitation, not a pass.
- Never flash, erase, force, or run a device-writing command unless the user
  explicitly requests that exact action and the §8 gates pass. A build, test, or
  edit is not permission to write hardware.
- Keep hardware register access in the HAL. Do not invent pinouts, voltages,
  clock values, FPU capabilities, or core ownership.

## Workflow

### 0. Orient

Confirm the board/model, firmware commit, available tools, and which evidence
layers are possible. Record what is blocked and why.

```sh
umetate quick-check          # read-only presence/version probe per layer
umetate status               # the roadmap's per-phase claim ledger
```

### 1. Design interview

Run focused rounds covering instrument/player, synthesis, controls/display,
MIDI, persistence, browser use, constraints, feature contracts, and the
supported-load profile. Write the confirmed result into
`templates/synth-brief.md`. Exit when the user confirms one internally
consistent brief and acceptance criteria.

### 2. Plan

Turn the brief into one living plan with `templates/project-plan.md`,
`templates/feature-contract.md`, and `templates/supported-load-profile.md`.
Exit when the user confirms interfaces, milestone order, measurable limits, and
the verification plan. Start with the smallest audible vertical slice.

### 3. Author the synth

Author the instrument as nodes/macros/patches. Inspect the shipped node library,
scaffold a starter, then replace one element at a time:

```sh
umetate lib                  # the shipped nodes + templates (local only)
umetate scaffold patch --name "My Synth" --out examples/my-synth
```

The generator AOT-compiles `patch.json` (+ `panel.json`) to the invariant
`<synth>_dsp_*` seam (`references/code-conventions.md` §4). A power user may hand-
write `dsp.c` against that same seam as an escape hatch. The patch's `params:`
section binds friendly names to flattened `<instance>.<param>` ids; `tables:` adds
`const` XIP tables. Keep the parameter API and bounds; change the sound
deliberately.

### 4. First audible slice

The slice is one oscillator, one envelope, one control, one MIDI note. Run the
host check after each change. Exit when a host test produces bounded, non-silent
output and a release to silence.

```sh
umetate deep-check --host    # the host DSP/UI tests
```

### 5. Share DSP without pretending runtimes are equal

Share pure DSP and deterministic event/state logic; keep scheduling, input,
display, DMA, flash, and buffer conversion behind adapters. The device callback
is 256 frames at nominally 44.1 kHz; an AudioWorklet quantum is usually 128
frames and its context rate may differ. Handle rate/block differences explicitly.
Prove host == wasm with the parity check (P4-1):

```sh
umetate web-build           # emscripten -> standalone dsp.wasm
umetate deep-check --web    # build + prove host == wasm parity
umetate web-serve           # loopback static server
```

### 6. Panel, display, controls

Map only controls the hardware actually exposes. Plan with
`templates/control-map.md`, then fill `panel.json`; the generator wires the UI.
Keep the audio callback free of display, flash, logging, blocking, and unbounded
work. Publish shared state with one writer or a snapshot protocol; `volatile`
alone is not atomicity. Draw only what changed.

### 7. MIDI, persistence, chosen features

Implement MIDI in small, testable pieces: channel filter, velocity-zero
note-off, sustain, panic, clock/transport if requested. Bound queues and define
overflow behaviour. Persist versioned records with CRC/commit and a rollback
path; save when silent. Do not add a feature just because the platform exposes a
peripheral.

### 8. Verify and report

Run the narrowest checks first, then widen:

```sh
umetate lint --c            # the C standing checks
umetate deep-check --host   # host tests
umetate deep-check --web    # wasm parity
umetate emu --check         # the emulator headless shot (model layer)
umetate build --board fm1 --model pro   # a target package (no flash)
```

Record each layer in `templates/evidence-matrix.md` and validate it with
`umetate evidence --strict`. A target package is not physical timing; a host test
is not device acceptance.

### 9. Recovery and handoff

Before any write, confirm the exact board/revision, current firmware, package
identity, backup, power/cable, rollback, and recovery route. Require explicit
approval for that write (`umetate flash --device`, `umetate debrick`). See
`references/platform-facts.md` §4 for the recovery taxonomy.

## Handoff to a fresh agent

A fresh agent should read, in order: the project brief and plan; the feature
contract for the current milestone; the supported-load profile and evidence
matrix; the current source and the relevant reference file. It must not "clean
up" unrelated user edits, change the platform/HAL without a written contract and
approval, weaken a test to make a build pass, or describe a blocked layer as
passed.

## Licence

GPL-3.0-only. Preserve the copyright and attribution notices in the source and
in `LICENSING.md`.
