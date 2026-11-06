# Build a synthesizer for the M-VAVE FM-1 / SMK-37

This tutorial is for programmers who know what they want an instrument to sound
like but are new to the FM-1, embedded audio, or umetate. You start from the
source-built **RIB** firmware, design an instrument, prototype its sound, then
build and verify the firmware in small steps. Stages 1–9 need no hardware, so
installation begins at stage 10.

> **Safety and evidence.** Never flash as a side effect of editing code. Identify a
> real recovery route before installing. Source, host, browser, target package,
> emulator, timing, and device acceptance are separate evidence layers, with a lower
> layer never proving a higher one. Use `pass` / `fail` / `blocked` / `not-run`.

## The 13 stages

| § | Stage | Outcome | Evidence layer | Hardware |
| --- | --- | --- | --- | --- |
| 1 | Umetate and RIB. RIB as the runtime, the framework on top | correct mental model | docs | no |
| 2 | Safety before hardware (hard-brick risk, backup limits, recovery) | informed consent + a backup plan | docs | no |
| 3 | Verify the environment (`umetate quick-check`) | a green/blocked report | host | no |
| 4 | Build untouched RIB, host tests, browser lab | first sound in the browser | host/browser | no |
| 5 | Firmware contract (`app_audio`, `app_main`, `platform_poll`, HAL) | a correct app skeleton | source | no |
| 6 | Design the instrument (brief, feature contracts, load profile) | a bounded design | docs | no |
| 7 | Author the synth (nodes/macros/patches, or hand-written `dsp.c`) | a working voice | host | no |
| 8 | Controls, MIDI, screen, storage | a playable instrument | host/browser | no |
| 9 | Test (host, browser parity, target package, fm1-emu, evidence) | a recorded evidence set | host/target | no |
| 10 | Install (identity, backup, installer, verify) | a safe install plan | docs | yes |
| 11 | Validate on device (audio, MIDI, USB, stress, recovery) | a device record | device | yes |
| 12 | Troubleshoot and recover (route taxonomy) | a known recovery path | docs/device | maybe |
| 13 | Record evidence and release provenance | a traceable release | release | no |

Each stage names its evidence layer and says whether hardware is needed. Only a
real FM-1 or SMK-37 can establish target timing or device acceptance, so
installation also requires separate approval and checks for backup, power, device
identity, and recovery.

## Core commands

```sh
umetate quick-check         # verify the environment per layer (read-only)
umetate setup --dry-run     # see exactly what would be installed (opt-in)
umetate deep-check          # run the host-side checks (default: --host)
umetate build --board fm1 --model pro   # a target package -> .fwsc (no flash)
umetate status              # the per-phase status ledger
```

For current project status, use [`docs/roadmap.md`](roadmap.md). The evidence-tagged
hardware facts (clock, cores, FPU, flash, and recovery) are in
[`docs/platform-facts.md`](platform-facts.md). The firmware API and coding rules
are in [`firmware/README.md`](../firmware/README.md).

---

## 1. Umetate, RIB, and the synth framework

**umetate** helps you design, build, test, and safely install custom firmware on
the M-VAVE **FM-1** and **SMK-37** (Pro/Elite/MKE-P37). Your instrument runs on
**RIB** (Rigid Inflatable Boat), a dual-core starter firmware derived from
Dinghy/Felucca, and the framework sits on top: you describe the synth with nodes,
macros, and patches, describe its UI with a panel and contexts, then let the
generator compile them and the parameter table into the `<synth>_dsp_*` interface.

The architecture has two parts, which I've kept visible through the stages. The
**composition model** turns nodes into macros, patches, panels, and firmware, whilst
the **development loop** takes each design through a small implementation, tests it,
verifies the result, and commits the change. [`docs/roadmap.md`](roadmap.md)
§6.12–§6.13 defines both, and this tutorial puts them into practice.

The framework has one entry point, `umetate`, and these pieces behind it:

1. **CLI**, `quick-check`, `setup`, `build`, `emu`, `deep-check`, `inspect`,
   `flash`, `debrick`, `scaffold`, `lib`, `lint`, `fmt`, `web-build`, `web-serve`,
   `evidence`, `status`, `version`, `help`.
2. **Skill: development**, the design → build loop (offline references).
3. **Skill: safety**, threat model, attack surfaces, device-write gates.
4. **Docker image + volume**, a pinned Linux container, with the JieLi toolchain in
   the `umetate-target` volume at `/opt/jieli` (read-only for builds, read-write
   only for `setup`).
5. **RIB starter firmware**, dual-core, integer-first DSP, FPU opt-in, SMK-37
   board layer, the `app_audio`/`app_main` contract.
