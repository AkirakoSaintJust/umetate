---
name: umetate-development
description: Design, plan, build, and safely validate a custom M-VAVE FM-1 or SMK-37 synthesizer on the umetate framework. Before any code, a gated interview fully specifies the synth design + voice architecture, the GUI design + control flow, and the implementation plan, and checks them for consistency. Code is then mechanical translation. Never write the device without an explicit, gated request.
version: 1.1.0
license: GPL-3.0-only
compatibility: OpenCode and Agent Skills-compatible loaders
allowed-tools: read, grep, glob, edit, shell, websearch, webfetch
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

## The prime directive: design before code

No code is written until **three artifacts are complete, mutually consistent, and
user-confirmed**:

1. **Synth design + architecture** — the voice graph, the parameter manifest, and
   the tables (`templates/synth-brief.md`).
2. **GUI design + architecture + control flow** — the context stack, pages,
   bindings, navigation, and per-context control meaning
   (`templates/control-map.md`).
3. **Implementation plan** — milestones, feature contracts, resource budget,
   architecture, exact granular structure and interface of any custom code that
   needs to be written, DSP algorithms, and the verification ladder
   (`templates/project-plan.md`, `templates/feature-contract.md`,
   `templates/supported-load-profile.md`, `templates/evidence-matrix.md`,
   `templates/dsp-algorithm.md`, `templates/code-structure.md`).

These map **one-to-one** onto `patch.json`, `panel.json`, and the plan/evidence
artifacts. Step 5 (authoring) is _mechanical translation_, not design. If the
translation forces a design decision you have not already made, stop and ask —
never improvise in the code.

## Operating contract

- Ask what the user wants to make. Do not assume a fixed voice architecture.
- Treat source/static, host, browser/WASM, target package, emulator, physical
  timing, and device acceptance as separate evidence layers. A lower layer never
  proves a higher one.
- Use `pass`, `fail`, `blocked`, `not-applicable`, or `not-run` for every layer.
  `blocked` is a recorded limitation, not a pass.
- Keep one brief, one plan, one load profile, and one evidence matrix. Update
  them in place; delete superseded text instead of adding another spec.
- Never flash, erase, force, or run a device-writing command unless the user
  explicitly requests that exact action and the §8 gates pass. A build, test, or
  edit is not permission to write hardware.
- Keep hardware register access in the HAL. Do not invent pinouts, voltages,
  clock values, FPU capabilities, or core ownership.

## Workflow

### 0. Orient — read the authoritative inventory

Before interviewing, read (do not trust memory):

- `references/platform-facts.md` — SoC, clock, cores, FPU, flash, recovery.
- `references/code-conventions.md` §2 — the platform input API (keys, buttons,
  encoders, MASTER, MIDI, storage) and §3 the numeric rules.
- `firmware/src/platform.c` — the exact `BTN_*`/`ENC_*` enums per board
  (`BOARD_SMK37` vs the FM-1 branch).
- `firmware/src/ui.h` — the binding-source vocabulary and the action verbs.
- `templates/scaffold/patch.schema.json`, `panel.schema.json`, `node.schema.json`,
  `params.schema.json` — what the generator can express.
- `umetate lib list` — the shipped node library.

Record the board (`--board fm1|smk37`), the **exact control inventory** (every
named button/encoder/key/pad/fader/wheel), and what each source can express. The
exact names are board-specific — always read the `BTN_*`/`ENC_*` enums in
`firmware/src/platform.c` rather than assuming a count. The SMK-37 adds, relative
to the FM-1, the velocity keybed, 16 pads, 4 faders (+ bank), 8 encoders
(+ bank), and the pitch/mod wheels.

### 1. Design interview — the synth architecture

Interview in focused rounds; write the result into `templates/synth-brief.md`.
Cover: instrument/player + non-goals; sound + voice architecture; the parameter
manifest; tables; MIDI; persistence; acceptance. Inspect repository facts instead
of asking the user to repeat them.

- **Voice architecture** must name, concretely: the node/macro graph (ids, types,
  wires), the `voice` vs `global` zones, the `voice_out` signal, the voice count,
  the sample rate, and any feedback (only `delay1`/`delayN` break cycles — the
  graph is a DAG).
