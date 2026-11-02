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
repository root, every command and path below is relative to it.

Work as a collaborative embedded-synth engineer, not an autonomous feature
factory. Preserve the user's product decisions and repository state. The user
retains control over every device write.

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

1. **Synth design + architecture**, the voice graph, the parameter manifest, and
   the tables (`templates/synth-brief.md`).
2. **GUI design + architecture + control flow**, the context stack, pages,
   bindings, navigation, and per-context control meaning
   (`templates/control-map.md`).
3. **Implementation plan**, milestones, feature contracts, resource budget,
   architecture, exact granular structure and interface of any custom code that
   needs to be written, DSP algorithms, and the verification ladder
   (`templates/project-plan.md`, `templates/feature-contract.md`,
   `templates/supported-load-profile.md`, `templates/evidence-matrix.md`,
   `templates/dsp-algorithm.md`, `templates/code-structure.md`).

These map **one-to-one** onto `patch.json`, `panel.json`, and the plan/evidence
artifacts. Step 5 (authoring) is _mechanical translation_, not design. If translation
requires a new design decision, stop and ask. Do not improvise in code.

## Operating contract

- Ask what the user wants to make. Do not assume a fixed voice architecture.
- Treat source/static, host, browser/WASM, target package, emulator, physical
  timing, and device acceptance as separate evidence layers. A lower layer never
  proves a higher one.
- Use `pass`, `fail`, `blocked`, `not-applicable`, or `not-run` for every layer.
  `blocked` is a recorded limitation, not a pass.
- Keep one brief, one plan, one load profile, and one evidence matrix. Update
  them in place, delete superseded text instead of adding another spec.
- Think in the **composition model + workflow loop** (`docs/roadmap.md` §6.12):
  node → macro → patch → panel → generator → firmware, produced by the orient →
  interview → plan → gate → author → verify loop. A decision that changes one
  level is reflected in both the model and the plan, never only in the code.
- **One decision-set per increment** (`docs/roadmap.md` §6.13): the smallest
  coherent, verifiable change, test the full gate after each, commit with the
  roadmap/brief/plan updated in the same commit. Never batch unrelated decisions,
  and never implement before the design is confirmed.
- Never flash, erase, force, or run a device-writing command unless the user
  explicitly requests that exact action and the §8 gates pass. A build, test, or
  edit is not permission to write hardware.
- When you remove a feature, remove its wiring *and* state in the same increment,
  a scrapped feature leaves a stray path that breaks later (type-p-fm1's early
  carrier-feedback knob left a spurious feedback floor on every carrier).
- Keep hardware register access in the HAL. Do not invent pinouts, voltages,
  clock values, FPU capabilities, or core ownership.

## Workflow

### 0. Orient: read the authoritative inventory

Before interviewing, read (do not trust memory):

- `references/platform-facts.md`, SoC, clock, cores, FPU, flash, recovery.
- `references/code-conventions.md` §2, the platform input API (keys, buttons,
  encoders, MASTER, MIDI, storage) and §3 the numeric rules.
- `firmware/src/platform.c`, the exact `BTN_*`/`ENC_*` enums per board
  (`BOARD_SMK37` vs the FM-1 branch).
- `firmware/src/ui.h`, the binding-source vocabulary and the action verbs.
- `templates/scaffold/patch.schema.json`, `panel.schema.json`, `node.schema.json`,
  `params.schema.json`, what the generator can express.
- `umetate lib list`, the shipped node library.

Record the board (`--board fm1|smk37`), the **exact control inventory** (every
named button/encoder/key/pad/fader/wheel), and what each source can express. The
exact names are board-specific, always read the `BTN_*`/`ENC_*` enums in
`firmware/src/platform.c` rather than assuming a count. The SMK-37 adds, relative
to the FM-1, the velocity keybed, 16 pads, 4 faders (+ bank), 8 encoders
(+ bank), and the pitch/mod wheels.