6. **Tutorial**, this document.
7. **Start guide**, [`README.md`](../README.md).

**Checkpoint:** you can distinguish umetate from RIB and know which command to
run first. No tools have been installed yet.

## 2. Safety before hardware

A failed flash can hard-brick the device. The FM-1 has a single 1 MiB flash bank,
no recovery button, no test pads, and no debug header. Before writing anything,
identify both a recovery route and a rollback image. The FM-1 has no documented
full-flash backup, so rollback means a verified stock `.fwsc` and a recovery
route that applies to the failure.

I implore you to read this stage carefully. Take notes if it helps.

Read the recovery taxonomy at [`docs/platform-facts.md`](platform-facts.md) §4 and
the device-write gates in the [safety skill](../skills/umetate-safety/SKILL.md).

A build, test, or edit never authorises a hardware write by itself: every `flash` or `debrick`
requires an explicit request, a recorded identity, a verified package, a named
rollback, and a named recovery route.

**Checkpoint:** you can state the hard-brick risk and the recovery taxonomy before
touching a device. You will not flash in this tutorial's no-hardware stages.

## 3. Verify the environment

The pinned Docker container runs target builds, host tests, and the WASM build, and
on Windows umetate calls Docker Desktop through native `docker.exe`. The JieLi
toolchain and SDK are in the `umetate-target` volume, so `umetate setup` installs
them there when you opt in, after checking their hashes against
[`env.lock`](../env.lock).

```sh
umetate quick-check         # read-only presence/version probe per layer
umetate setup --dry-run     # see exactly what would be installed, nothing written
```

`quick-check` reports each evidence layer, and a missing toolchain shows as
`blocked` rather than `fail`. When you're ready to build for the target, run
`umetate setup` and approve installation of the JieLi toolchain and SDK into the
volume. Setup also installs Rust and the `fm1-emu` emulator. `--no-emulator`
skips the emulator if you want.

**Checkpoint:** `quick-check` shows `source`/`host` as `pass` and `target`/`device`
as `blocked` (or `pass` for target after `setup`).

## 4. Build untouched RIB, host tests, browser lab

First, build and test the untouched baseline:

```sh
umetate deep-check --host   # host DSP/UI/unit tests
umetate web-build           # emscripten -> standalone dsp.wasm
umetate web-serve           # loopback static server (build/web/)
```

The container runs host tests that check for bounded, non-silent output, and the
browser lab in `build/web/` runs the same pure DSP in an AudioWorklet, so you can
listen locally. Neither check establishes FM-1 timing, panel ergonomics, DMA
behaviour, flash safety, or recovery.

Get the browser lab making noise before you touch synth code. That gives you a
known-good baseline to compare against.

To produce a target package, which still does not flash anything and needs the
toolchain from stage 3, run:

```sh
umetate build --board fm1 --model pro --profile perf
```

Available flags are `--board fm1|smk37`, `--model pro|elite|mke` (Elite and MKE
require `--board smk37`), `--dsp integer|float`, `--clock 240|320`, and
`--profile baseline|perf`. The package, such as `umetate-fm1-pro.fwsc`, is written
to `firmware/build/`. Inspect it with `umetate inspect` to check its identity,
model, and CRC.

**Checkpoint:** the host tests pass, the browser produces sound, and a target
package builds with the SDK asset hashes verified. A package does not prove
device acceptance.

## 5. Firmware contract

The framework (`firmware/src/rib.c`) provides the platform and the synth services,
and your app supplies the glue (see [`firmware/README.md`](../firmware/README.md)
§1):

```c
static void app_audio(int32_t *out, uint32_t n);   /* audio ISR: fill n=256 stereo frames @ 44.1 kHz */
static void app_main(void);                        /* main loop; must call platform_poll() */
static void app_idle(void);                        /* runs while the screen draws (MIDI in) */
```

`umetate build --synth <dir>` composes the framework, the generated engine, and
your `app.c` glue into the firmware, so you never hand-write the platform half.

These are the rules I'd keep in mind for the rest of the build.

- Each callback handles 256 interleaved stereo frames and lasts about 5.8 ms, so
  keep DSP work below **2.9 ms**, which is half the callback period. Output uses
  Q15 (±32767), and the platform clips and scales it after the app returns.
- Raw register access belongs in `firmware/hal/`, whilst the app and DSP use
  `fm1_*` helpers instead.
- **Dual-core is the default.** CPU0 handles boot, platform services, USB, flash,
  the panel, and recovery, whilst CPU1 renders audio. A boot-time probe checks for
  the `0x00200000` core-1 misread, and if it fails, the same firmware renders on
  CPU0, so the fallback does not require a separate build.
