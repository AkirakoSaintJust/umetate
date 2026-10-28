# Build your own M-VAVE FM-1 / SMK-37 synthesizer

A workshop for programmers who know the sound they want but are new to the FM-1,
embedded audio, and the umetate workflow. You start from the source-built
**RIB** starter firmware, design an instrument, prototype its sound, then develop
and verify firmware in small, measured increments. Hardware is optional until stage 10
(install).

> **Safety and evidence.** Never flash as a side effect of editing code. Identify a
> real recovery route before installing. Source, host, browser, target package,
> emulator, timing, and device acceptance are separate evidence layers — a lower
> layer never proves a higher one. Use `pass` / `fail` / `blocked` / `not-run`.

## The 13 stages

| § | Stage | Outcome | Evidence layer | Hardware |
| --- | --- | --- | --- | --- |
| 1 | What umetate is; RIB as the runtime; the framework on top | correct mental model | docs | no |
| 2 | Safety before hardware (hard-brick risk, backup limits, recovery) | informed consent + a backup plan | docs | no |
| 3 | Verify the environment (`umetate quick-check`) | a green/blocked report | host | no |
| 4 | Build untouched RIB; host tests; browser lab | first sound in the browser | host/browser | no |
| 5 | The firmware contract (`app_audio`, `app_main`, `platform_poll`, HAL) | a correct app skeleton | source | no |
| 6 | Design the instrument (brief, feature contracts, load profile) | a bounded design | docs | no |
| 7 | Author the synth (nodes/macros/patches; or hand-written `dsp.c`) | a working voice | host | no |
| 8 | Controls, MIDI, screen, storage | a playable instrument | host/browser | no |
| 9 | Test (host, browser parity, target package, fm1-emu, evidence) | a recorded evidence set | host/target | no |
| 10 | Install (identity, backup, installer, verify) | a safe install plan | docs | yes |
| 11 | Validate on device (audio, MIDI, USB, stress, recovery) | a device record | device | yes |
| 12 | Troubleshoot and recover (route taxonomy) | a known recovery path | docs/device | maybe |
| 13 | Record evidence and release provenance | a traceable release | release | no |

Every stage states its evidence layer and a no-hardware path. Target timing and
device acceptance require the actual FM-1/SMK-37; installation requires the
separate approval, backup, power, identity, and recovery gates.

## Core commands

```sh
umetate quick-check         # verify the environment per layer (read-only)
umetate setup --dry-run     # see exactly what would be installed (opt-in)
umetate deep-check          # run the host-side checks (default: --host)
umetate build --board fm1 --model pro   # a target package -> .fwsc (no flash)
umetate status              # the per-phase claim ledger
```

The status authority is [`docs/roadmap.md`](roadmap.md); the evidence-tagged
hardware facts (clock, cores, FPU, flash, recovery) live in
[`docs/platform-facts.md`](platform-facts.md). The firmware code-level contract is
[`firmware/README.md`](../firmware/README.md).

---

## 1. What umetate is; RIB as the runtime; the framework on top

**umetate** is a toolkit for designing, building, testing, and safely installing
custom firmware on the M-VAVE **FM-1** and **SMK-37** (Pro/Elite/MKE-P37). **RIB**
(Rigid Inflatable Boat) is its starter firmware — a Dinghy/Felucca-derived, dual-core
base that your instrument runs on. On top of RIB sits the **framework**: a declarative
way to author the synth (nodes/macros/patches), the UI (panel/contexts), and the
parameter table, compiled by the generator into the `<synth>_dsp_*` seam.

The **composition model** (node → macro → patch → panel → generator → firmware)
and the **development loop** (design → small, tested increments → verify → commit)
are the two halves of the architecture — defined once in
[`docs/roadmap.md`](roadmap.md) §6.12–§6.13 and walked through stage by stage here.

Seven components, one entry point (`umetate`):

1. **CLI** — `quick-check`, `setup`, `build`, `emu`, `deep-check`, `inspect`,
   `flash`, `debrick`, `scaffold`, `lib`, `lint`, `fmt`, `web-build`, `web-serve`,
   `evidence`, `status`, `version`, `help`.