Record each control's **kind**, not just its name: a smooth analog *pot* (the
FM-1's `MASTER`) is volume and platform-owned, a detented *encoder* is a parameter
control. Distinguish *dedicated* knobs (`ALGORITHM`, `PRESETS`) from *page-slot*
knobs (`KNOB1–4`). Name collisions exist, the FM-1 has both a `SELECT` *knob* and
a `SEL` *button*, so read the enums, never guess.

### 1. Design interview: the synth architecture

Interview in focused rounds, write the result into `templates/synth-brief.md`.
Cover: instrument/player + non-goals, sound + voice architecture, the parameter
manifest, tables. MIDI, persistence, acceptance. Inspect repository facts instead
of asking the user to repeat them.

- **Voice architecture** must name, concretely: the node/macro graph (ids, types,
  wires), the `voice` vs `global` zones, the `voice_out` signal, the voice count,
  the sample rate, and any feedback (only `delay1`/`delayN` break cycles, the
  graph is a DAG). In FM, tap operator **self-feedback from the oscillator output**
  (pre-envelope/pre-tremolo), tapping the enveloped VCA output leaks the
  amplitude LFO and envelope into `ph.fm` as spurious pitch modulation (type-p-fm1
  carriers warbled with the A-LFO until the tap moved to `osc.audio`).
- **Parameter manifest** must list every parameter: its flattened
  `<instance>.<param>` target, min/max/default, curve, unit, rate
  (`sample`/`block`), and whether it is `modulatable`. This is the source of the
  generated `params.json`.
- **Tables** must name any wavetable/segments/spectrum/phase-map data (the
  `tables:` section → `const` XIP).
- **Multi-timbrality** (if the synth has `parts:`): name each part, whether it is
  an **independent timbre** (its own parameter set), its routing (`channel` +
  keyzone `low`/`high`), its gain/timing (`level`, `delay`), the note→part routing
  rule (channel + keyzone), whether **layering** is allowed (one note → several
  parts), and the voice pool per part + the total.
- **MIDI specification**: the receive channels (per part or omni), the `cc → param`
  map (fixed generator-assigned, or user-assignable), sustain (CC64), panic
  (CC123), pitch bend, program change, and note-on/off + velocity. This is the
  source of the generated `cc-map` and the `note_on_ch` allocator.

Each node/macro's **DSP algorithm** (the exact math, formats, coefficients,
state, and edge cases) is specified in `templates/dsp-algorithm.md` during
planning (step 3), which requires research, not recall. The design interview
only fixes the *graph*, the algorithm spec pins the *how*.

**Exit:** the brief + architecture + manifest are complete, internally consistent,
and user-confirmed. Do not proceed to the GUI until the voice architecture is
stable (it determines which parameters the GUI can expose).

### 2. GUI interview: the control map

Write into `templates/control-map.md`. Map **only** sources that exist (from
orient). Cover: surface inventory (exact controls + kinds), the context stack
(modes), each context's pages + widgets + bindings, global bindings, the boot
screen. LED/pad feedback, and the full control flow.

- **Contexts:** every mode is a context with pages, bindings, and optional
  `on_enter`/`on_exit` hooks (save-on-exit, reset-on-entry).
- **Menu → page → mode correspondence:** enumerate the full graphical tree,
  every context (menu), its pages, and the *modes* within a page (a page whose
  widgets change under a hold/shift, or a multi-mode page). A fresh reader must be
  able to draw the screen for every state, this is the panel's *graphical UI
  correspondence*, not just its bindings.
- **Control flow:** name every transition, `push`/`pop`/`pop_home`/`next_page`/
  `prev_page`/`set_page`/`bank_next`/`bank_prev`, and which control triggers it.
  A fresh agent must be able to trace every button/encoder/key through every
  context with no ambiguity.
- **Global bindings** are resolved last: `KEY → note_on`, `MASTER → volume`,
  transport, panic.
- **Widgets** are abstract (`label`, `value`, `bar`, `param_row`, `param_column`,
  `list`, `grid`), no skeuomorphic knobs on a 240×240 screen.