- **FPU:** the hardware supports single precision only, so keep `double` out of
  the DSP. `--dsp float` is the opt-in path, though it is not yet wired in (P2-4),
  and integer DSP remains the default.
- **Clock:** the bootloader determines the clock, with the V13 app at 240 MHz, the
  V15 bootloader at 360 MHz, and the V16 bootloader at 320 MHz. The `--clock`
  option offers only **240 or 320 MHz**. RIB reports the measured clock and does
  not change it by default. Power-cycle after changing it.

**Checkpoint:** you can state the contract, the dual-core split, the FPU rule, and
the clock rule. Change nothing yet.

## 6. Design the instrument

Finish the design before writing code, then work through the design interview and
record the decisions in copies of these templates:

- [`templates/synth-brief.md`](../templates/synth-brief.md), the instrument, the
  voice architecture (node/macro graph), the parameter manifest, and tables.
- [`templates/control-map.md`](../templates/control-map.md), the GUI: context
  stack, pages, bindings, and the full control flow.
- [`templates/project-plan.md`](../templates/project-plan.md) +
  [`templates/feature-contract.md`](../templates/feature-contract.md) +
  [`templates/supported-load-profile.md`](../templates/supported-load-profile.md)
  + [`templates/evidence-matrix.md`](../templates/evidence-matrix.md), the plan,
  contracts, budget, and verification.
- [`templates/dsp-algorithm.md`](../templates/dsp-algorithm.md), the exact
  algorithm per component (researched, credit + licence recorded).
- [`templates/code-structure.md`](../templates/code-structure.md), the exact
  structure + interface of any custom code.

The [development skill](../skills/umetate-development/SKILL.md) guides the
interview and checks that the artefacts agree. Every GUI binding must point to a
defined parameter, and every control needs an account: either a mapping or a
reason it is unused. The voice count and architecture must also fit the resource
limits, with CPU0 `.data`/`.bss` ≤ 96 KiB, CPU1 `.cpu1_bss` ≤ 16 KiB,
`.dsp_text` ≤ 32 KiB, `.pool` ≤ 336 KiB, and XIP ≤ 568 KiB.

DON'T rush it! The brief, control map and plan are what the rest of the work gets
checked against. If you don't know exactly what you're coding, you'll have to do a
lot of backtracking, and you might end up giving up or shipping a load of slop.
Write it all down on paper if that helps.

**Checkpoint:** the brief + control map + plan are complete, mutually consistent,
and confirmed. No code yet.

## 7. Author the synth

Translate the confirmed design into a patch. I'd start by inspecting the shipped
nodes and scaffolding a project:

```sh
umetate lib                 # the shipped nodes + templates (local only)
umetate scaffold patch --name "My Synth" --out examples/my-synth
```

The generator compiles `patch.json` and `panel.json` ahead of time into the stable
`<synth>_dsp_*` interface, and the shipped library, which you can list with
`umetate lib`, covers oscillators (`phasor`, `osc`, `naive_osc`, the band-limited
`saw`/`pulse`/`triangle`, phase shaping), envelopes (`env`, `dx_env`), filters,
gain/VCA, and routing.

> **Anti-aliasing warning.** A raw table-based square/saw/pulse aliases at high
> pitches: its above-Nyquist harmonics fold back as inharmonic, warbly "ghost"
> partials that no filter can remove. The `naive_osc` node is non-band-limited *by
> design*, so for clean top octaves use the polyBLEP `saw`/`pulse`/`triangle`, or the
> `osc` node's mip-mapped pulse/square/saw (waves 9-11, six band-limited levels
> each, selected automatically from the note's increment). Sine-derived shapes
> (the OPZ set, `osc` waves 0-8) are already band-limited and need no treatment.

The two delay nodes are the only way to break a cycle, so without them the graph is
a DAG. If you need to, you can write `dsp.c` by hand against the same interface. In
the patch, `params:` maps readable names to flattened `<instance>.<param>` IDs,
whilst `tables:` adds `const` tables stored in XIP. See the
[`patch.schema.json`](../templates/scaffold/patch.schema.json) and the worked
[`type-p-fm1` patch](../examples/type-p-fm1/patch.json).

### Reading the patch and panel JSON

The patch and the panel are plain JSON, so you can read them and edit them by
hand. Here is what each part means. The schemas are the authority:
[`patch.schema.json`](../templates/scaffold/patch.schema.json) and
[`panel.schema.json`](../templates/scaffold/panel.schema.json).

**`patch.json` is the instrument.** Top level:

- `name` is the machine name, lowercase with no spaces. Hyphens and dots
  become underscores in the generated C names, so `type-p-fm1` becomes
  `type_p_fm1_*`.
- `voices` is the voice count.
- `macros` are named subgraphs you can reuse. A macro lists `ins`, `outs`,
  `params`, `nodes`, and `wires`, exactly like a zone below.
- `voice` is the per-voice graph, run once per voice per sample. `nodes` are
  instances, each an `id` plus a `type` (a node or a macro name). `wires` connect
  `<instance>.<port>` to `<instance>.<port>`. `voice_out` names the one voice
  signal summed into the global bus.
- `global` is the shared graph, run once per block. The word `voice` is a reserved
  wire source for that summed voice signal.
- `params` bind a friendly name to a flattened `<instance>.<param>` target, plus
  min, max, default, curve, unit, and the on-screen `display` form.
- `tables` are const wavetable, segment, and routing data stored in flash.

A wire has a `from` and a `to`. A `from` is a port, an `<instance>.<port>`, or a
reserved voice source (`gate`, `velocity`, `trigger`), and a `to` is always an
`<instance>.<port>`. The graph is a DAG, and only the two delay nodes can break a
cycle.

**`panel.json` is the screen.** Top level:

- `name` and `home`, the context you land in on boot.
- `global`, the always-on bindings, resolved last.
- `contexts`, a map of mode name to `pages` and `bindings`.

A binding has a `source` (a control like `ENC_KNOB1`, or MIDI `cc:N`) and one of
three things: a `target` (the param to write), an `action` (push a context, save,
panic), or a `slot` (the Nth param on the current page). A widget is a `label`,
`value`, `bar`, `param_row`, `scope`, `spectro`, or `envelope`, placed by
`row` and `col`.

The panel is a description of the screen. The generator emits the wiring, and a
retained-mode redraw engine draws it, so you edit the JSON and never write drawing
code.

Work in **small, measured increments**, with one decision-set in each, and keep
every change coherent and verifiable. After each increment, run the full gate and
**commit the code with the brief, plan, and roadmap updated alongside it**. Do not
bundle unrelated decisions, and do not start implementation before the design is
confirmed.

Verify each increment with:

```sh
umetate deep-check --host
```

**Checkpoint:** a host test produces bounded, non-silent output and a release to
silence, and the patch builds. Add a node to `modules/nodes/` only when a shipped
node is genuinely insufficient.

## 8. Controls, MIDI, screen, storage

Map only controls that exist on the hardware, and check the `BTN_*` and `ENC_*`
enums in `firmware/src/platform.c`. Use the control map to fill out `panel.json`:
each context owns its pages and bindings, and global bindings (such as keys to
note-on and MASTER to volume) resolve last. The UI uses abstract widgets such as
`label`, `value`, `bar`, `param_row`, `list`, and `grid`.

Identify each control before assigning it. The FM-1's smooth `MASTER` pot is
platform-owned volume, never a page slot, whilst the detented encoders change
parameters. Keep dedicated knobs (`ALGORITHM`, `PRESETS`) distinct from page-slot
knobs (`KNOB1–4`), and remember that the `SELECT` knob and the `SEL` button are
different controls. Printed labels are constraints, so `ALGORITHM` should still
control the algorithm. The keybed can also serve as a menu surface, for example as
operator or mute shortcuts. Prefer the **page-slot model**: a small set of encoders
controls the parameters on the current page, whose labels appear on screen.

Popups are **modal**: while one is open (name editor, save, part chooser, page
copy), it **captures all control**, so the page's encoders and the preset browser
stay inert and any events are drained, which keeps a twist during the popup from
firing once it closes. Modal popups **auto-close after ~3 s of no input** without
committing, and commits show a brief "SAVED/COPIED SUCCESSFULLY" acknowledgement.

Draw the **menu tree** before filling in bindings, with every context, its pages,
and any modes within a page, so that someone else can sketch the screen for every
state. Decide on **multi-timbrality** (`parts:`) and the **MIDI specification**
(channels, CC-to-parameter mapping, sustain, panic, bend, and program change)
during the same interview, because both affect the engine and the control map.

The MIDI spec is now part of the framework rather than the app glue. The fixed CC map is the patch's `cc:`
list: the params you declare there get one CC each, ascending from 16 (sustain 64
and the channel-mode block stay reserved), and a 7-bit CC value is scaled to the
param's full `[min, max]`. A multitimbral patch's params overflow the CC space, so
the list is the deliberate surface (the test project maps part 0's timbre + the
global FX). Notes route to the parts by channel + keyzone, sustain defers note-offs,
CC 123 is panic, and bend is ±2 semitones, all shipped in `synth_midi`. Presets
are 128 single parts + 64 multi patches (chunked across the slot area's measured
ceiling) plus one settings record, the firmware answers the five SysEx commands
over the shared envelope, and `umetate preset export/import` moves the bank as
`.syx`.