2. **Skill: development** — the design → build loop (offline references).
3. **Skill: safety** — threat model, attack surfaces, device-write gates.
4. **Docker image + volume** — a pinned Linux container; the JieLi toolchain lives
   in the `umetate-target` volume at `/opt/jieli` (read-only for builds, read-write
   only for `setup`).
5. **RIB starter firmware** — dual-core, integer-first DSP, FPU opt-in, SMK-37
   board layer, the `app_audio`/`app_main` contract.
6. **Tutorial** — this document.
7. **Start guide** — [`README.md`](../README.md).

**Checkpoint:** you can name the toolkit, the firmware component, and the first
command. Do not install anything yet.

## 2. Safety before hardware

Hard-brick risk is real: a single 1 MiB flash bank, no recovery button, no test
pads, no debug header. Before any write, you must be able to name a recovery route
and a rollback image. A **full-flash backup is not a documented FM-1 capability** —
the rollback target is a verified stock `.fwsc` plus the applicable route.

Read the recovery taxonomy in [`docs/platform-facts.md`](platform-facts.md) §4 and
the device-write gates in the [safety skill](../skills/umetate-safety/SKILL.md).
The rules, in one sentence: a build, test, or edit is **never** permission to write
hardware; every `flash`/`debrick` requires an explicit request, a recorded identity,
a verified package, a named rollback, and a named recovery route.

**Checkpoint:** you can state the hard-brick risk and the recovery taxonomy before
touching a device. You will not flash in this tutorial's no-hardware stages.

## 3. Verify the environment

Everything POSIX — the target build, host tests, the WASM build — runs in the
pinned Docker container; on Windows the CLI drives native `docker.exe` (Docker
Desktop). The toolchain and SDK live in the `umetate-target` volume, populated by
`setup` (opt-in, hash-verified against [`env.lock`](../env.lock)).

```sh
umetate quick-check         # read-only presence/version probe per layer
umetate setup --dry-run     # see exactly what would be installed, nothing written
```

`quick-check` reports each evidence layer; a missing toolchain is `blocked`, not a
failure. When you are ready to do target work, run `umetate setup` (with consent) to
install the JieLi toolchain + SDK into the volume, then Rust + the `fm1-emu`
emulator. `--no-emulator` opts out of the emulator.

**Checkpoint:** `quick-check` shows `source`/`host` as `pass` and `target`/`device`
as `blocked` (or `pass` for target after `setup`).

## 4. Build untouched RIB; host tests; browser lab

Build and test the baseline before you change anything:

```sh
umetate deep-check --host   # host DSP/UI/unit tests
umetate web-build           # emscripten -> standalone dsp.wasm
umetate web-serve           # loopback static server (build/web/)
```

The host tests run in the container and prove bounded, non-silent output. The
browser lab (`build/web/`) is a local listening target — an AudioWorklet that runs
the same pure DSP as the host and the firmware. It cannot prove FM-1 timing, panel
ergonomics, DMA, flash safety, or recovery.

To produce a target package (still no flash, needs the toolchain from stage 3):

```sh
umetate build --board fm1 --model pro --profile perf
```

Flags: `--board fm1|smk37`, `--model pro|elite|mke` (non-`pro` requires `--board
smk37`), `--dsp integer|float`, `--clock 240|320`, `--profile baseline|perf`. The
package (`umetate-fm1-pro.fwsc` and friends) lands in `firmware/build/`; inspect it
with `umetate inspect firmware/build/umetate-fm1-pro.fwsc` (identity, model, CRC).

**Checkpoint:** the host tests pass, the browser produces sound, and a target
package builds with the SDK asset hashes verified. A package is not device
acceptance.

## 5. The firmware contract

Your app supplies two functions, nothing else is required (see
[`firmware/README.md`](../firmware/README.md) §1):

```c
void app_audio(int32_t *out, uint32_t n);   /* audio ISR: fill n=256 stereo frames @ 44.1 kHz */
void app_main(void);                        /* main loop; must call platform_poll() */
```

- 256 interleaved stereo frames ≈ 5.8 ms per callback; keep the DSP under **2.9 ms**
  (50%). Output is Q15 ±32767; the platform clips/scales after the app.