- **Parameter manifest** must list every parameter: its flattened
  `<instance>.<param>` target, min/max/default, curve, unit, rate
  (`sample`/`block`), and whether it is `modulatable`. This is the source of the
  generated `params.json`.
- **Tables** must name any wavetable/segments/spectrum/phase-map data (the
  `tables:` section → `const` XIP).

Each node/macro's **DSP algorithm** (the exact math, formats, coefficients,
state, and edge cases) is specified in `templates/dsp-algorithm.md` during
planning (step 3) — which requires research, not recall. The design interview
only fixes the *graph*; the algorithm spec pins the *how*.

**Exit:** the brief + architecture + manifest are complete, internally consistent,
and user-confirmed. Do not proceed to the GUI until the voice architecture is
stable (it determines which parameters the GUI can expose).

### 2. GUI interview — the control map

Write into `templates/control-map.md`. Map **only** sources that exist (from
orient). Cover: surface inventory (exact controls + kinds); the context stack
(modes); each context's pages + widgets + bindings; global bindings; the boot
screen; LED/pad feedback; and the full control flow.

- **Contexts:** every mode is a context with pages, bindings, and optional
  `on_enter`/`on_exit` hooks (save-on-exit, reset-on-entry).
- **Control flow:** name every transition — `push`/`pop`/`pop_home`/`next_page`/
  `prev_page`/`set_page`/`bank_next`/`bank_prev` — and which control triggers it.
  A fresh agent must be able to trace every button/encoder/key through every
  context with no ambiguity.
- **Global bindings** are resolved last: `KEY → note_on`, `MASTER → volume`,
  transport, panic.
- **Widgets** are abstract (`label`, `value`, `bar`, `param_row`, `param_column`,
  `list`, `grid`) — no skeuomorphic knobs on a 240×240 screen.

**Exit:** every control is mapped to a param or action, or explicitly marked
unmapped; every binding target is a param from the manifest; the control flow is
complete and user-confirmed.

### 3. Implementation plan

Turn the two designs into one living plan:

- `templates/project-plan.md` — milestones ordered by audible value: first slice
  → polyphony/filter → panel/display → MIDI/persistence → target/device.
- `templates/feature-contract.md` — one per milestone: params/events, bounds,
  files, verification, risks, fallback.
- `templates/supported-load-profile.md` — the simultaneous maxima and the worst
  case. Hard limits (per `docs/roadmap.md` §12.2, verified by the linker report):
  audio callback ≤ 2.9 ms (50% of 5.8 ms); CPU0 `.data`/`.bss` ≤ 96 KiB; CPU1
  `.cpu1_bss` ≤ 16 KiB; `.dsp_text` ≤ 32 KiB; `.pool` ≤ 336 KiB; XIP code + const
  ≤ 568 KiB; stack 24 KiB CPU0 + 8 KiB CPU1.
- `templates/evidence-matrix.md` — one row per layer, exact command/artifact.
- `templates/dsp-algorithm.md` — the exact algorithm for each component (see
  "DSP algorithm research" below).
- `templates/code-structure.md` — the exact structure + interface of any custom
  code: files, the `<synth>_dsp_*` seam (or `node.json` + `process(ctx, n)` for a
  new node), data layout + section placement, and the host-test hook.

Record file ownership: which files may change, and the forbidden ones (HAL
registers, `platform.c` services, the loader, `uboot.boot`/`isd_config.ini`).

### DSP algorithm research (specification *and* implementation)

Before you write any DSP algorithm, research how it is best implemented. The
user may supply references; online search may surface more. Start from the
default reference points:

| Source | URL |
| --- | --- |
| ymfm (MAME 3rdparty) | https://github.com/mamedev/mame/tree/master/3rdparty/ymfm |
| SuperCollider DSP (UGens) | https://github.com/supercollider/supercollider |
| Mutable Instruments (eurorack) | https://github.com/pichenettes/eurorack |
| Synthesis Toolkit (STK) | https://github.com/thestk/stk |
| maximilian | https://github.com/micknoise/Maximilian |
| music dsp archives | https://www.musicdsp.org/en/latest/ |