Your project then needs only the **app glue**: `app.c` with `app_audio` (call the
generated `<synth>_dsp_render`), `app_main` (keys + panel + the service polls +
silent-only saves), `app_idle`, the `ui_act_*` hooks, and the three service
contexts (`synth_midi_ctx`, `synth_sysex_ctx`, `synth_runtime_ctx`). The frozen
framework (`src/rib.c`) provides everything else, and
`umetate build --synth examples/<your-synth>` composes it. See
`examples/type-p-fm1/app.c` for the worked glue.

Keep display work, flash access, logging, blocking calls, and allocation out of the
audio callback. Give each shared value one writer, or use a snapshot protocol. On
the UI side, draw only what changed. Save versioned records with a CRC and commit
rule, and write them while the instrument is silent.

**Checkpoint:** controls map to documented ids, the `cc:` list names the CC
surface, `build --synth` composes, and the host leg renders sound on cue (held
notes survive a redraw). Device checks remain `blocked`.

## 9. Test

The gate is one command, so I'd run it after every increment:

```sh
umetate deep-check --all                       # mypy + ruff + pyright + the test modules + host + skill + links + lint
umetate budget patch.json --voices 20           # the measured polyphony figure
umetate build --synth examples/my-synth        # compose + host run + target package
umetate emu --check --mhz 240                  # boot the built package, hold a chord
umetate preset export examples/my-synth        # the bank as .syx (import reverses it)
```

`build --synth` writes the generated engine/panel/CC/layout files into
`firmware/gen/`, host-builds the composition and runs your `host-script.txt`
(WAV + screen shots, and a silent run fails the gate), then packages the firmware
through the JieLi toolchain (`umetate-fm1-pro-<synth>.fwsc`). Without the
toolchain it reports the target leg blocked and stops at the host evidence.
`emu --check --mhz 240` boots that package in the emulator and holds a chord: the
test project run never halts and peaks at full scale, so the polyphony fit is
measured rather than estimated.

Record the results in the
[`evidence matrix`](../templates/evidence-matrix.md) and validate them with
`umetate evidence --strict`. The emulator is only a model: its timing is 1.92×
optimistic, and it cannot establish recovery behaviour, FPU operation, core-1
stability, or electrical behaviour. A target package does not prove physical
timing, and host tests do not establish device acceptance.

**Checkpoint:** every must-have feature has a test matrix, host/emulator/target
evidence is recorded, device layers are `blocked`.

## 10. Install: only when ready (hardware)

This stage requires the device. Before writing, confirm the board and revision,
current firmware identity, verified package (use `umetate inspect`), rollback image
(verified stock `.fwsc`), and recovery route. Get explicit approval before running:

```sh
umetate flash firmware/build/umetate-fm1-pro.fwsc --device
```

`flash` requires `--device` and interactive confirmation, and it exits with code 6
if the model does not match. `debrick` lists the recovery routes, though its
`mask-rom` route remains `blocked` until the USB_KEY dongle is available. Building,
testing, or editing never grants permission to write to hardware.

**Checkpoint:** the install plan names the board, identity, rollback, and route.
The write itself is `blocked` until hardware and approval exist.

## 11. Validate on device (hardware)

This stage also requires hardware and remains `blocked`. Test audio, MIDI, USB,
stress under the supported-load profile, power cycling, and recovery. Record the
board and revision, firmware and package, test steps, and any unresolved risks.
Only a device test record can establish device acceptance.

## 12. Troubleshoot and recover

Recovery is not one button, since each route has its own prerequisites (see
[`docs/platform-facts.md`](platform-facts.md) §4). Options include app-level USB
rescue, the boot guard, boot-time `OCT−`, holding `OCT−` and `OCT+` for five
seconds while running, the `ota-<identity>` update loader, and mask-ROM UBOOT via
the USB_KEY dongle. There is no "three short flashes" route and no full-flash
backup. If you cannot identify a route and confirm its prerequisites, stop.

## 13. Record evidence and release provenance

Keep the evidence matrix with the release record. If a release is requested,
record which source produced each package, along with licences and notices, the
version, and reproducible inputs. Publishing requires a separate explicit request.
Do not describe the baseline as **security-clean** while `SEC-1` USB endpoint
validation remains blocked on hardware.