- **GUI design rules** (learned on the type-p-fm1 FM-1 exercise):
  - **Know each control's kind.** A smooth pot (`MASTER`) is volume and
    platform-owned, never bind it to a page slot, a detented encoder is a
    parameter. Distinguish dedicated knobs from page-slot knobs.
  - **Respect the silkscreen.** A control's printed label fixes its meaning, the
    firmware must mean what it says. Don't reassign a labelled control.
  - **Keys are a menu surface.** A keybed is not just notes, use keys as
    shortcuts (operator select, mute) so a few controls reach every parameter.
  - **Prefer the page-slot model.** A small fixed set of encoders whose meaning
    changes per page, with the labels shown on screen (the screen says what the
    knobs do). This beats deep menus for a few knobs + a 240×240 screen.
  - **Gesture primitives.** If the design needs long-press/double-tap, check the
    UI kit expresses it, otherwise use an explicit page or button.
  - **Popups capture control.** A modal popup (name/save/part/copy chooser) owns
    all control while open (`ui_popup_active()`), the app drains the page encoders
    so a stray knob twist never fires on the page behind the popup. Modal popups
    **auto-close after ~3 s of no input** (non-destructive, `ui_popup_cancel_all`),
    and commits show a brief "SAVED/COPIED SUCCESSFULLY" acknowledgement.
  - **Mirror parallel modulations.** When two modulation sources reach the same
    targets (key-follow and velocity-follow), give them the same page *shape* in
    the same menus, one page set per source, differing only where the source
    differs (velocity drops the breakpoint/LO-HI and adds a single per-target
    amount + a global on/off). Put a "targets live in EDIT/FX/ENV" hint on the
    global page that owns the shared control, so the user learns one set of pages
    and understands the other.

**Exit:** every control is mapped to a param or action, or explicitly marked
unmapped, every binding target is a param from the manifest, the control flow is
complete and user-confirmed.

### 3. Implementation plan

Turn the two designs into one living plan:

- `templates/project-plan.md`, milestones ordered by audible value: first slice
  → polyphony/filter → panel/display → MIDI/persistence → target/device.
- `templates/feature-contract.md`, one per milestone: params/events, bounds,
  files, verification, risks, fallback.
- `templates/supported-load-profile.md`, the simultaneous maxima and the worst
  case. Hard limits (per `docs/roadmap.md` §12.2, verified by the linker report):
  audio callback ≤ 2.9 ms (50% of 5.8 ms). CPU0 `.data`/`.bss` ≤ 96 KiB. CPU1
  `.cpu1_bss` ≤ 16 KiB, `.dsp_text` ≤ 32 KiB, `.pool` ≤ 336 KiB. XIP code + const
  ≤ 568 KiB, stack 24 KiB CPU0 + 8 KiB CPU1.