The in-repo study is `docs/dsp-study.md` (MI, SuperCollider, Pure Data, Dexed,
Nuked, ymfm, SAPF).

**Credit and licences.** Distinguish *consulting* a source (learn the technique —
give credit in the algorithm spec) from *copying/deriving* its code (preserve the
source's notice and record it in `LICENSING.md`). Check each source's licence at
use: GPL-3.0 code folds into this GPL-3.0 project; MIT/BSD code requires its
notice preserved; incompatible-licensed code is consulted, never copied.

**Performance and memory safety are constraints throughout:** bounded loops, no
allocation, no 64-bit division, no `double`, no per-sample dispatch in the hot
loop; one writer per shared value or a snapshot protocol.

**Exit:** the user confirms interfaces, milestone order, measurable limits, and
the verification plan.

### 4. The consistency gate (fully green before any code)

Cross-check the three artifacts against each other. A failure means _fix the
artifact_, never the code. Walk every item; do not skip:

- [ ] Every GUI binding target is a parameter in the manifest, or a reserved
      action verb from `panel.schema.json`.
- [ ] Every parameter is reachable (bound by a control or MIDI CC) or explicitly
      marked internal-only.
- [ ] Every control in the inventory is mapped or explicitly unmapped — no
      silent gaps.
- [ ] Every node/macro type in the voice architecture resolves: a shipped node
      (`umetate lib list`) or a macro defined in the patch.
- [ ] Every wire connects real ports; `voice_out` names a real voice-zone signal;
      `gate`/`velocity` reserved sources are used correctly.
- [ ] The voice count × architecture fits the supported-load profile (voice SoA
      × nodes × per-sample work within the callback budget).
- [ ] The MIDI map (`cc:N`, `note:N`) targets only defined parameters.
- [ ] Persistence fields correspond to defined parameters/tables.
- [ ] Non-goals are respected; no feature was added "because the platform can".

Then restate the whole plan to the user, in one message, and require explicit
confirmation before writing code.

### 5. Author the synth — mechanical translation

Now translate, do not design:

```sh
umetate scaffold patch --name "My Synth" --out examples/my-synth
```

- Fill `patch.json` from the voice architecture + parameter manifest + tables.
- Fill `panel.json` from the control map.
- Add a node to `modules/` only when a shipped node is genuinely insufficient
  (conform to `node.schema.json`; add its host test + budget annotation).
- After each increment, prove it: `umetate deep-check --host`.

### 6. Share DSP, panel, MIDI, persistence

- Share pure DSP across host/browser/firmware; keep scheduling/display/DMA/flash
  behind adapters. The device callback is 256 frames @ 44.1 kHz; an AudioWorklet
  quantum is ~128 frames. Prove parity: `umetate web-build` then
  `umetate deep-check --web`.
- Keep the audio callback free of display, flash, logging, blocking, allocation.
- Bound queues and define overflow; velocity-zero is note-off; persist versioned
  records with CRC/commit, saving when silent.

### 7. Verify and report

Run the narrowest checks first, then widen:

```sh
umetate lint --c
umetate deep-check --host
umetate deep-check --web
umetate emu --check
umetate build --board fm1 --model pro      # a target package, no flash
```

Record each layer in `templates/evidence-matrix.md` and validate with
`umetate evidence --strict`. A target package is not physical timing; a host test
is not device acceptance.

### 8. Recovery and handoff

Before any write, confirm the exact board/revision, current firmware, package
identity, backup, power/cable, rollback, and recovery route. Require explicit
approval for that write (`umetate flash --device`, `umetate debrick`). See
`references/platform-facts.md` §4 for the recovery taxonomy.

## Handoff to a fresh agent

A fresh agent should read, in order: the project brief + architecture + manifest;
the control map; the plan + current feature contract; the load profile and
evidence matrix; then the current source. It must not "clean up" unrelated user
edits, change the platform/HAL without a written contract and approval, weaken a
test to make a build pass, or describe a blocked layer as passed. Its first action
is read-only inspection, then a one-line statement of the next safe increment.

## Licence

GPL-3.0-only. Preserve the copyright and attribution notices in the source and
in `LICENSING.md`.