- Raw registers live in `firmware/hal/` only; the app and DSP call `fm1_*` helpers.
- **Dual-core is the default:** CPU0 owns boot/platform/USB/flash/panel/recovery,
  CPU1 owns the DSP render. A boot-time core-1 probe detects the `0x00200000`
  misread and, on failure, the same firmware renders on CPU0 (a stability fallback,
  not a second build).
- **FPU:** single-precision only (no `double`). `--dsp float` is the opt-in path
  (still unwired as of P2-4); the shipped default is integer.
- **Clock is bootloader-dependent** (V13 app 240 MHz, V15 bootloader 360 MHz, V16
  bootloader 320 MHz); `--clock` offers **240 / 320** only. RIB reports the measured
  clock and never sets it by default; power-cycle after any change.

**Checkpoint:** you can state the contract, the dual-core split, the FPU rule, and
the clock rule. Change nothing yet.

## 6. Design the instrument

Design before code. Run the design interview and record it in the templates (copy
them into your project, replace the prompts):

- [`templates/synth-brief.md`](../templates/synth-brief.md) — the instrument, the
  voice architecture (node/macro graph), the parameter manifest, and tables.
- [`templates/control-map.md`](../templates/control-map.md) — the GUI: context
  stack, pages, bindings, and the full control flow.
- [`templates/project-plan.md`](../templates/project-plan.md) +
  [`templates/feature-contract.md`](../templates/feature-contract.md) +
  [`templates/supported-load-profile.md`](../templates/supported-load-profile.md)
  + [`templates/evidence-matrix.md`](../templates/evidence-matrix.md) — the plan,
  contracts, budget, and verification.
- [`templates/dsp-algorithm.md`](../templates/dsp-algorithm.md) — the exact
  algorithm per component (researched; credit + licence recorded).
- [`templates/code-structure.md`](../templates/code-structure.md) — the exact
  structure + interface of any custom code.

The [development skill](../skills/umetate-development/SKILL.md) drives this
interview and its consistency gate: every GUI binding must target a defined
parameter, every control mapped or explicitly unmapped, and the voice count ×
architecture must fit the budget (CPU0 `.data`/`.bss` ≤ 96 KiB, CPU1 `.cpu1_bss`
≤ 16 KiB, `.dsp_text` ≤ 32 KiB, `.pool` ≤ 336 KiB, XIP ≤ 568 KiB).

**Checkpoint:** the brief + control map + plan are complete, mutually consistent,
and confirmed. No code yet.

## 7. Author the synth

Translate the design into a patch — not design, translate. Inspect the shipped
node library, scaffold a starter, then fill it in:

```sh
umetate lib                 # the shipped nodes + templates (local only)
umetate scaffold patch --name "My Synth" --out examples/my-synth
```

The generator AOT-compiles `patch.json` (+ `panel.json`) to the invariant
`<synth>_dsp_*` seam. The nodes are `phasor`, `osc`, `noise`, `env`, `one_pole`,
`vca`, `mix`, `delay1`, `delayN`; `delay1`/`delayN` are the only cycle-breakers (the
graph is a DAG). A power user may hand-write `dsp.c` against the same seam as an
escape hatch. The patch's `params:` section binds friendly names to flattened
`<instance>.<param>` ids; `tables:` adds `const` XIP tables. See
[`templates/scaffold/patch.schema.json`](../templates/scaffold/patch.schema.json)
and the worked example [`examples/pocket-drone/patch.json`](../examples/pocket-drone/patch.json).

Work in **small, measured increments — one decision-set per increment** (the
smallest change that is a coherent, verifiable unit). After each, run the full
gate and **commit with the brief/plan/roadmap updated in the same commit**. Never
batch unrelated decisions, and never implement before the design is confirmed.
Prove each increment:

```sh
umetate deep-check --host
```

**Checkpoint:** a host test produces bounded, non-silent output and a release to
silence; the patch builds. Add a node to `modules/nodes/` only when a shipped node is
genuinely insufficient.

## 8. Controls, MIDI, screen, storage