- `templates/evidence-matrix.md`, one row per layer, exact command/artifact.
- The **voice count is a measured claim**, run `umetate budget --voices N,M --parts P`
  (host timing: per-voice cost + linearity, the 2.9 ms device fit is the
  emulator's job, `blocked` until the firmware is built). Never estimate polyphony.
- `templates/dsp-algorithm.md`, the exact algorithm for each component (see
  "DSP algorithm research" below).
- `templates/code-structure.md`, the exact structure + interface of any custom
  code: files, the `<synth>_dsp_*` seam (or `node.json` + `process(ctx, n)` for a
  new node), data layout + section placement, and the host-test hook.

Record file ownership: which files may change, and the forbidden ones (HAL
registers, `platform.c` services, the loader, `uboot.boot`/`isd_config.ini`).

### DSP algorithm research (specification *and* implementation)

Before you write any DSP algorithm, research how it is best implemented. The
user may supply references, online search may surface more. Start from the
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

**Credit and licences.** Distinguish *consulting* a source (learn the technique,
give credit in the algorithm spec) from *copying/deriving* its code (preserve the
source's notice and record it in `LICENSING.md`). Check each source's licence at
use: GPL-3.0 code folds into this GPL-3.0 project. MIT/BSD code requires its
notice preserved, incompatible-licensed code is consulted, never copied.

**Performance and memory safety are constraints throughout:** bounded loops, no
allocation, no 64-bit division, no `double`, no per-sample dispatch in the hot
loop, one writer per shared value or a snapshot protocol.

**Oscillator anti-aliasing (a standing warning).** A *naive* table-based
square/saw/pulse (and the shipped `naive_osc`) folds its above-Nyquist harmonics
back into the band at high pitches, audible as inharmonic, warbly "ghost"
partials that a filter cannot remove. When a design calls for these shapes, use a
band-limited source: the polyBLEP `saw`/`pulse`/`triangle` nodes, or the
mip-mapped `osc` (waves 9/10/11 are six band-limited levels selected from the
note's increment via the phasor's `fm1_wave_mip(step)`). Sine-derived shapes (the
OPZ set, `osc` waves 0-8) are already band-limited. Warn the user explicitly
against excessive aliasing when a raw square/saw is pitched into the top octaves.

**Summed modulations must stay in bounds.** When two bipolar factors push the same
target toward its extreme (key-follow + velocity-follow on a level/cutoff/rate),
sum them and **clamp the sum** to the target's Q range before applying, so a target
never overshoots its extreme (`fm1_key_add`). Additive is correct, the clamp makes
it safe. Per-voice targets read the voice's own note/velocity, global targets read
the **highest held** note/velocity.

**No bare locals in a `node.c` body.** A node body is inlined once per instance
into the fused render, so a hardcoded local identifier (e.g. `int32_t fc;`)
**collides** when two instances of the same node share a scope. Namespace every
local through a placeholder, `${state.<name>}` (and compute it in `block_derived`
when it only depends on block-rate inputs) or `${out.<name>}`, never a bare C
identifier. This bit `svf` the moment a second filter was added (the `fc` cutoff is
block-constant, so it became a block-derived state field).

**Exit:** the user confirms interfaces, milestone order, measurable limits, and
the verification plan.

### 4. The consistency gate (fully green before any code)

Cross-check the three artifacts against each other. A failure means _fix the
artifact_, never the code. Walk every item, do not skip:

- [ ] Every GUI binding target is a parameter in the manifest, or a reserved
      action verb from `panel.schema.json`.
- [ ] Every parameter is reachable (bound by a control or MIDI CC) or explicitly
      marked internal-only.
- [ ] Every control in the inventory is mapped or explicitly unmapped, no
      silent gaps.
- [ ] Every node/macro type in the voice architecture resolves: a shipped node
      (`umetate lib list`) or a macro defined in the patch.
- [ ] Every wire connects real ports, `voice_out` names a real voice-zone signal.
      `gate`/`velocity` reserved sources are used correctly.
- [ ] The voice count × architecture fits the supported-load profile (voice SoA
      × nodes × per-sample work within the callback budget), measured with
      `umetate budget`, not estimated.
- [ ] The MIDI map (`cc:N`, `note:N`) targets only defined parameters, sustain,
      panic, and bend are wired or explicitly deferred.
- [ ] Every part's params, routing (channel/keyzone), and gain/timing are
      specified, the note→part routing + layering is unambiguous, per-part voice
      pools sum to the supported-load profile's voice count.
- [ ] Every menu/page/mode in the GUI correspondence has its widgets and bindings.
      no page is declared without a screen it can draw.
- [ ] Persistence fields correspond to defined parameters/tables.
- [ ] Non-goals are respected, no feature was added "because the platform can".

Then restate the whole plan to the user, in one message, and require explicit
confirmation before writing code.

### 5. Author the synth: mechanical translation

Now translate, do not design:

```sh
umetate scaffold patch --name "My Synth" --out examples/my-synth
```

- Fill `patch.json` from the voice architecture + parameter manifest + tables.
- Fill `panel.json` from the control map.
- Add a node to `modules/nodes/` only when a shipped node is genuinely insufficient
  (conform to `node.schema.json`, add its host test + budget annotation).
- Work in **small increments, one decision-set per increment** (the smallest
  change that is a coherent, verifiable unit, see `docs/roadmap.md` §6.13). After
  each, run the full gate and **commit with the plan/brief/roadmap updated in the
  same commit**. Do not batch unrelated decisions, do not implement before the
  design is confirmed.

### 6. Compose the firmware: app glue on the framework

- Share pure DSP across host/browser/firmware, keep scheduling/display/DMA/flash
  behind adapters. The device callback is 256 frames @ 44.1 kHz, an AudioWorklet
  quantum is ~128 frames. Prove parity: `umetate web-build` then
  `umetate deep-check --web`.
- Keep the audio callback free of display, flash, logging, blocking, allocation.
- The MIDI spec, presets, and SysEx are **shipped framework** (`firmware/src/`:
  `synth_midi`, `synth_sysex`, `synth_runtime`, `presets.c`). Declare the CC
  surface as the patch's `cc:` list (a multitimbral patch must, its params
  overflow the 7-bit CC space), presets are 128 single parts + 64 multi patches
  (chunked across the slot area's measured ceiling), the firmware answers the
  five SysEx commands.
- Write only the **app glue**: `app.c` with `app_audio` / `app_main` / `app_idle`,
  the `ui_act_*` hooks, and the three service contexts (see
  `examples/type-p-fm1/app.c`). `umetate build --synth examples/<project>` composes
  framework + generated code + glue, host-build, run the project's
  `host-script.txt` (a silent run fails), then package through the toolchain.
- **Firmware-level controls are app glue, not panel params.** Any button the synth
  uses but the patch doesn't model (the FM-1's `OCT−`/`OCT+`) is handled directly
  in `app.c`, shift the keybed base note (`lit_base`) and clamp, the demo
  `rib_app.c` binds them, but a synth project must re-map them (a silent bug:
  octave buttons that do nothing).
- Bound queues and define overflow, velocity-zero is note-off, persist versioned
  records with CRC/commit, saving when silent.

### 6b. CPU optimisation (the safe loop)

When an increment needs to cut the audio ISR cost, follow
`references/optimisation-loop.md`. In one line: baseline the ISR% and an output
hash, profile the hot loop, check the compiler is not already optimal, then change
one lever at a time, gated byte-identical, and record both wins and rejections.
Never guess, never hand-roll what the compiler does, never accept a non-bit-exact
change.

### 7. Verify and report

The gate is one command, `umetate deep-check --all` (mypy + ruff + pyright, the
four test modules, the firmware host route, `_skill`/`_links`/`lint --c`). It is
the deterministic "is this increment done" check. The wider, slower steps follow:

```sh
umetate deep-check --all                       # the gate (one command, exit 0/1)
umetate budget <patch.json> --voices N         # the measured polyphony claim
umetate build --synth examples/<project>       # compose + host evidence + package
umetate emu --check --mhz 240                  # boot the package, hold a chord
```

Record each layer in `templates/evidence-matrix.md` and validate with
`umetate evidence --strict`. The emulator is a model (1.92× optimistic), a target
package is not physical timing, a host test is not device acceptance.

### 8. Recovery and handoff

Before any write, confirm the exact board/revision, current firmware, package
identity, backup, power/cable, rollback, and recovery route. Require explicit
approval for that write (`umetate flash --device`, `umetate debrick`). See
`references/platform-facts.md` §4 for the recovery taxonomy.

## Handoff to a fresh agent

A fresh agent should read, in order: the project brief + architecture + manifest.
the control map, the plan + current feature contract, the load profile and
evidence matrix, then the current source. It must not "clean up" unrelated user
edits, change the platform/HAL without a written contract and approval, weaken a
test to make a build pass, or describe a blocked layer as passed. Its first action
is read-only inspection, then a one-line statement of the next safe increment.

## Licence

GPL-3.0-only. Preserve the copyright and attribution notices in the source and
in `LICENSING.md`.