Map only controls the hardware actually exposes (read the `BTN_*`/`ENC_*` enums in
`firmware/src/platform.c`). Fill `panel.json` from the control map: contexts own
their pages and bindings; global bindings (keys → note-on, MASTER → volume) resolve
last. Widgets are abstract (`label`, `value`, `bar`, `param_row`, `list`, `grid`).

Know each control's **kind** before binding it: a smooth analog *pot* (the FM-1's
`MASTER`) is volume and platform-owned — never bind it to a page slot; a detented
*encoder* is a parameter control. Distinguish *dedicated* knobs (`ALGORITHM`,
`PRESETS`) from *page-slot* knobs (`KNOB1–4`), and note name collisions (`SELECT`
knob vs `SEL` button). Respect the silkscreen — a printed label fixes a control's
meaning. Use the keybed as a menu surface (keys as operator/mute shortcuts), and
prefer the **page-slot model**: a few encoders whose meaning changes per page, with
the labels shown on screen (the screen says what the knobs do).

Draw the **menu tree** up front — every context (menu), its pages, and the *modes*
within a page — before you fill the bindings; a fresh reader must be able to draw
the screen for every state. Design **multi-timbrality** (`parts:`) and the **MIDI
specification** (channels, the `cc → param` map, sustain/panic/bend, program
change) in the same interview — they are engine and control-map concerns, not
afterthoughts.

Rules: the audio callback does no display, flash, logging, blocking, or allocation;
publish shared values with one writer or a snapshot protocol; draw only what
changed. Persist versioned records with CRC/commit, saving when silent.

**Checkpoint:** controls map to documented ids; held notes survive a redraw (host
UI test first). Device checks remain `blocked`.

## 9. Test

Run the narrowest checks first, then widen:

```sh
umetate lint --c             # the C standing checks
umetate deep-check --host    # host tests
umetate deep-check --web     # wasm + host == wasm parity
umetate emu --check          # the emulator headless shot (a model layer)
umetate build --board fm1 --model pro   # a target package
```

Record each layer in [`templates/evidence-matrix.md`](../templates/evidence-matrix.md)
and validate it with `umetate evidence --strict`. The emulator is a model layer
(1.92× optimistic on timing; it cannot prove recovery, FPU, core-1 stability, or
electrical behaviour). A target package is not physical timing; a host test is not
device acceptance.

**Checkpoint:** every must-have feature has a test matrix; host/browser/target
evidence is recorded; device layers are `blocked`.

## 10. Install — only when ready (hardware)

Device-only. Before any write, confirm the exact board/revision, current firmware
identity, a verified package (`umetate inspect`), a named rollback (verified stock
`.fwsc`), and a named recovery route. Then, with explicit approval:

```sh
umetate flash firmware/build/umetate-fm1-pro.fwsc --device
```

`flash` requires `--device` and an interactive confirmation; a wrong-model device
exits 6. `debrick` names the recovery routes (its `mask-rom` route is `blocked`
until the USB_KEY dongle is ready). A build, test, or edit is never permission to
write hardware.

**Checkpoint:** the install plan names the board, identity, rollback, and route.
The write itself is `blocked` until hardware and approval exist.

## 11. Validate on device (hardware)

Device-only and `blocked` here: audio, MIDI, USB, stress under the supported-load
profile, power-cycle, and recovery. Record board/revision, firmware/package, steps,
and unresolved risks. A device record is the only thing that proves device
acceptance.

## 12. Troubleshoot and recover (maybe)

Recovery is a taxonomy, not one button — see
[`docs/platform-facts.md`](platform-facts.md) §4: app-level USB rescue, the boot
guard, boot-time `OCT−`, running `OCT−`+`OCT+` held 5 s, the update loader
(`ota-<identity>`), and mask-ROM UBOOT via the USB_KEY dongle. There is no "three
short flashes" and no full-flash backup; if you cannot name the route and its
prerequisite, stop.

## 13. Record evidence and release provenance

Record the evidence matrix and, if a release is requested, the source/package
correspondence, licences/notices, version, and reproducible inputs. Publication is
a separate, explicit request. The baseline is **not** "security-clean" while the
`SEC-1` USB endpoint validation is blocked on hardware.
