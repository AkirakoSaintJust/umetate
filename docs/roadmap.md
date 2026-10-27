# umetate — Architecture & Implementation Roadmap

**Project:** umetate — a simpler, clearer, better toolkit for building custom
M-VAVE FM-1 / SMK-37 firmware, inspired by (but independent of) fm1tk.
**Author:** P1Onken. **Licence:** GPL-3.0-only. **Status authority:** this file
(`docs/roadmap.md`). **Date:** 2026-10-25.

This document is the single source of truth for the design and the order of
work. It is meant to be executable top to bottom by a fresh agent with no prior
context, leaving nothing to chance. Spare prose; one fact lives in one place.

---

## 1. Decisions (settled)

| # | Topic | Decision |
| --- | --- | --- |
| D1 | Name / authorship | `umetate`; commits credited to P1Onken; not endorsed by M-VAVE. |
| D2 | Starter firmware (RIB) | Dinghy/Felucca lineage, source-owned, integer-first C. Out of the box it supports **SMK-37**, **dual-core**, **single-precision FPU (opt-in)**, and the **JieLi acceleration hardware**. Performance + stability; extendible + maintainable. |
| D3 | Dual-core | **Default and the only architecture.** CPU0 = platform/OS/USB/MIDI/UI/flash/watchdog/installer; CPU1 = DSP render only. A boot-time core-1 probe + runtime fallback to CPU0 is the *stability* net, not a build profile. |
| D4 | FPU | **Opt-in** (`--dsp float`). Single-precision only; `double` prohibited; only the DSP translation unit uses FP. |
| D5 | Clock | Setup offers **240 MHz or 320 MHz**. 360 MHz and 396 MHz are not offered (see §5.1). Firmware reports the measured clock; never assumes. |
| D6 | On-device identity | **Frozen**: `FM-1_990`, `SMK-37 Pro_990`, `SMK-37 Elite_990`, `MKE-P37_990`. Rename artifacts freely; never rename identity. |
| D7 | CLI device writes | The CLI drives flash/debrick **directly** (`flash`, `debrick`), always behind explicit approval + recovery/backup gates; never as a build/test side effect. |
| D8 | Document set | **Five canonical docs** (see §4.6) + one firmware-internal `firmware/README.md` + JSON schemas (artifacts). |
| D9 | Skills | Two skills (development, safety); each **bundles its references offline**. |
| D10 | Web target | A **WASM parity lab** (web-synth style) + **fm1-emu** as the separate pre-hardware model layer. |
| D11 | Build environment | **Docker-only**: pinned Linux dev container + a Docker volume holding the JieLi toolchain at `/opt/jieli`; Windows runs it via WSL2. |
| D12 | First install (stock device) | **Stock update entry** (primary) + **mask-ROM UBOOT / USB_KEY dongle** (fallback). |
| D13 | Update loader | **Custom source-owned loader** (`ota-<identity>`, Felucca/RIB lineage): on-device model check, resume, `.fwsc` + frozen `_990` preserved. |
| D14 | Flash execution | **Host-side installer** (USB CDC); build + package stay in Docker. |
| D15 | Debrick scope | **All routes**, incl. mask-ROM full-flash *write*. Full-flash *backup* never promised. |
| D16 | Firmware doc | **One `firmware/README.md`** (contract + chip rules + API + SMK notes). |
| D17 | C module granularity | **Minimal TUs**: `rib.c` + `rib_dsp.c` + `platform.c`, header-only `hal/`. |
| D18 | Lint/format | **clang-format + clang-tidy + custom Python safety checks** (`umetate lint --c`). |
| D19 | Framework model | **Angular-style opinionated framework**: nodes/macros/patches + an AOT generator. First law: zero runtime cost. |
| D20 | Module shape | Signal kinds `event`/`control`/`audio`; six-part base node; **one node = one algorithm, shape/spectrum = data**; `control` = block-rate, `audio` = sample-rate. |
| D21 | Hierarchy & authoring | **node / macro / patch**. The CLI scaffolds **all three** — defaults or custom DSP — **by hand or agentically** (like `ng generate`). `<synth>_dsp_*` is the invariant seam; hand-written `dsp.c` is an escape hatch. |
| D22 | Feedback | Graph is a **DAG**; `delay1` (1-sample) / `delayN` are the only cycle-breakers. FM/PM feedback = explicit `delay1` edge. |
| D23 | Modulation / events / data | Mod = a `modulatable` param's paired control input (base + mod·depth, block rate). Events carry `{kind, note, velocity}`. Shape data lives in the patch `tables:` section → `const` XIP arrays. |

---

## 2. Lessons carried over from fm1tk

The `/old-reference` project was over-engineered in places and under-decided in
others. umetate keeps the engineering discipline and drops the ceremony.

| fm1tk pain point | umetate response |
| --- | --- |
| ~15 canonical docs | **5 docs** + one `firmware/README.md` + schemas. |
| Two build systems / task names, legacy aliases | One CLI, one entry point, no migration shims. |
| Five build profiles + three knobs | **Two profiles** (`baseline`, `perf`) + two knobs (`--dsp`, `--clock`). Dual-core is not a knob. |
| FPU/dual-core/clock required but device-gated, stayed `blocked` | Dual-core default from day one; FPU opt-in; clock a two-way setup choice — each grounded in primary-source evidence. |
| A flat scaffold: the user hand-writes `dsp.c` + `params.json` | An **opinionated framework**: the user authors nodes/macros/patches; the generator emits the DSP. Hand-written `dsp.c` remains as an escape hatch. |
| Evidence vocabulary in every doc | Defined once in `platform-facts.md`. |
| Unity-build `-O2` USB-MIDI regression | DSP is a separate TU; platform/USB/loader pinned `-Os`; permanent regression check. |
| Emulator over/under-trusted | fm1-emu is a fixed model layer (1.92× optimistic). |
| "Three short flashes" etc. | Recovery is a taxonomy of named routes with prerequisites. |

The non-negotiable safety rules are preserved in full (§5.4, §8).

---

## 3. Product architecture (the seven components)

```text
umetate
├─ 1. CLI (`umetate`)              one entry point: quick-check, setup, build, deep-check,
│                                  inspect, flash, debrick, scaffold
│                                  (node|macro|patch), add, lib, lint, fmt, web, status
├─ 2. Skill: development           interview → brief → plan → scaffold/author →
│                                  verify (interactive loop, offline refs)
├─ 3. Skill: safety                threat model, attack surfaces, device-write gates
├─ 4. Docker image + volume        pinned Linux container; JieLi toolchain at /opt/jieli
├─ 5. RIB starter firmware         Dinghy-derived; dual-core default; FPU opt-in;
│                                  SMK-37; hardware-accelerated DSP
├─ 6. Tutorial (`docs/tutorial.md`) the learner path to the project standard
└─ 7. Start guide (`README.md`)     what to run, what the components are
```

Targets: **FM-1**, **SMK-37** (Pro/Elite/MKE-P37), **fm1-emu** (model layer), and
the **WASM parity lab** (local web app). All four are first-class.

### 3.1 The framework model — "the Angular of synthesizer firmware"

umetate is an **opinionated framework**, not a library of parts. The mapping:

| Angular concept | umetate equivalent |
| --- | --- |
| `ng generate component/service` | `umetate scaffold node|macro|patch --template` + `umetate lib list` |
| Components / services | **nodes** (typed DSP primitives) + **macros** (reusable subgraphs) + the platform API as compile-time "services" |
| Declarative template | the **patch** — a declarative signal graph |
| AOT compiler + tree-shaking + ivy | the **generator**: patch → SoA state + one fused monomorphic render + params table |
| Reactive state | the app is a pure function of (state, events); one-writer/snapshot |
| Batteries included | the **module library** (shipped, reviewed nodes) |
| CLI lint/format | `umetate lint` / `fmt` |

**The first law:** every framework feature must compile to **zero runtime cost** or
live in cold/control paths. The framework is compile-time + generator-time +
agent-time, never runtime.

**The module shape (see §6.9 and `templates/scaffold/*.schema.json`):**

- **Signal kinds:** `event` (note+velocity), `control` (block-rate scalar),
  `audio` (sample-rate stream). Ports are typed; the generator type-checks edges
  and splits the render into a control-rate prologue and an audio-rate loop.
- **Node** (primitive): one algorithm, conforming to a six-part base shape —
  typed ports, a params interface (`set_param`/`get_param`/`param_count`), a state
  manifest, and a `static inline <node>_process(ctx, n)` dsp core. **One node =
  one algorithm; shape/spectrum/envelope/transfer-function = data.**
- **Macro** (reusable subgraph): a named graph of nodes/macros with its own ports
  and params (mapped inward). E.g. `op` = phasor + osc + `delay1` feedback.
- **Patch** (the instrument): instantiates nodes/macros, wires them, declares
  `voice`/`global` zones (multiplicity) and a `tables:` section.
- **Feedback:** the graph is a **DAG**; `delay1`/`delayN` are the only
  cycle-breakers. FM/PM feedback is an explicit `delay1` edge — a per-sample *data
  dependency*, not a per-sample *dispatch*.
- **Modulation:** a `modulatable` param gets a paired control input `<param>_mod`
  and a depth param; effective value = base + mod·depth at block rate.
- **Shape data:** wavetables, segments, spectra, phase-maps live in `tables:` →
  `const` XIP arrays.
- **Events:** `{kind: note_on|note_off, note, velocity}`; nodes derive gate/trigger.
- **Multiplicity:** patch zones — `voice` = SoA × NVOICE, `global` = single.

**Authoring, by hand or agentically (like Angular):** the CLI scaffolds a default
node/macro/patch, which the user customizes — its DSP core, params, and graph —
either by hand or through the development skill. The `<synth>_dsp_*` API (§6.8) is
the **invariant seam**: the generator emits it from a patch, and a power user may
hand-write it directly as an escape hatch. Both produce the same shape that plugs
into RIB, host, and WASM via `app_audio`.

### 3.2 The UI layer — panel + contexts

The UI is the framework's "view + bindings" layer, parallel to the patch. Its core
guarantee: **a mode owns both its view and its control meaning, so they cannot
drift.** Modeled as a **context stack**:

- **Context (mode/menu):** a self-contained object with its **pages** (a menu is a
  multi-page context), its **bindings** (what controls/MIDI do here), and optional
  **on-enter/on-exit hooks** (save-on-exit, reset-on-entry).
- **Context stack:** contexts push/pop; the top is active.
- **Home context:** the base of the stack, booted into.
- **Boot screen:** an optional transient pre-context page (shown while boot
  completes), not a context.
- **Global bindings:** always-on, resolved last. A control resolves against the
  active context first, then falls through to global (MASTER = volume, transport,
  panic, MIDI notes → note-on).
- **Binding (unified):** `{source, target: <param> | action: <verb> [arg],
  behavior, curve}`. Hardware controls and MIDI CC/note are the same kind of
  source. "Keys play notes vs. do something else" = the home context's global
  `KEY → note_on` is overridden by a mode's `KEY → set_step`.
- **Widgets (abstract, not skeuomorphic):** `label`, `value`, `bar`, `param_row`,
  `param_column`, `list`, `grid`.
- **Redraw engine (the tested base):** retained-mode, dirty-tracking, rate-bounded
  (~30 Hz), `LCD_IDLE`-integrated, safe-failure screen; hard-wires the rule of no
  display/flash/logging in the audio callback.

Authoring mirrors the DSP layer: the CLI scaffolds a `panel.json` (declarative),
which the generator compiles to the app's UI wiring; a custom page can be
hand-written against the `cv_*` canvas API. See `templates/control-map.md` and
`templates/scaffold/panel.schema.json`.

---

## 4. Target architecture

There are **two layers**: the **RIB runtime** (the minimal C firmware the patch
runs on) and the **user framework** (nodes/macros/patches compiled *into* the
DSP translation unit). This section describes the runtime; §3.1/§6.8 describe the
framework on top of it.

### 4.1 Repository tree

```text
umetate/
├─ README.md                # component 7: project start guide
├─ LICENSING.md             # origin, attribution, licence manifest + deps
├─ LICENSE
├─ .clang-format  .clang-tidy  # formatting + lint contract (enforced)
├─ env.lock                 # pinned toolchain/SDK versions + hashes
├─ pyproject.toml           # `umetate` CLI package
├─ umetate/                 # CLI implementation (Python >=3.11)
│  ├─ cli.py                #   arg parsing, dispatch, help
│  ├─ quick_check.py setup.py build.py deep_check.py inspect.py
│  ├─ flash.py debrick.py scaffold.py lib.py
│  ├─ lint.py fmt.py web.py status.py evidence.py generate.py
│  └─ runner.py             #   WSL2/Docker POSIX shim
├─ firmware/                # component 5: RIB runtime (single firmware root)
│  ├─ README.md             #   the code-level contract (API + rules)
│  ├─ CMakeLists.txt  app.ld  crt0.S
│  ├─ src/                  #   rib.c (app), rib_dsp.c (DSP), platform.c (services)
│  ├─ hal/                  #   registers, flash map, math/FFT wrapper, SMK board layer (smk_input.h)
│  ├─ loader/               #   update loader
│  ├─ gen/  assets/
│  ├─ tests/                #   host tests, flash-map tests, security tests
│  └─ tools/                #   firmware-local build/package/install helpers
├─ modules/                 # module library: reviewed nodes (node.json + <node>.c + test)
├─ web-synth/               # WASM parity lab (local web app target)
├─ skills/
│  ├─ umetate-development/  # component 2 (SKILL.md + offline references/)
│  └─ umetate-safety/       # component 3 (SKILL.md + offline references/)
├─ templates/
│  ├─ synth-brief.md  project-plan.md  feature-contract.md
│  ├─ supported-load-profile.md  evidence-matrix.md
│  └─ scaffold/             # params.schema.json, node.schema.json, patch.schema.json, panel.schema.json
├─ docker/                  # component 4: Dockerfile, build.sh, compose, .env.example
├─ docs/
│  ├─ roadmap.md            #   THIS document (status authority)
│  ├─ platform-facts.md     #   hardware facts + device safety + recovery taxonomy
│  └─ tutorial.md           # component 6
└─ examples/                # worked example(s)
```

Hard rule: **one firmware root** (`firmware/`, no nesting), **one status
authority** (`docs/roadmap.md`), **one CLI entry point** (`umetate`). Generated
views (`gen/`, skill `references/`, `web-synth` artifacts, generated `dsp.c` and
param tables) are produced by a generator, never hand-edited.

### 4.2 Runtime ownership (dual-core — the only way)

| Core | Owns | Must not |
| --- | --- | --- |
| CPU0 | boot, OS/runtime, USB (MIDI + UAC), MIDI UART, panel/UI, display, storage/flash, watchdog, update installer, recovery | long DSP work; FP when CPU1 owns the FPU |
| CPU1 | DSP render: voice state, block production | OS calls (incl. `printf`), allocation, flash, USB, blocking |

- **CPU1 code lives in RAM** (`.c1_text`, its waiting loop) so it never fetches
  from flash while flash is busy (AC79 §7.40).
- **IPC:** the one-job mailbox (`fm1_c1_mb`, Felucca `fm1_cpu1.h`) for the render
  job; a SPSC note queue (`hal/fm1_ipc.h`, csync-guarded) for events; shared
  single-writer values for params/bend. `volatile` is never a multi-field atomic
  protocol.
- **Inter-core exclusion:** single-writer/single-reader mailbox + queue; no OS
  `spin_lock` (the SDK-OS model, AC79 §7.40, does not apply — RIB is bare-metal).
- **Flash park:** `fm1_cpu1_halt()` holds CPU1 before a flash write and in every
  reset path; it is not auto-resumed.
- **Boot probe + fallback:** a boot-time core-1 memory-integrity probe (the mailbox
  check word, which detects the `0x00200000` misread); on failure the same firmware
  renders DSP on CPU0 — a stability fallback, not a second build.

### 4.3 Build profiles (collapsed)

| Profile | DSP opt | Code placement | Use |
| --- | --- | --- | --- |
| `baseline` | `-Os` | flash XIP | size-first / debugging |
| `perf` (default) | `-O3` | hot DSP in SRAM (`.dsp_text` / `UMETATE_TARGET_DSP`) | performance-first, shipped default |

| Knob | Values | Default | Notes |
| --- | --- | --- | --- |
| `--dsp` | `integer` \| `float` | `integer` | `float` compiles only the DSP TU with FPU; `double` forbidden. |
| `--clock` | `240` \| `320` | `320` | chosen at setup; see §5.1. `--board fm1\|smk37`, `--model pro\|elite\|mke` orthogonal. |

Platform, USB, loader, and ISR code always compile at `-Os` (the known `-O2`
USB-MIDI regression is a standing constraint). The `--dsp` and `--clock` knobs
never transitively change non-DSP code through LTO or unity compilation.

### 4.4 Firmware contract

```c
void app_audio(int32_t *out, uint32_t n);   /* audio ISR: fill n=256 stereo frames @ 44.1 kHz */
void app_main(void);                        /* main loop; never returns; must call platform_poll() */
```

- 256 interleaved stereo frames ≈ 5.8 ms/callback; output is Q15 ±32767; the
  platform clips/scales after the app. Callback budget target: ≤ 2.9 ms (50%).
- No display, flash, logging, blocking, or allocation in the audio path.

### 4.5 Flash maps and protected ranges

Per-board authority: `firmware/hal/fm1_flash_map.h`. **The FM-1 and SMK-37 maps
differ; never copy one board's protected list to the other.**

| Board | Store window | OTA staging | Protected (never write) |
| --- | --- | --- | --- |
| FM-1 | data `0x97000–0xE0000` | `0xE0000–0xE5000` | head `0x0–0x3FFF`; `0xC1000` USRTRIM area; `0xFF000+` |
| SMK-37 | `0x9D000–0xBAFFF` (+ `0xC2000–0xE9FFF` samples) | `0xBB000–0xBFFFF` | `0x0–0x3FFF`, `0xC0000–0xC1FFF`, `0xF4000–0xFDFFF`, `0xFF000+` |

Every allowed range is `_Static_assert`-ed at compile time; the RAM flash driver
carries a second guard; the allow-list is never widened. On SMK work, `0xC1224`
must read `trimdat` after the work.

### 4.6 The canonical documents

| Document | Job | Status authority? |
| --- | --- | --- |
| `README.md` | what umetate is, components, first commands, repository map | No |
| `docs/roadmap.md` | this file: status + implementation plan | **Yes** |
| `docs/platform-facts.md` | evidence-tagged hardware facts + device safety + recovery taxonomy + evidence vocabulary | No |
| `docs/tutorial.md` | learner path from baseline to a custom synth | No |
| `LICENSING.md` | origin, attribution, licence + dependency manifest | No |

Plus one firmware-internal `firmware/README.md` (the code-level contract), the
JSON schemas (`templates/scaffold/*.schema.json`) — config/artifacts — and
`docs/dsp-study.md` (reference material: a DSP implementation study). None of these
is a canonical governance/status doc. Templates are fillable forms; skill
`references/` are offline copies; neither is a second source of truth.

---

## 5. Platform facts to encode (evidence-tagged)

`docs/platform-facts.md` owns these. Tags: `vendor`, `stock-code`, `source`,
`community-measured`, `unverified`.

### 5.1 SoC, clock, FPU, cores

- **SoC:** JieLi AC791N / WL82, dual-core pi32v2 DSP; family max **320 MHz**;
  **single-precision float only** (no `double`; literals `1.0f`); hardware
  **FFT/IFFT + matrix**, AES/SHA/CRC16/random; **578 KB SRAM** (+ optional SDRAM);
  USB1.1/2.0; DAC/IIS/PDM/SPDIF audio. `vendor`.
- **Clock is bootloader-dependent.** V13 app 240 MHz; V15 bootloader 360 MHz; V16
  bootloader 320 MHz. The setup offers **240 / 320** only: 320 is the rated max and
  passed a two-core 30-minute soak; 360 failed under load on one V15 unit; **396
  has no FM-1 evidence**. A soft reset keeps the PLL; power-cycle returns to the
  bootloader clock. `community-measured`.
- **Dual-core split (AC79 §7.40, SDK-OS model — a vendor fact only):** `CPU_CORE_NUM 1`
  + single-core `system.a` + explicit `irq_info_table`; CPU1 runs `cpu1_main`, may
  not call OS APIs; `spin_lock` for exclusion; flash write suspends CPU1 unless its
  code is in RAM/SDRAM. **RIB does not use this** — it is bare-metal (links no
  `system.a`): core 1 runs `fm1_c1_main` via the Felucca `fm1_cpu1.h` raw-register
  start. `vendor`.
- **FPU (AC79 §7.22):** single-precision hardware only. FM-1 enable/ABI/context is
  `not-run` until the target probe (P2-4). `vendor`.

### 5.2 Build/toolchain

- Linux toolchain → **`/opt/jieli`** (contains `/opt/jieli/common/bin/clang`),
  `ulimit -n ≥ 8096`, `make`. Linux *compiles*; flashing needs `init_env.sh` +
  `download_linux.c`. `vendor`.
- FM1 Open (flag authority): JieLi **Windows toolchain 2.5.3** (pi32v2 **clang
  4.0.1**, `-mcpu=r3 -mfprev1`, `-flto`); WASI SDK 27 for the web build. `stock-code`.
- Flash line: `isd_download.exe isd_config.ini -tonorflash -dev wl82 -boot 0x1c02000
  … -uboot uboot.boot -app app.bin cfg_tool.bin …` — boot address and SDK assets
  `uboot.boot`, `cfg_tool.bin` (plus `eq_cfg_hw.bin`). **SFC addresses only 16 MB.** `vendor`.

### 5.3 Math / acceleration (AC79 §7.16)

- Hardware FFT: `jl_fft.c` (hw) / `kiss_fft.c` (sw) / `flfft_core_pi32v2.c` (float).
  Vector DSP: `nn_function_vec.c` (saturating, `q`-shift) and `jl_math.c`
  (`ASM_ENABLE` 1=sw/2=asm/3=hw). Trig: `driver/cpu/wl82/math/math.c`. `vendor`. RIB
  wraps these behind `hal/fm1_math.h` with a software fallback for host/WASM parity.

### 5.4 Update, identity, recovery (safety core)

- `.fwsc` carries a 27-byte zero-padded identity, parsed `([^_]+)_(\d+)`.
  `same_keyboard` + model check on **install and resume**; wrong model exits 6.
- Updates are **CRC-16 integrity, not authenticity** — no signature.
- USB update mode enumerates as **`WL82 UBOOT1.00 USB Device`**; `WL80UBOOT`/
  `4C4A:8057` also observed.
- **Recovery is a taxonomy**, not one button:
  | Route | Prerequisite | Status |
  | --- | --- | --- |
  | App-level USB rescue | app startup + RAM flash driver + USB stack | source; device `blocked` |
  | Automatic boot guard | boot guard intact | source; device `blocked` |
  | Boot-time `OCT−` | held at power-on | source; did not fire on MD-One's unit |
  | Running `OCT−`+`OCT+` held 5 s | running firmware servicing `platform_poll()` | source + host test; device `blocked` |
  | Update loader (`ota-<identity>`) | app accepted package, record written | resumes interrupted write |
  | Mask-ROM UBOOT / USB_KEY dongle | USB enumeration / RP2040 dongle | community-reported; last resort; `blocked` (dongle at hand, pending a USB solder) |
- **No full-flash backup** is a documented FM-1 capability; rollback = verified
  stock `.fwsc` + the applicable route.
- **No "three short flashes."** No primary source supports it.

### 5.5 Evidence vocabulary (defined once)

`pass` / `fail` / `blocked` / `not-applicable` / `not-run`. Layers: source/static,
host, browser/WASM, target package, emulator, physical timing, device acceptance,
release provenance. **A lower layer never proves a higher one.** The emulator is a
model layer (1.92× optimistic; cannot prove recovery/FPU/core-1/electrical).

### 5.6 Boot & flash procedure (settled)

```text
Power on
  └─ Mask ROM (always present)
       ├─ no valid app / forced  → USB "WL82 UBOOT1.00 USB Device"  (brick-proof entry)
       └─ valid flash  →  UBOOT "uboot.boot"
            ├─ update record set  → ota loader "ota-<identity>"  → writes .fwsc, resets
            └─ no record          → APP (entry 0x2000120, XIP from 0x02000000)
```

- **UBOOT variant is load-bearing.** `uboot.boot` is single-bank-OTA-capable;
  `uboot_no_ota.boot` is not. Keep `uboot.boot` byte-identical to the pinned SDK.
- **Memory:** XIP `0x02000000+`; internal RAM `0x1c00000` (CPU1 DSP); cache RAM
  `0x1f28000`; boot info `0x1c7fd50`. FM-1 flash is **1 MiB** (board map in
  `fm1_flash_map.h`).
- **Clock tree @320:** sys `320`, sdram `192`, hsb `160`, lsb `53.33`, sfc `80` MHz.

| Path | Format | Entry | Runs |
| --- | --- | --- | --- |
| Update (primary) | `.fwsc` (CRC-16 + identity/model) | app rescue / chord / update record | **host-side Python installer over USB-MIDI SysEx** (mido + python-rtmidi) |
| Raw NOR (last resort) | `uboot.boot` + `app.bin` + `cfg_tool.bin` | mask-ROM UBOOT / burner | `isd_download` / `jl-uboot-tool`, via the **USB_KEY dongle** |

---

## 6. Component specifications

### 6.1 CLI (`umetate`, Python)

```text
umetate quick-check [--json] [--strict]        verify environment per evidence layer
umetate setup      [--no-emulator] [--dry-run] [--clock 240|320] [--json]   opt-in; toolchain+SDK into the volume, Rust + fm1-emu on the host
umetate build      --board fm1|smk37 [--model pro|elite|mke]
                   [--dsp integer|float] [--clock 240|320] [--profile baseline|perf]
umetate emu        [--board fm1|smk37] [--persist] [--midi NAME] [--check]   run your firmware in the fm1-emu GUI (or headless)
umetate deep-check  [--host|--web|--safety|--skill|--links|--all]
umetate inspect    PACKAGE                   inspect a .fwsc without a device
umetate flash      PACKAGE [--port NAME] [--device] [--yes]   flash; identity + CRC + model checked; resumes a device in update mode
umetate debrick    [--route app-rescue|update-loader|mask-rom] [--device]   recovery write (mask-rom: blocked, needs the USB_KEY dongle)
umetate scaffold   <node|macro|patch> --name NAME [--template T] [--out DIR]   generate a skeleton (optionally from a shipped template)
umetate lib        [list]                     list the shipped nodes + templates (local only)
umetate lint       [--c]                     C lint + static checks (bounds, ROM, MMIO, flash-busy)
umetate fmt        [--check]                 clang-format over the repo
umetate web-build  / web-serve               WASM build + a minimal manual browser harness
umetate status                              per-layer claim ledger parsed from docs/roadmap.md
umetate help [CMD]                           documents every option (component 1 requirement)
```

- `quick-check` is read-only; missing target toolchain is `blocked`, not `fail`;
  `--strict` turns non-device `blocked` into a failure exit.
- `setup` is opt-in, interactive, hash-pinned, never silent; records the clock choice;
  installs Rust + fm1-emu on the host (`--no-emulator` skips that).
- `scaffold` generates a **default** node/macro/patch (from the schemas, or
  `--template` copies a shipped template), which the user customizes — DSP core,
  params, graph — **by hand or agentically**. `lib list` shows the shipped nodes +
  templates. All of it can also be written by hand against the schemas. The module
  library is local-only — no remote registry.
- `flash`/`debrick` are the only device-writing commands, gated by §8,
  run on the **host** (USB CDC), never in the container.
- `lint` encodes the standing checks: MAXP bounds (`SEC-1`), UAC access (`SEC-2`),
  ROM-address constants, HAL-only MMIO, flash-busy call graph, no `double`/
  64-bit-div/allocation in DSP.

### 6.2 Skill: umetate-development

Offline-bundled interactive loop. Workflow: orient → design interview (player,
synthesis, controls, MIDI, persistence, browser, acceptance) → one brief → one plan
(feature contracts + supported-load profile) → environment/baseline → **author the
synth as nodes/macros/patches** (via `scaffold`, by hand or driven by the
agent) → first audible slice → shared DSP (host/browser/firmware adapters) →
panel/display → MIDI/persistence → verify (evidence matrix) → handoff. Refuses
device writes unless the user explicitly requests that action and §8 gates pass.

`references/` bundles (offline): AC79 facts, flash maps + protected ranges, the
port-kit mapping patterns, the node/macro/patch schemas, the recovery taxonomy, the
evidence vocabulary, the code conventions.

### 6.3 Skill: umetate-safety

Offline-bundled. Triggers on memory-safety review, USB/UAC/MIDI/OTA attack
surfaces, package identity, flash writes, and any device write. Maps each surface
(USB EP0/EP1/EP3, UAC tap/FIR/DMA, MIDI SysEx, OTA parser, update loader,
flash/store, package identity, host installer, build supply chain) to code, a test,
or an explicit gate. Owns the device-write gate (§8).

### 6.4 Docker image + volume

- Image (`umetate-host-build:latest`): Python 3.11+, Node 20+, Git, CMake 3.20+,
  Ninja, a C compiler, Pillow, Emscripten 6.0.13.
- Volume (`umetate-target`): JieLi pi32v2 toolchain + AC79 SDK assets
  (`uboot.boot`, `cfg_tool.bin`, `eq_cfg_hw.bin`), mounted read-only at `/opt/jieli`.
  **Not** baked into the image (vendor-terms compliance). `umetate setup` populates it:
  auto-fetch (toolchain from `pkgman.jieliapp.com`, SDK from gitee, both with opt-in
  consent) or a user-supplied path; version- + hash-verified against `env.lock`.
- Windows: everything through WSL2 → Docker.

### 6.5 RIB starter firmware

Dinghy/Felucca-derived, restructured for the dual-core/acceleration product
statement (§4.2, §4.3). Integer-first by default; FPU opt-in; hardware math via
`hal/fm1_math.h`; SMK-37 board layer out of the box.

### 6.6 Tutorial

`docs/tutorial.md` — the learner path (13 stages, hardware-optional until install):

1. What umetate is; RIB as the runtime; the framework on top of it.
2. Safety before hardware (hard-brick risk, backup limits, recovery, approval).
3. Verify the environment (`umetate quick-check`); Docker/WSL2 model.
4. Build untouched RIB; host tests; browser lab; first sound.
5. The firmware contract (`app_audio`, `app_main`, `platform_poll`, HAL).
6. Design the instrument (brief, feature contracts, supported-load profile).
7. **Author the synth** (nodes/macros/patches; `scaffold`; or hand-written
   `dsp.c` against `<synth>_dsp_*`).
8. Controls, MIDI, screen, storage.
9. Test (host, browser parity, target package, fm1-emu, evidence matrix).
10. Install (identity, backup, installer, verify) — hardware.
11. Validate on device (audio, MIDI, USB, stress, recovery) — hardware.
12. Troubleshoot and recover (route taxonomy) — maybe.
13. Record evidence and provenance.

### 6.7 Start guide

`README.md` — what umetate is, the seven components, the first three commands
(`quick-check`, `setup --dry-run`, `deep-check`), the repository map, and the status line.

### 6.8 Maintainability & readability contract

Enforced by three committed artifacts, owned in detail by `firmware/README.md`.
This section summarizes; do not duplicate the detail.

- **`firmware/README.md`** — the app contract, the enumerated platform/HAL API,
  numeric conventions, naming case rules, the **ten rules**, and the audio-callback
  "never" list.
- **`.clang-format`** — Allman braces, 4-space indent, 100 col, right-aligned
  pointers. Applied by `umetate fmt`.
- **`.clang-tidy`** — bug/UB/portability/readability/perf checks, warnings-as-errors.
- **`templates/scaffold/*.schema.json`** — `params`/`node`/`patch` schemas.

**The ten rules** (adapted from the NASA/JPL "Power of 10", Holzmann 2006): simple
control flow (no goto/setjmp/recursion); bounded loops (no `while(1)` in the
callback); no heap after init; small functions (≤ ~60 lines, `static`+`inline` under
`-O3`/LTO); assert invariants; smallest scope; check returns + parameters; limited
preprocessor (only `BOARD_SMK37` / `--dsp` / `--clock` seams); restricted pointers
(**no per-sample indirect dispatch** — block-rate `switch`/jump-table or
model-as-data, `firmware/README.md` §5.1); warnings-as-errors from day one.

**Data-layout rule:** per-voice parallel state is **SoA**; single-instance control
is a plain struct; `const` tables are XIP. The layout is stated next to the
declaration.

**Module boundaries (the RIB runtime, minimal TUs).**

```text
firmware/
  hal/       header-only; raw registers + board facts. One header per peripheral.
  src/
    rib.c        app: instrument logic, app_main()/app_audio()
    rib_dsp.c    pure DSP: platform-free; the ONLY TU allowed FP or hardware math
    platform.c   device services: USB, MIDI, panel, screen, store, recovery, boot guard
  loader/    update loader (separate image; shares hal/ + the flash driver)
  # SMK-37 board layer: hal/smk_input.h + src/smk_wheel.h (BOARD_SMK37-gated)
```

- `hal/` owns raw MMIO. `rib_dsp.c` is platform-free (the parity seam). `platform.c`
  owns device services. `rib.c` is the app against the platform API. *(lint:
  HAL-only MMIO; no float/double/64-bit-div/alloc in DSP.)*

**Fixed, tiny contracts (the invariant seams):**

```c
void app_audio(int32_t *out, uint32_t n);   /* device: 256 stereo frames @ 44.1 kHz */
void app_main(void);                        /* device: main loop; calls platform_poll() */
/* shared DSP (host/browser/firmware), prefix from the scaffold name — see §12.1:
   <synth>_dsp_init/render/note_on/note_off/all_off/set_param/get_param/param_count/
   quiet/set_bend_q16/lit */
```

The `<synth>_dsp_*` API is the **invariant seam** both authoring paths produce: the
generator emits it from a patch; a power user hand-writes it as an escape hatch.
`params.json` is the **generated, flattened** param table (what panel/MIDI sees),
validated by `params.schema.json`; the patch's per-node params are its source.

**Naming.** `fm1_` = board/HAL, `rib_` = reference app, `<synth>_` = user synth;
frozen identity strings (`_990`); one prefix per layer.

**Python conventions.** One module per command, thin `cli.py` dispatcher, `argparse`
subparsers, `dataclasses` for config, no side effects on import, the evidence
vocabulary as an `Enum`. I/O-bound: optimize only measured hot paths.

- **Strict typing** — `mypy --strict` over the owned Python (`umetate/` +
  `firmware/tools/gen_math_tables.py`), enforced in the build. Every public
  function/module is annotated; the fm1tk-lineage `firmware/tools/` + `tests/`
  are excluded (strangler-fig'd, not typed in place). Modern style: PEP 585
  (`list[int]`), PEP 604 (`int | None`), `from __future__ import annotations`,
  `TypeAlias` for callable/union aliases, `Protocol` for structural typing across
  module boundaries (avoids import cycles), `NamedTuple` for tiny value types.
- **Lint + format** — `ruff check` + `ruff format --check` (88 cols, py311), clean
  in the build. No hand-styled whitespace.
- **Packaging** — `setuptools` (PEP 621 `[project]` + `[build-system]` +
  `[project.scripts] umetate = "umetate.cli:main"`). Version authority is
  `pyproject.toml`, read via `importlib.metadata.version("umetate")` with a
  `PackageNotFoundError` fallback for a raw checkout (the firmware's `APP_VER` is a
  separate thing).
- **Clarity over cleverness** — names read as sentences, one-line docstrings state
  the *why* of every public function/module, and the generator is a *compiler*
  (§12.4): typed IR, ordered passes, deterministic output, `GenError(message)`
  diagnostics carrying the reason + location (never a bare assert or a silent
  fallback).

**Generated files.** `gen/`, generated `dsp.c` + param tables, `synth_params.h`,
`params.js`, skill `references/`, `web-synth` artifacts carry `// GENERATED — do not
edit`; the generator is authoritative.

### 6.9 Module library (the batteries)

Shipped, reviewed nodes in `modules/`, each = `node.json` + `<node>.c` + a host
test + a budget annotation:

| Node | Kind | Purpose |
| --- | --- | --- |
| `phasor` | phase accumulator | pitch→phase ramp; reset/sync/mod; the shared phase source |
| `osc` / `table` | wave reader | phase→audio via a table; optional `phase_map` (phase distortion) |
| `env` / `seg` | segment generator | gate event→control via breakpoint segments (data) |
| `vca` / `mul` | gain | audio×control (modulatable level) |
| `mix` / `add` | summer | N audio ins → 1 out |
| `svf` / `one_pole` | filter | state-variable / one-pole; modulatable cutoff/res |
| `delay1` / `delayN` | delay | 1-sample (feedback) / N-sample (echo); the DAG cycle-breakers |
| `noise` | source | white / pink |
| `ifft` / `add` | spectral | spectral bins → audio (additive) |

`umetate lib list` shows the library; `umetate scaffold --template` starts from a shipped template; user
nodes conform to `node.schema.json`, patches to `patch.schema.json`.

### 6.10 UI kit (the panel base)

The shipped, tested UI base every project builds on:

- **Context runtime:** the stack + global-fallthrough resolution + entry/exit
  hooks + boot screen + home.
- **Abstract widget set:** `label`, `value`, `bar`, `param_row`, `param_column`,
  `list`, `grid` (no skeuomorphic knobs/meters on a 240×240 screen).
- **Retained-mode redraw engine:** dirty-tracking (redraw only changed widgets),
  rate-bounded (~30 Hz), `LCD_IDLE`/`app_idle` integration so held notes stay
  playable during DMA, a visible safe-failure screen, and the hard rule of no
  display/flash/logging in the audio callback.
- **Panel generator:** `panel.json` → the app's UI wiring (bindings, pages,
  navigation); a custom `cv_*` canvas page is the escape hatch.

The panel schema is `templates/scaffold/panel.schema.json`; the interview fills
`templates/control-map.md`.

---

## 7. Implementation roadmap (ordered)

Each task lists its goal, actions, and acceptance/evidence (per §5.5). A task is
"done" only when its acceptance is met and the claim ledger in `docs/roadmap.md`
is updated in the same commit.

### Phase 0 — Governance & skeleton (P0) — **done** (2026-10-26)

**P0-1 — Repository skeleton and naming.** — **done** — Flat tree (§4.1); `umetate`
name, CMake project, `UMETATE_*` env prefix, `rib` identifiers, and the frozen
`_990` identities (D6) locked; `.gitignore`, `.gitattributes`, `.clang-format`,
`.clang-tidy`, and the four schemas (with the §12.7.5 fixes: `gate`/`note`/
`velocity` bindings, `voice_out`, macro state-targets, `q12`, Q32 port formats) in
place; the stale root `umetate-roadmap.md` removed. The frozen identities header
(`hal/fm1_cc.h`) is created in P2-1 with the firmware import. **Layer: source.**

**P0-2 — Canonical documents.** — **done** — `README.md`, `docs/roadmap.md`,
`docs/platform-facts.md`, `docs/tutorial.md` (§6.6 skeleton), `LICENSING.md`,
`LICENSE`, and `firmware/README.md` in place. **Layer: docs.**

**P0-3 — Dependency & licence manifest.** — **done** — `env.lock` pins the toolchain
versions + the SDK asset-hash placeholders (filled at P2-1); `LICENSING.md` records
per-dependency licences + the non-redistribution rule. **Layer: docs.**

**Exit P0:** **met** — a reader names the toolkit, the firmware component, and the
first command; identity and doc set are frozen.

### Phase 1 — Docker image + volume (P1) — **done**

**P1-1 — Pinned Linux dev container.** — **done** (2026-10-26; hardened 2026-10-27) —
`docker/Dockerfile` (Debian 13 trixie, Emscripten 6.0.13 pinned), `.dockerignore`,
`build.sh`, compose + `.env.example`. Node comes from emsdk's own node 24 (not apt's
EOL node 18); `apt-get upgrade` + `setuptools` are kept current. *Verified:* `docker
build` succeeds; `cc`, `cmake`, `ninja`, `python3` (3.13), `node` (24), `emcc`, Pillow
all resolve; the firmware host test runs green inside it. `docker scout cves` reports
1 critical / 16 high (down from 9 / 83) — the remainder is pinned emsdk npm
build-tooling + Debian packages awaiting upstream fixes (picked up by `apt-get
upgrade` on rebuild). **Layer: host.**

**P1-2 — Target volume + setup.** — **done** — `umetate setup` installs the JieLi Linux
pi32v2 toolchain (`jieli-linux-toolchains-20260730.1`, SHA-256 `a1545cdd…`, `clang
4.0.1`) and the AC79 SDK (`AC79NN_SDK_V1.2.1_2023-12-13`) into the `umetate-target`
volume at `/opt/jieli/toolchain` + `/opt/jieli/sdk`. The toolchain tarball SHA-256 and
the three SDK assets (`uboot.boot`, `cfg_tool.bin`, `cfg/eq_cfg_hw.bin`) are verified
against `env.lock`; `--force` accepts a mismatch; `--dry-run`/`--json` print the plan.
A git-ignored `.jieli/` checkout remains as a per-checkout fallback. **Layer: host.**

### Phase 2 — RIB runtime + generator (P2) — **done (host), blocked (target/device)**

**P2-1 — Import the Dinghy/Felucca baseline and flatten.** — **done (import + host +
target packages)** — Imported source-owned C (app `rib.c`/`rib_dsp.c`,
platform, HAL, loader, `crt0.S`, `app.ld`, SMK board layer) into `firmware/`;
CMake/Ninja with a **separate DSP TU**; platform/USB/loader at `-Os`. Renamed
`FM1TK`→`UMETATE` / `fm1tk`→`umetate` (15 files) and removed the Dinghy migration
shims (5 files); no `FM1TK`/`fm1tk`/`DINGHY_`/`dinghy-` identifiers remain. *Verified:*
host test builds and runs green in the container (`rib.wav` 286464 frames + screen
PNGs, zero warnings); the target packages build once the JieLi toolchain + SDK are
present (P1-2) — `umetate-fm1-pro.fwsc` and `umetate-smk37-pro.fwsc` produced with
the SDK assets hash-verified. Identities frozen as `FM-1_990`, `SMK-37 Pro_990`,
`SMK-37 Elite_990`, `MKE-P37_990` (D6 corrected to the code's authoritative value;
also fixed the two spots that carried the wrong `SMK-37 MKE-P37_99` prefix —
`tools/cmake_target.py:61` and `tests/run_tests.sh:57` — so the package identity now
matches the on-device `SMK_MODEL` value the installer recognizes).
**Layer: source/host/target.**

**P2-2 — Dual-core bring-up (default).** — **done (source/host), blocked (target/device)**
— Imported Felucca's proven core-1 layer verbatim (`hal/fm1_cpu1.h` + `hal/fm1_cpu1.S`,
lineage X0X/Melodee/Jangada via Felucca): the synchronous one-job mailbox (`fn(arg)`
+ a check word that is itself the `0x00200000` boot probe) and the built-in fallback
(bad check / 4 ms stall → hold core 1 → single core). Restored the dropped core-1
bits to `hal/fm1_sys.h` (`FM1_C1_CON`, `fm1_cpu1_halt`, `FM1_RESET_PREP`) and
`hal/fm1_guard.h` (`.c1_text` PC window, `fm1_guard_pc_open`); added `.c1_text` to
`app.ld`; `build.py` compiles `fm1_cpu1.S` + `-DFM1_CPU1_USED=1`. Wired the csync-only
note queue (`hal/fm1_ipc.h`), the `rib_render_block` job, and the dual-core↔fallback
branches in `app_audio`/`play`/`stop`/`quiet`. *Verified:* host build green; `dsp_test`
+ `ipc_test` (FIFO / wrap-around / overrun / no-lost-note-off) pass. *Blocked:* the
target package and the device probe need the JieLi toolchain + hardware. **Layer: source/host.**

**P2-3 — Hardware acceleration HAL.** — **done (source/host), blocked (target/device)**
— `hal/fm1_math.h`: saturating Q arithmetic (`fm1_q15_mul`/`q16_mul`/`q31_mul`,
`fm1_sat_add32`/`sat_sub32`, `fm1_madd_sat`, `fm1_shr_round`) + the transcendental
tables (`fm1_sin`/`fm1_cos` from a 256-entry quarter-sine, `fm1_exp2_q16`,
`fm1_log2_q16`) + the ROM transcendental passthrough (`fm1_cos_sin`/`fm1_exp`/
`fm1_log`/`fm1_atan2`/`fm1_sqrt` → `math_cos_sin`/`math_exp`/… on target) + an
opt-in FFT wrapper (`FM1_MATH_FFT` → kiss_fft). Generated `gen/math_tables.h`
(tools/gen_math_tables.py, checked in). Vendored the self-contained SDK math:
`vendor/kiss_fft/` (BSD-3, the SW FFT) and `vendor/jieli/` (`math.h` — the ROM
hardware transcendentals, `fftvec_math_drv.h` — the hw FFT/vector driver,
`flfft_core_pi32v2.c` — the float-FFT wrapper; Apache-2.0). `rib_dsp.c` routes its
hot-loop multiply/accumulate through `fm1_q15_mul`/`fm1_sat_add32`. *Verified:* host
build green; `math_test` (24 checks), `dsp_test`, `ipc_test` pass. *Read-from-SDK at
target link (not vendored):* the `jl_fft.c`/`nn_function_vec.c`/`jl_math.c` bodies
and the `libFFT_pi32v2_OnChip.a` — they include `cpu.h` → `WL82.h` (the whole CPU
register header) + the OS (`system/includes.h`, `os/os_api.h`), so only their
self-contained *declarations* are vendored; the implementations are read from the SDK
checkout like the binary assets. The hardware FFT (`hwfft_*`) and vector DSP
(`vector_*`) are wired in P2-8. *Blocked:* target link + emulator hw-vs-sw parity
need the JieLi toolchain + fm1-emu. **Layer: source/host.**

**P2-4 — FPU opt-in (`--dsp float`).** DSP-TU-only FPU; no `double`; prove context
ownership. *Acceptance:* no soft-float helpers in DSP; no FP outside the DSP object;
host integer-vs-float parity; device `blocked`. **Layer: source/host/target.**

**P2-5 — Clock profiles (240/320).** Report measured clock; implement the 240/320
selection with the `fm1-clk320-probe` ordering; power-cycle semantics. *Acceptance:*
`status`/screen reports measured clock + revision; 360/396 rejected at the CLI.
Device soak `blocked`. **Layer: source/target.**

**P2-6 — SMK-37 board layer.** Velocity keybed, 16 RGB pads, 4 faders, 8 encoders,
wheels, outer keys, per-model identities, SMK flash map + owner tag; FM-1
byte-identical (`BOARD_SMK37`). *Acceptance:* all three SMK models build; FM-1
byte-identical; flash-map test covers every object. **Layer: source/host/target.**

**P2-7 — Recovery & safety in firmware.** App-level rescue, boot guard, running
chord, custom loader (`ota-<identity>` + resume + model check), single-bank-OTA
`uboot.boot`, protected-range guards, `SEC-1`/`SEC-2` fixes. *Acceptance:* host
`bootguard` test; `lint --c` encodes SEC-1/SEC-2 + flash allow-list. Device `blocked`.
**Layer: source/host.**

**P2-8 — Patch generator (the AOT compiler).** — **done (host, strict-typed), blocked (WASM/target)**
— A compiler pipeline (the §12.4 spec): `_ir.py` (Port/Edge/PortSpec NamedTuples,
`NodeSpec`, `NodeInstance`, `CompiledGraph`, `GenError`), `_frontend.py` (parse →
macro expand → wire resolve → type-check → cycle-check + topo), `_backend.py` (rate
split → state alloc → allocator → emission), and `generate.py` (the thin pure entry).
The node library lives in `modules/<node>/node.json + node.c` (§12.5): a manifest +
a per-sample C template with `${in.*}`/`${out.*}`/`${state.*}`/`${param.*}`
placeholders (zone-agnostic auto-wrap) and `@@read@@`/`@@write@@` cycle breakers;
a leftover placeholder is a `GenError`. It type-checks wires (rejects `audio→event`
+ Q-format mismatches), cycle-checks with `delay1`/`delayN` removed as breakers, and
emits the **rate split** (control prologue every `CONTROL_BLOCK`=32, audio loop per
sample) + the §12.1 seam + the note→inc allocator (`ratio` via a note-derived state
binding). *Verified:* the pocket-drone two-op FM example (op macro + delay1 feedback
+ global chain) compiles; a delay-free env/vca patch renders non-silent then silent;
an `audio→event` edge is rejected; `mypy --strict` + `ruff check` + `ruff format
--check` are clean over the owned Python. *Deferred:* the flattened `params.json`
table + `const` XIP `tables:` + `model`-enum dispatch (P2-8 follow-up, with
`scaffold` in P3); WASM (emscripten) + target (JieLi clang) builds need
P1-2/P3-2. **Layer: host.**

**P2-9 — UI base + panel generator.** — **done (host), blocked (target/device)**
— Shipped `firmware/src/ui.c`/`ui.h` (the context-stack runtime: push/pop/pop_home,
global binding fallthrough, entry/exit hooks, the 7 widget renderers + the
`UI_CUSTOM` canvas escape hatch, the binding resolver + action dispatch, and the
retained-mode dirty/redraw engine — rate-bounded ~30 Hz, redraw touches only dirty
widgets, `LCD_IDLE`-integrated, a `ui_safe_fail` screen). The tables are `const`
(XIP); the only mutable state is the param array, the stack, the cursor, and one
last-drawn value per widget. `umetate/_panel.py` generates the tables from
`panel.json` (param/source/action/behavior names resolved to the fixed `ui.h` ids;
an unknown name is a GenError; deterministic). `rib.c`'s demo screen is rebuilt on
the kit (the keyboard stays app code, drawn directly). *Verified:* `python3 -m
umetate.test_panel` (determinism + compile + unknown-name rejection) and the
`ui_test` host target (home/edit/step, `KEY → note_on` overridden by `KEY →
set_step`, a relative param write) pass; `mypy --strict` + `ruff` clean; the host
build plays notes and shifts octaves through the bindings, and the screen redraws
differently between captures. *Deferred:* the `boot` screen (a transient pre-context
page) and the `on_enter`/`on_exit` hooks (emitted as `0` for now); the log curve.
**Layer: host.**

**Exit P2:** **met (host)** — RIB is the dual-core, integer-by-default runtime for
FM-1 + SMK-37; the generator compiles patches to the invariant `<synth>_dsp_*` seam
and panels to the shipped UI kit. Every device gate is explicitly `blocked`/`not-run`.

### Phase 3 — CLI (P3)

**P3-1 — CLI skeleton.** — **done** — `pyproject.toml` (`[build-system]` setuptools +
`[project.scripts] umetate = "umetate.cli:main"`), the `umetate/` package, `cli.py`
(dispatch, `--help`/`help CMD`, no import side effects), `evidence.py` (the §5.5
`Status`/`Layer` enums), `version.py`, `status.py` (the per-layer roadmap parser),
`quick_check.py` (the presence probe). The other commands are registered and report
their phase. *Verified:* `pip install -e .`; `umetate --help` lists all commands;
`umetate status` parses the roadmap; `python3 -m umetate.test_cli` + `mypy --strict`
+ `ruff` green. **Layer: host.**

**P3-2 — Env + build orchestration.** — **done (host + target)** — `runner.py`
(the persistent-container docker shim: `ensure_container`/`run`/`run_writable`/
`probe`, native `docker.exe` on Windows), `setup.py` (auto/manual toolchain+SDK fetch,
SHA-256 verify vs `env.lock`, smoke-test, `--dry-run`/`--clock`/`--force`), `build.py`
(the target branch → `.fwsc`, wraps `cmake_target.py`, resolves the toolchain/SDK as
`$JIELI_TOOLCHAIN`/`$AC79_SDK` → the `umetate-target` volume → the `.jieli/` checkout,
rejects `--clock 360|396`), `deep_check.py` (`--host` runs the host tests),
`inspect.py` (the `.fwsc` reader). *Verified:* `mypy --strict` + `ruff` + `test_cli`
green; `setup --dry-run` prints the plan; `umetate setup --yes` downloads the
toolchain (SHA-256 `a1545cdd…`), clones the SDK (`AC79NN_SDK_V1.2.1_2023-12-13`), and
installs both into the `umetate-target` volume with all three SDK assets hash-verified;
`umetate build` then builds from `/opt/jieli/toolchain` + `/opt/jieli/sdk` and produces
`umetate-fm1-pro.fwsc` (FM-1_990) and `umetate-smk37-pro.fwsc` (SMK-37 Pro_990);
`umetate quick-check` reports the TARGET layer as the volume. **Layer: host/target.**

**P3-3 — `scaffold`/`lib`, `lint`, `fmt` + the param table.** — **done (host)** —
`scaffold.py` (generate a node/macro/patch skeleton; `--template` copies a shipped
example, e.g. `pocket-drone`; a generated patch is verified to build), `lib.py`
(`lib list` — the 9 nodes + 2 templates, local only), `lint.py` (`lint --c` — the
grep-based standing checks: SEC-1 MAXP bounds, HAL-only MMIO, hardcoded flash
addresses, no double/alloc in the DSP TU), `fmt.py` (clang-format), and the
**flattened param namespace**: the generator now emits the §12.1
`set_param`/`get_param`/`param_count` seam + `params.json` (a named node param → its
`set_param` id). *Verified:* `scaffold patch` (minimal and `--template pocket-drone`)
builds; `lib list` lists the nodes + templates; `lint --c` passes on the firmware and
flags a crafted MAXP/MMIO violation; `params.json` maps `lp.cutoff` → id 4; `mypy
--strict` + `ruff` + `test_cli`/`test_generate`/`test_panel` green. The **name →
node-param binding** (the patch `params:` section, `params.schema.json`) and the
**`const` XIP `tables.c`** landed as a follow-up: `params:` binds a friendly name +
display metadata (min/max/curve/unit/rate/modulatable) to a flattened
`<instance>.<param>`; the generator emits the `dsp_param` metadata table + the full
`params.json`; `generate_panel` shares that set_param id space; `generate_tables`
emits `tables.c`/`.h` (built-in shapes + inline spec, referenceable by
`${table.<name>}`). **Layer: host.**

**P3-4 — `flash`, `debrick` (direct, gated).** Per §6.1 and §8. `flash` wraps the
inherited `fm1_install.py` (strangler-fig, not a rewrite — the clean `umetate/flash.py`
stays after device verification): parses identity/CRC/model, switches to update mode,
and resumes a device already in update mode; `debrick` names the recovery routes and
their prerequisites. `mask-rom` debrick is **blocked** (needs the USB_KEY dongle +
`jl-uboot-tool`; the dongle is at hand but pending a USB solder, and the FM-1 is
unreachable for ~10 days). *Acceptance:* no write without `--device` + confirmation;
wrong-model exits 6; resume checks the model; a fake device (the inherited
`install_test.py`'s `backend` seam) exercises flash/resume without hardware.
**Layer: host.**

**P3-5 — `web-build`/`web-serve` + `evidence`.** — **done (host/browser)** —
`web.py` (`web-build` emscripten-compiles the generated `dsp.c` to a standalone
`dsp.wasm` — no import section — + a minimal `index.html`/`app.js` harness (a manual
browser poke); `web-serve` is a loopback static server), `evidence.py` (validate an
evidence matrix: per-layer status, `blocked`/`not-run` never `pass`, `--strict`
requires every layer), and the `deep-check --web` wasm check (standalone, no imports).
*Verified:* `web-build` produces `dsp.wasm` (no import section) that renders in a
browser (peak 32765 on note-on, silent after off); `web-serve` serves the harness;
`deep-check --web` passes; `quick-check` reports the `browser` layer; `mypy --strict`
+ `ruff` + `test_cli` green. The real parity lab (AudioWorklet + the automated
host↔browser check) is **P4-1**. **Layer: host/browser.**

### Phase 4 — Web lab + emulator (P4) — **in progress**

**P4-1 — WASM parity lab.** Compile the generated DSP (the same sources as
firmware/host) to standalone WASM; AudioWorklet adapter; versioned message protocol;
explicit rate/block conversion; gesture-gated start. *Acceptance:* `deep-check --web`
passes; browser matches host within tolerance. **Layer: browser.**

**P4-2 — fm1-emu as model layer.** — **done (emulator)** — `umetate setup` (no flags)
now installs Rust (rustup) and builds fm1-emu at the pinned commit — the `fm1-emu`
batch interpreter *and* the `fm1-live` GUI. `umetate emu` runs the GUI (`--fwsc`,
`--persist`, `--midi`, `--mhz`) or `--check` (headless `fm1-live --shot` → panel +
audio peak). *Verified:* `umetate emu --check` boots `umetate-fm1-pro.fwsc` (audio peak
10378, chord LEDs lit, no halt) and `umetate-smk37-pro.fwsc` (SMK-37 pads rendered,
audio peak 6720, no halt); `quick-check` reports the `emulator` layer as `pass`. RIB
runs unchanged in the emulator. No device-acceptance claim. **Layer: emulator.**

### Phase 5 — Skills (P5)

**P5-1 — umetate-development skill.** `SKILL.md` + offline `references/` (AC79
facts, flash maps, port-kit patterns, the node/macro/patch schemas, recovery
taxonomy, evidence vocabulary, code conventions) + `assets/` (copies of `templates/`).
*Acceptance:* `deep-check --skill` passes; it drives `scaffold`/patch authoring and
refuses device writes without §8 gates. **Layer: docs.**

**P5-2 — umetate-safety skill.** `SKILL.md` + offline `references/` (threat model,
audit checklist, device gates, recovery taxonomy). *Acceptance:* `deep-check --skill`
passes; maps every surface to code/test/gate; preserves "not security-clean while
SEC-1 device validation is blocked." **Layer: docs.**

### Phase 6 — Tutorial + start guide final (P6)

**P6-1 — Tutorial.** Fill §6.6 with real commands, per-source flags, the
dual-core/FPU/clock facts, the framework authoring flow, the recovery taxonomy, and
evidence levels. *Acceptance:* a reader follows the no-hardware path to a target
package; device steps `blocked`; `deep-check --links` passes. **Layer: docs.**

**P6-2 — Start guide.** Finalize `README.md`. *Acceptance:* a new reader names the
toolkit, the firmware component, and the first command. **Layer: docs.**

### Phase 7 — Release & provenance (P7, optional)

**P7-1 — Baseline tag + provenance.** Tag `umetate-baseline-YYYY-MM-DD`; record
commit, tag, package hashes, identities, toolchain/SDK hashes, per-claim status.
*Acceptance:* clean clone → `deep-check --all` → four target builds; no "security-clean"/
"device-accepted" wording while blocked. **Layer: release.**

**P7-2 — Publish only on request.** Nothing pushed/published by default. **Layer: release.**

---

## 8. Device-safety gates (non-negotiable)

Every `flash`/`debrick` write requires, before the command:

1. explicit operator request for that exact action;
2. exact board/revision + current firmware identity recorded;
3. package identity + CRC integrity verified (`umetate inspect`);
4. rollback image named (verified stock `.fwsc`);
5. recovery route named, with its prerequisite (§5.4);
6. `--device` + interactive confirmation (or `--yes`).

A build, test, or code edit is never permission to write hardware. Hard-brick
risk is real (single 1 MiB flash bank, no recovery button/test pads/debug header,
co-packaged flash die). The agent does not execute device-writing commands as a
side effect of any other task.

---

## 9. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Dual-core flakiness (core-1 `0x00200000` misread) | Boot-time probe + runtime fallback to CPU0; per-unit report. |
| Cache/barrier bugs in IPC | SPSC rings + acquire/release barriers; host stress tests; overrun counters. |
| Flash write during CPU1 render | Park/drain/ack protocol; abort on no-ack; CPU1 code in RAM/SDRAM. |
| FPU context corruption | Only DSP TU uses FP; proof or ISR save/restore; no `double`; host parity. |
| Clock change instability | 240/320 only; probe ordering; report measured value; power-cycle; soak. |
| `-O2`/LTO USB-MIDI regression | DSP is a separate TU; platform/USB/loader pinned `-Os`; regression check. |
| Generator emits dispatch or allocation in the hot loop | `lint`/disasm gate (no per-sample dispatch); budget + evidence gates. |
| Generator type system too weak (bad edge slips through) | Port-kind checking; `delay1`/`delayN` as the only cycle-breakers; schema validation. |
| Wrong-model update | `same_keyboard` + model check on install and resume; exit 6; 20/36/21-block tests. |
| Unsigned update | CRC-16 is integrity not authenticity; documented; no "secure update" claim. |
| Full-flash backup unavailable | Stock `.fwsc` + named recovery route; no backup promise. |
| Identity change breaks recognition | `_990` identities frozen; artifact names free. |
| Vendor toolchain licensing | Toolchain in Docker volume, user-obtained; hashes only; no redistribution. |
| Plan/implementation drift | Each commit updates the task state + claim ledger in `docs/roadmap.md`. |

---

## 10. Open questions (non-blocking)

1. Exact MCU part/revision (`AC791N` vs the `AC7911B` label) — resolve from the SDK
   datasheet at P2-1.
2. Whether the FM-1 enables the FPU by default (F3 claim) — resolved by the P2-4
   target probe; `blocked` until then.

---

## 11. Definition of done

- [ ] Five canonical docs + `firmware/README.md` + the three schemas exist;
      `docs/roadmap.md` is the only status authority.
- [ ] `umetate` is the only entry point; every command has `--help`/`help`.
- [ ] `umetate quick-check`/`setup` are opt-in, non-silent, dry-runnable, hash-pinned.
- [ ] `umetate build` produces `umetate-<board>-<model>[-<release>].fwsc` for FM-1
      and SMK-37 Pro/Elite/MKE, dual-core by default, identities `_990` frozen.
- [ ] `--dsp float` (single-precision, opt-in) and `--clock 240|320` work; `double`
      and 360/396 MHz are rejected or absent.
- [ ] Hardware acceleration is exposed through `hal/fm1_math.h` with a parity fallback.
- [ ] The framework is real: `scaffold node|macro|patch --template` + `lib list` author a
      synth (defaults or custom DSP, by hand or agentically); the generator emits
      the invariant `<synth>_dsp_*` seam with no per-sample dispatch; a hand-written
      `dsp.c` against the same API works as an escape hatch.
- [ ] The UI base is real: a context stack (home/boot/hooks/global fallthrough),
      the abstract widget set, the retained-mode dirty/redraw engine, and the panel
      generator — tested by scripted host UI tests, with no display/flash in the
      audio callback.
- [ ] The WASM parity lab and fm1-emu model layer are first-class targets.
- [ ] Two offline skills (development, safety) pass `deep-check --skill`.
- [ ] The tutorial teaches design, authoring, testing, installation, recovery, and
      evidence, with explicit hard-brick risk; device steps `blocked` until hardware.
- [ ] Device writes are gated (§8); no write as a build/test side effect.
- [ ] `deep-check --all` passes on a clean clone; four target builds pass through the
      Docker route; the baseline is not described as security-clean or
      device-accepted while blocked.

---

## 12. Detailed design (the blueprint)

The implementation blueprint: files, structs, functions, data flow, and memory,
per subsystem, so a fresh implementer makes zero design decisions. Written
subsystem by subsystem; read with §7 (the order). Sections: 12.1 the invariant
seam; 12.2 the memory & emission contract; 12.3 the RIB runtime; 12.4 the
generator; 12.5 the node library; 12.6 the UI kit; 12.7 CLI/build/tests; 12.8 the
CLI codebase.

### 12.1 The invariant seam — the `<synth>_dsp_*` contract

**Role.** The single interface every synth engine implements — generated from a
patch or hand-written — that the runtime calls. It is where the framework (the
generator) meets the hardware layer (`app_audio`).

**Interface (frozen).**

```c
void     <synth>_dsp_init(uint32_t rate);                      /* once at boot */
void     <synth>_dsp_render(int32_t *out, uint32_t frames);    /* fill out = L R L R…, Q15 ±32767 */
void     <synth>_dsp_note_on(uint32_t note, uint32_t velocity);/* note = MIDI number, vel 1..127 */
void     <synth>_dsp_note_off(uint32_t note);
void     <synth>_dsp_all_notes_off(void);
int      <synth>_dsp_set_param(uint32_t id, int32_t value);    /* clamp; 0 ok, -1 bad id */
int32_t  <synth>_dsp_get_param(uint32_t id);
uint32_t <synth>_dsp_param_count(void);
int      <synth>_dsp_quiet(void);                              /* all voices silent */
void     <synth>_dsp_set_bend_q16(uint32_t bend);              /* pitch bend, Q16 cents */
uint32_t <synth>_dsp_lit(uint32_t base_note);                  /* bitmask of sounding note keys */
```

**Param table (generated, `const`, XIP).**

```c
typedef struct { uint32_t id; const char *name; int32_t min, max, def;
                 uint8_t curve;   /* 0 linear, 1 log */
                 uint8_t rate;    /* 0 sample, 1 block */
                 const char *unit; } dsp_param;
extern const dsp_param <synth>_dsp_params[];   /* [param_count()] */
```

**State ownership.** The engine owns its voice state as `static` SoA arrays
(`phase[NVOICE]`, `env[NVOICE]`, …), zero-alloc. `render` is a pure function of
(state, params, pending events) → `out`: no I/O, no allocation, no blocking, no
per-sample dispatch. `note_on`/`note_off`/`set_param` mutate state (or the
pending-event queue).

**Dual-core transport (runtime-owned).**

```c
typedef struct { uint8_t kind;      /* NOTE_ON | NOTE_OFF | ALL_OFF  (events only) */
                 uint8_t pad; uint16_t note; uint16_t vel; } dsp_cmd;   /* note-queue entry */

/* params & bend are shared VALUES, not queue commands — CPU0 writes, both read */
extern volatile int32_t param_values[NUM_PARAMS];   /* in aligned .bss (shared) */
extern volatile int32_t bend_q16;                    /* in aligned .bss (shared) */

typedef struct { volatile uint32_t quiet;   /* 1 = all voices silent   (CPU1 → CPU0) */
                 volatile uint32_t lit;     /* sounding note keys, 27-bit (FM-1; unused on SMK) */
               } dsp_status;                /* in aligned .bss (shared) */
```

- **one-job mailbox** (CPU0→CPU1): Felucca `fm1_cpu1.h` — core 0 hands `fn(arg)` +
  a check word and waits (`fm1_cpu1_run`/`fm1_cpu1_wait`); core 1 verifies the check
  before running. The check word **is** the boot probe; a bad check or a 4 ms stall
  holds core 1 (single-core from then on).
- **note queue** (CPU0→CPU1): SPSC, 64 entries, 32-bit indices, csync
  acquire/release, overrun counter. `note_on`/`note_off`/`all_notes_off` (main loop)
  enqueue events; the render job drains the queue at block start.
- **params & bend** (shared values): `set_param`/`set_bend_q16` (main loop) write
  `param_values[]`/`bend_q16` directly (single writer = CPU0); CPU1 reads them at
  block start, CPU0 reads them for display. No queue command, no reverse channel.
- **reverse status:** CPU1 writes `quiet`/`lit` each block; CPU0's `quiet()`/`lit()`
  read them (single-word, atomic).
- **fallback** (probe fail / host / single-core): `app_audio` runs `rib_render_block`
  locally; the mailbox and queue are unused; the engine is unaware of the mode.

The shared state (mailbox, note queue, params, status) lives in **plain aligned
`.bss`** — no `.shared` section, no uncached alias (none is sourced). The two cores
share the caches (Felucca `fm1_cpu1.h`), so ordering is `csync` only; `flushinv` is
for the flash/XIP cache (`hal/fm1_flash.h`), never for the inter-core transport.

**Memory placement.**

| What | Where |
| --- | --- |
| `render` + callees | `.dsp_text` (SRAM) — `UMETATE_TARGET_DSP` |
| engine voice state | `.cpu1_bss` (internal RAM) / `.bss` (host, single-core) |
| param table | `const` → XIP |
| mailbox + note queue + params + status | aligned `.bss` (shared, csync) |

**P2-8 (future): asynchronous ping-pong.** To drop the ISR wait, core 1 renders
ahead into `int32_t dsp_blocks[2][512]` with a per-buffer `ready[2]`/`done[2]`
handshake (CPU1 sets `ready[p]`, toggles `p`; CPU0's `app_audio` copies `buf[p]`,
sets `done[p]`, clears `ready[p]`); the render job becomes a continuous core-1
worker instead of a one-shot job. Not built — the synchronous mailbox above ships.

**Verification (must pass).** host parity (silence → note → silence; param clamp;
bad-id rejection; `quiet()` toggles); ring host tests (wrap-around, overrun, no
lost note-off); `render(256)` ≤ 2.9 ms on device; dual-core handshake + boot probe
+ fallback soak (§P2-2).

### 12.2 The memory & emission contract

**Purpose.** The last shared contract between the generator and the runtime: the
exact C types, the linker sections, and the portability macro — so *one* generated
`dsp.c` compiles for host (gcc/clang), WASM (emscripten), and target (JieLi pi32v2
clang), and lands in the right memory. Pinning this fully decouples the two sides:
the generator is tested against a host harness, the runtime against a stub engine.

#### 12.2.1 Fixed-point type map

The generator emits exactly these types (from the `node.schema.json` state/param
manifest kinds). A `q` name carries its scale, so no scale is ever implicit.

| manifest kind | C type | scale |
| --- | --- | --- |
| `q12` | `int16_t` | ×4096 (gains/coefficients) |
| `q15` | `int16_t` | ×32768 (levels/signals) |
| `q16` | `int32_t` | ×65536 (gains, filters) |
| `q32` | `int32_t` | ×2³² (wide intermediates) |
| `phase` | `uint32_t` | wrapping accumulator: `inc = f·2^32/FS` |
| `int8`/`int16`/`int32`/`uint32` | same | raw |

`const int16_t` wavetables and `const dsp_param` tables live in XIP.

#### 12.2.2 The portability macro

One header (`hal/fm1_cc.h`, extended) defines three placement macros that are
no-ops on host/WASM and emit the target section attribute on the device build.
The build defines `UMETATE_TARGET` (device) and `UMETATE_TARGET_DSP` (perf
profile, SRAM placement).

```c
#if defined(UMETATE_TARGET)
#define UMETATE_CPU1 __attribute__((section(".cpu1_bss")))   /* CPU1 engine state */
#define UMETATE_POOL __attribute__((section(".pool")))       /* big buffers (delay lines) */
#else
#define UMETATE_CPU1
#define UMETATE_POOL
#endif
#if defined(UMETATE_TARGET_DSP)
#define UMETATE_DSP __attribute__((section(".dsp_text"), noinline, used))  /* hot code → SRAM */
#else
#define UMETATE_DSP
#endif
```

The *contract* is the three section names (`.cpu1_bss`, `.pool`, `.dsp_text`) and
which macro carries each; the exact preprocessor spelling is pinned at P2-1. The
generator writes portable C11 and only ever places things through these three
macros — never a raw `__attribute__((section(...)))`.

#### 12.2.3 Linker sections & memory regions

`app.ld` defines the sections below; the generator emits into them via the macros;
the build's linker report verifies every budget (the fm1tk image/RAM/pool checks).

| Section | Contents | Owner | Memory |
| --- | --- | --- | --- |
| `.text` / `.rodata` | platform + app code, `const` tables (params, wavetables) | runtime + generator | XIP flash (`0x02000000+`) |
| `.dsp_text` | hot DSP code (`render` + callees) | generator | internal RAM, copied at boot |
| `.data` / `.bss` | CPU0 platform/app state (`fm1_in`, UI, MIDI) **+ the shared mailbox, note queue, params, status** | runtime | internal RAM |
| `.cpu1_bss` | CPU1 engine state (SoA voice + global) | generator | internal RAM |
| `.pool` | big buffers (delay lines), zeroed at boot | generator | internal RAM |

Hot per-sample tables (wavetables read every sample) may need a `.cpu1_rodata` RAM
section copied at boot instead of XIP — XIP reads route through the SFC and depend
on D-cache and the flash-park protocol. Default is XIP; measure at P2-3.

**Memory regions (budgets — verified by the linker report, never silently
exceeded):**

| Region | Budget | Notes |
| --- | --- | --- |
| XIP code + const | ≤ 568 KB | flash `0x02000000+`; `const` costs no RAM |
| CPU0 `.data`/`.bss` | ≤ 96 KB | platform/app **+ the shared mailbox/queue/params/status + core-1 stack** |
| CPU1 `.cpu1_bss` | ≤ 16 KB | engine voice/global state (SoA) |
| `.dsp_text` | ≤ 32 KB | hot DSP code in SRAM |
| `.pool` | ≤ 336 KB | big buffers |
| stack | 24 KB CPU0 + 8 KB CPU1 | separate stacks |

Total internal RAM must fit the usable ~511 KB (0x1c00000+). The indicative sizes
above sum to ~512 KB — at the limit, so the **linker report is the authority and
the build fails on overage, never silently.** Reconcile at P2-8 (when the generator
first emits `.cpu1_bss`/`.dsp_text`), before the first target package — e.g. trim
`.pool` (delay lines are the discretionary budget) or `.dsp_text`. The shared state
(mailbox, note queue, status) lives in plain aligned `.bss` — **no `.shared` section
or uncached alias is used** (none is sourced on this chip). The two cores **share the
caches** (Felucca `fm1_cpu1.h`), so ordering is enforced with `csync` barriers only;
`flushinv` is reserved for the flash/XIP cache (`hal/fm1_flash.h`), never for the
inter-core transport.

#### 12.2.4 Emission rules (what the generator may emit)

- **SoA for voice state:** each voice-zone node's `state` fields become
  `static <type> <instance>_<field>[NVOICE] UMETATE_CPU1`; global-zone fields are
  single `static <type> <instance>_<field> UMETATE_CPU1`. Names are
  `<instance>_<field>` to stay unique.
- **`const` everything the engine doesn't mutate** (tables → XIP).
- **Forbidden in the generated DSP** (enforced by `umetate lint --c`): `malloc`/
  `free`, `float`/`double` (integer default), 64-bit division/modulo, function
  pointers in the render path, unbounded loops, and any raw register access (HAL
  owns registers).

### 12.3 The RIB runtime

**Basis.** A fork of the Dinghy/Felucca hardware layer — imported, not rewritten.
The working layer (input matrix, flash driver, USB/MIDI, recovery, boot guard,
update loader, SMK board layer) is kept; what changes is the DSP architecture
above it (dual-core, §12.1) and the additions below.

**Import list (unchanged unless noted).**

```text
firmware/
  crt0.S  app.ld  CMakeLists.txt  build.sh
  hal/     fm1_input.h fm1_flash_map.h fm1_gpio.h fm1_cc.h fm1_audio.h fm1_adc.h
           fm1_timer.h fm1_time.h fm1_sys.h fm1_lcd_hw.h fm1_isr.S fm1_irq.h
           fm1_usb.h fm1_uart.h fm1_vec.S fm1_xip.h fm1_guard.h fm1_flash.h
           + fm1_cpu1.h (NEW, P2-2)   + fm1_math.h (NEW, P2-3)
  src/     rib.c rib_dsp.c rib_dsp.h platform.c bootguard.h gfx.c lcd.c libc.c
           midi_uart.c ota.c recovery.c smk_wheel.h store.h uac_fir.h uac_tap.h usb.c
  gen/     felucca_font.h  math_tables.h (NEW, P2-3; generated by tools/gen_math_tables.py)
  vendor/  kiss_fft/ (BSD-3, the SW FFT)  jieli/ (Apache-2.0: fftvec_math_drv.h + flfft_core_pi32v2.c)   (NEW, P2-3)
  loader/  (update loader — separate image)
  # SMK-37 board layer: hal/smk_input.h + src/smk_wheel.h (BOARD_SMK37-gated)
```

**Translation units — exactly two, plus the loader.** The existing code is already
`rib.c` (includes `platform.c`) + `rib_dsp.c`; umetate keeps it and renames the
section macro `FM1TK_DSP_API` → `UMETATE_DSP`.

- **TU A** `rib.c` → `#include "platform.c"` (the app + all device services:
  `usb.c`, `midi_uart.c`, `ota.c`, `recovery.c`, `gfx.c`, `lcd.c`, `libc.c`,
  `store.h`, `bootguard.h`, `uac_tap.h`, `uac_fir.h`, `smk_wheel.h`) — one unity
  TU at `-Os`.
- **TU B** `rib_dsp.c` — the DSP; `-Os` baseline, `-O3` + `.dsp_text` in `perf`,
  FPU opt-in. The only hot TU. `rib_dsp.c` is the *reference* engine; a user project
  replaces TU B with the generated `<synth>_dsp.c` — same seam, different prefix
  (§12.7).
- **`loader/`** — a third, separate image (its own entry + flash window).

**Dual-core bring-up (the divergence from Dinghy).**

- **Core-1 start (the only model this firmware uses).** RIB is bare-metal (it links
  no `system.a`), so the AC79 §7.40 SDK-OS model (`CPU_CORE_NUM 1` + `system.a` +
  `irq_info_table`) does **not** apply; it is recorded as a vendor fact only. The
  implemented sequence is Felucca `fm1_cpu1.h` (platform-facts §3): interrupt bank
  off (`0x1EEF300..`), entry address into `0x01C7FFF8`, bit 3 of `0x10008` held
  while starting, `C1_CON` (`0x1EEE004`) bit 3 set / bit 1 cleared; hold = bit 1
  set then bit 3 cleared. **No register writes beyond this recorded sequence.**
  Core 1 runs the bare-metal `fm1_c1_main`, never OS APIs (incl. `printf`).
- **Transport is the synchronous one-job mailbox** (imported `fm1_cpu1.h`, the
  proven Felucca/X0X/Melodee/Jangada layer): core 0 hands `fn(arg)` + a check word
  (`fn ^ arg ^ job*0x9E3779B1`) and waits for `done`; core 1 verifies the check
  before running. The check word **is** the boot probe — it detects the
  `0x00200000` misread; a bad check or a 4 ms stall holds core 1 and core 0 does
  the work (single-core fallback).
- **Notes travel on a csync-guarded SPSC queue** (`hal/fm1_ipc.h`, plain aligned
  `.bss` — the cores share the caches, so ordering is the only concern); params/bend
  are shared single-writer values; core 1 publishes `quiet`/`lit` status each block.
- **flash-park** is `fm1_cpu1_halt()` (bus traps off, `C1_CON` bit 1 set then bit 3
  cleared), called first thing in `fm1_cstart` and in every reset path
  (`FM1_RESET_PREP`); core 1's waiting loop sits in RAM (`.c1_text`).
- **audio wiring:** dual-core → `app_audio` hands `rib_render_block(out)` as the job
  and waits; on fallback it runs the same block locally. The engine is unaware of
  the mode.
- **Deferred to P2-8:** the §12.1 ping-pong `dsp_blocks[2][512]` + `ready`/`done`
  handshake (asynchronous, no ISR wait).

**Key structs (grounded in the imported code).** `fm1_in` (input matrix,
`hal/fm1_input.h`: notes/buttons/edges/encoders/LED layers, debounced, 10 kHz
tick); `dsp_cmd`/`dsp_status` (§12.1); `store` (`store.h`: settings/blobs/slots,
magic + CRC); the flash map (`fm1_flash_map.h` allow-list + `_Static_assert`s).

**Boot/init sequence.** `crt0.S → platform_init (clock, SFC, RAM) →
fm1_input_init → (dual-core: release CPU1 + probe) → app_init (engine_init) →
app_main` loop.

**Memory reconciliation (closes the §12.2 budget).** Reconcile at P2-8, when the
generator first emits `.cpu1_bss`/`.dsp_text` — e.g. trim `.pool` (delay lines are
the discretionary budget) or `.dsp_text`. The linker report is the authority; the
build fails on overage, never silently.

**Kept imported unchanged (the "working hardware layer").** input matrix + encoder
decoder + LED layers, the RAM flash driver + allow-list, USB (UAC + MIDI) + SysEx,
MIDI UART + TRS, the OTA parser + update loader, recovery + boot guard, the SMK-37
board layer, `app.ld`/`crt0.S`.

**The fm1tk tooling is strangler-fig'd (not kept).** `firmware/tools/` (the
fm1tk-lineage `build.py`, `cmake_target.py`, `fm1pkg_make.py`, `lz4blk.py`,
`fm1_install.py`) and `firmware/tests/` are inherited build/package/install tooling.
The CLI wraps each and replaces it incrementally from zero behind `umetate/`
(P3, §12.7) — `build.py`/`fm1pkg_make.py`/`lz4blk.py` first, the **installer last**, and only
after the clean replacement is device-verified (§8 gates). The inherited versions
stay until each replacement is proven; typing effort goes into the replacements,
not the throwaway lineage. The one exception is `firmware/tools/gen_math_tables.py`,
which is **umetate-owned** (written in P2-3) and fully strict-typed.

### 12.4 The generator (patch → engine)

**Purpose.** Compile `patch.json` + node manifests + `tables:` into
`<synth>_dsp.c` implementing the §12.1 seam. AOT: everything resolves at build time
to one fused, monomorphic `render`. (The panel→UI generator is §12.6.)

**Location & nature.** `umetate/generate.py` (Python) — a **pure function**: schemas
+ patch in → `<synth>_dsp.c` + `<synth>_dsp_params` out. No device, no toolchain.
Deterministic: same inputs → byte-identical output, marked `// GENERATED — do not edit`.

**Module structure (the compiler pipeline).** `generate.py` is the thin public
entry; the passes live in underscore-internal modules (roadmap §12.8), each a pure,
separately-testable stage:

```text
umetate/
  generate.py     # the public entry: generate(patch, nodes) -> str
  _ir.py          # Port/Edge/PortSpec NamedTuples, NodeSpec, NodeInstance,
                  #   CompiledGraph, GenError, load_library (the typed IR)
  _frontend.py    # parse -> macro expand -> binding resolve -> type-check ->
                  #   cycle-check -> topo -> CompiledGraph
  _backend.py     # rate split -> state allocation -> allocator -> C emission
  test_generate.py
modules/<node>/   # node.json (manifest) + node.c (per-sample body template)
```

**Inputs.** node manifests (`node.schema.json`, from `modules/` + user nodes); the
patch (`patch.schema.json`); the `tables:` data (wavetables/segments/spectra/
phase_maps).

**Outputs.** `<synth>_dsp.c` (the engine: fused `render` + the 11 seam functions +
SoA state); the `dsp_param` table (flattened from node params); `tables.c`/`.h`
(the `const` XIP arrays); `params.json` (the flattened param list the panel consumes).

**IR — a typed graph:**

```python
# _ir.py
class Port(NamedTuple):  node: str; port: str
class Edge(NamedTuple):  src: Port; dst: Port          # src -> dst

class PortSpec(NamedTuple):
    kind: str            # EVENT | CONTROL | AUDIO
    fmt: str | None      # q15 | q16 | q32 | phase (None = unannotated)

@dataclass
class NodeSpec:                                        # the compiled node.json (§12.5)
    name: str
    ins: dict[str, PortSpec]; outs: dict[str, PortSpec]
    params: dict[str, str]; state: dict[str, str]      # name -> q-format / pool
    body: str                                          # the node.c per-sample template

@dataclass
class NodeInstance:
    id: str; type: str; zone: str                      # zone: "voice" | "global"
    spec: NodeSpec; params: dict[str, str]
    in_expr: dict[str, str]                            # input port -> C expr (resolved)
    note_derived: dict[str, str] | None = None         # state -> macro ratio (note-on)

@dataclass
class CompiledGraph:                                   # frontend -> backend
    name: str; voices: int
    instances: list[NodeInstance]
    voice_order: list[str]; global_order: list[str]    # topo order per zone
    voice_out: Port | None                             # voice signal summed into bus
    global_out: Port | None                            # global node feeding `out`
    control_block: int = CONTROL_BLOCK_DEFAULT
```

**Passes (in order):**

1. **Parse & expand.** Load the patch; expand each macro instance into its nodes
   (prefixing ids `op1.ph`, `op1.osc`, …), mapping the macro's ports/params to its
   inner nodes. A macro's `freq → ph.inc` is a note-derived **state** binding,
   `fm → ph.fm` an edge, `vca.audio → audio` an output rename. Validate every wire
   (real ports, matching kind). *Reject `audio→event` and other kind/Q-format
   mismatches with a type error.*

2. **Cycle check.** Treat `delay1`/`delayN` as cycle-breakers — each contributes a
   *source* (register read, ordered first) and a *sink* (register write, ordered
   last) instead of an in→out edge. Topologically sort; a remaining cycle is an
   error. (FM feedback = an explicit `delay1` edge, so it compiles.)

3. **Template validation.** Every `${in.*}`/`${out.*}`/`${state.*}`/`${param.*}`
   placeholder in a `node.c` is checked against that node's `node.json`; an unknown
   placeholder (e.g. a typo `${in.phsae}`) is a `GenError`, never a silently-wrong
   `.c`.

4. **Rate split.** A node is **audio-rate** if any port is `audio`, else
   **control-rate**. Control-rate nodes run once per **sub-block** (every
   `CONTROL_BLOCK` frames, the prologue); audio-rate nodes run per sample (the loop).
   `<param>_mod` inputs are control-rate. `CONTROL_BLOCK` is a compile-time generator
   choice defaulting to **32** (~1.4 kHz control rate — zipper-free at ~5% of the
   audio cost; see `docs/dsp-study.md` §7); `16` is an option for fast sweeps, never
   larger than 64.

5. **State allocation.** Emit `static <type> <instance>_<field>[NVOICE] UMETATE_CPU1`
   (voice SoA) or `static <type> <instance>_<field> UMETATE_CPU1` (global); params
   as `static int32_t <instance>_<param>`; `pool` state as a `static <type> _buf[]
   UMETATE_POOL` ring buffer.

6. **Voice-allocator synthesis.** The voice zone's reserved **allocator inputs** —
   `note` (a MIDI note → `inc = note_to_inc(note) × ratio`, stored in each phasor's
   `inc` state), `gate` (event → the `env` nodes), `velocity` (control → the `vca`
   levels) — drive the allocator. These are **bindings, not graph edges** (the
   note→inc uses a table at note-on). Emit `note_on`: pick a free/stealable voice,
   set each phasor's `inc`, set `velocity`, trigger `gate`. Emit `note_off` (clear
   `gate`), `all_notes_off`, `quiet`, `lit`, `set_bend_q16` (the shared slot), and
   the `set_param`/`get_param` shared-array accessors.

7. **Code emission** — the fused `render` (inlines each node's `node.c` body with
   placeholders substituted — flat, monomorphic, no per-sample dispatch):

```c
void <synth>_dsp_render(int32_t *out, uint32_t frames) {
    for (uint32_t b = 0; b < frames; b += CONTROL_BLOCK) {
        /* control prologue (every CONTROL_BLOCK = 16..32 frames): control-rate nodes */
        for (uint32_t f = b; f < b + CONTROL_BLOCK; f++) {
            int32_t bus = 0;
            for (uint32_t v = 0; v < NVOICE; v++)   /* voice zone, SoA */
                /*   audio-rate voice nodes in topo order */
            bus = /* mix the NVOICE voice streams into the global bus */;
            /*   audio-rate global nodes in topo order (scalars) */
            out[f*2] = bus; out[f*2+1] = bus;        /* stereo, post-processed */
        }
    }
}
```

Each node's body is **inlined per sample** from its `node.c` template (§12.5)
— monomorphic, no per-sample dispatch. `delay1` emits a `static int32_t` register
(1-sample, so FM feedback is correct); `delayN` a `static` `.pool` buffer. The
voice→global boundary is an emitted `mix` that sums the `NVOICE` voice streams.
The placeholder substitution is **zone-agnostic** — a template writes `${state.x}`
once; the generator emits `x[v]` in the voice zone and `x` in the global zone
(auto-wrap). `@@read@@`/`@@write@@` markers in a template split a delay node's
register read (ordered first) from its write (ordered last), which is what makes
FM feedback exactly 1-sample.

**Schema note** (see `examples/pocket-drone/README.md` §5): the `voice` zone's
reserved allocator inputs `gate`/`note`/`velocity` are **bindings, not wires**; a
named `voice_out` marks the voice-zone signal summed into the global bus; macro
params may target a node's **state** (e.g. `ratio → phasor.inc`) as well as a port.
Add all of these to `patch.schema.json` at P0-1 (§12.7.5).

**Verification (host, no device).** A two-op FM example patch compiles; the emitted
`dsp.c` builds under gcc (host) and emscripten (WASM), then JieLi clang (P2-1);
`render(256)` matches a reference within tolerance; `lint --c` finds no forbidden
constructs; a bad edge (`audio→event`) is rejected; the same patch reproduces
byte-identical output.

### 12.5 The node library

The shipped DSP primitives — the framework's "batteries." Each node =
`node.json` (manifest) + `node.c` (the per-sample body **template**, inlined by the
generator) + a host parity test. The generator composes nodes into the §12.1 seam.

**Node contract (concretized).**

- **`node.json`** (manifest, `node.schema.json`): `name`, `ins`/`outs`
  (port → `event|control|audio` plus a Q-format `q15|q16|q32|phase` on control/audio),
  `params`/`state` (name → Q-format, or `pool` for a ring buffer). This is the single
  source of truth the generator validates against.
- **`node.c`** (the per-sample body template): regular C with placeholders the
  generator substitutes — `${in.<port>}` (input value), `${out.<port>}` (output
  local), `${state.<name>}` (state; **zone-agnostic** — auto-wrapped `[v]` for voice,
  plain for global), `${param.<name>}` (param value), `${v}` (voice index).
  `delay1`/`delayN` split with `@@read@@`/`@@write@@` markers (register read ordered
  first, write last — the sample-level cycle breaker). Example:

  ```c
  /* modules/osc/node.c */
  ${out.audio} = fm1_sin(${in.phase});
  ```
  ```c
  /* modules/delay1/node.c */
  @@read@@
  ${out.out} = ${state.prev};
  @@write@@
  ${state.prev} = ${in.in};
  ```

  Every placeholder is validated against the manifest at generation time (a typo is
  a `GenError`); a host parity test proves the template's per-sample form matches the
  scalar reference, so the inlining cannot silently diverge.
- **Rate:** a node is audio-rate if any port is `audio`; control-rate nodes run once
  per sub-block (their control outs are scalars), audio-rate nodes loop per sample
  (§12.4 pass 4).
- **Rules:** pure (no I/O/alloc/blocking), monomorphic, bounded; the ten rules and
  §12.2.4 emission rules apply.

**Shipped nodes** (c = control, a = audio, e = event):

| Node | Kind | Ins | Outs | Params | State |
| --- | --- | --- | --- | --- | --- |
| `phasor` | phase accumulator | `mod`(c), `fm`(a) | `phase`(c/a) | — | `inc`(q32), `phase`(phase) |
| `osc` / `table` | wave reader | `phase`(c/a) | `audio`(a) | `shape`, `level`, `phase_map` | — |
| `phase_shape` | dynamic phase shaper (VPS) | `phase`(c/a) | `phase`(c/a) | `d`, `v` | — |
| `env` / `seg` | segment generator | `gate`(e) | `cv`(c) | — (segments = data) | `stage`, `level`(q16) |
| `vca` / `mul` | gain | `audio`(a), `cv`(c) | `audio`(a) | `level` | — |
| `mix` / `add` | summer | `in0..inN`(a) | `audio`(a) | — | — |
| `svf` / `one_pole` | filter | `audio`(a), `cut`(c), `res`(c) | `audio`(a) | `cutoff`, `res` | `z1`, `z2`(q16) |
| `delay1` | 1-sample delay | `audio`(a) | `audio`(a) | — | `prev`(q15) |
| `delayN` | N-sample delay | `audio`(a) | `audio`(a) | `time`, `fb` | `buf`[`.pool`], `idx` |
| `noise` | source | — | `audio`(a) | `color` | `lfsr` |
| `ifft` / `add` | spectral | `bins`(c) | `audio`(a) | — | `buf` |

`env`/`seg` takes its shape as **data** (a `segments` table); an ADSR is one
4-segment table, not a distinct node (`docs/dsp-study.md` §3).

**Phase shaping split.** Static transfer (Casio CZ PD, the 8-waveform bitmask) is
**data** — `osc`'s `phase_map` table. Dynamic transfer (VPS) is **code + params** —
the `phase_shape` node (`d`/`v`, modulatable). Composition is `phasor →
[phase_shape] → osc.phase` in both cases (`docs/dsp-study.md` §2.5). **The `phase`
signal is Q32** (a wrapping accumulator), distinct from Q16 control — so ports carry
a numeric format (Q15/Q16/Q32) alongside the rate, letting the generator reject
`Q16 control → Q32 phase` mismatches (a `node.schema.json` port annotation).

**The §12.4 correction (feedback is sample-level).** FM/PM feedback
(`osc.audio → delay1 → phasor.fm`) needs a **1-sample** delay, but block
processing would turn it into 1-block (~5.8 ms) and sound wrong. The generator's
audio loop is therefore **sample-fused** (the §12.4 outer `for f` loop), with each
node's per-sample body inlined and `delay1`'s register breaking the cycle at sample
level via its `@@read@@`/`@@write@@` split. The host parity test proves the inlined
per-sample form matches the scalar reference, so the generator's inlining cannot
silently diverge.

**The FM "algorithm" is a macro.** Dexed/ymfm's 32 algorithms are 32 routings of N
operators, where an operator = phasor + osc + env + vca + `delay1` feedback
(`docs/dsp-study.md` §2.5). In umetate an algorithm is a macro wiring N `op` macros —
the decomposition is independently validated by the FM-chip authors.

**Host test per node.** silence/identity/bounded checks + a scalar-reference parity
test; a node without a test is not in the library (a "surface with no test is a
finding", §6.3).

### 12.6 The UI kit

**Where it runs.** CPU0, in `app_main`. Cold code, but bounded: rate-limited redraw,
`LCD_IDLE` integration, no display in the audio callback.

**Params live in shared `.bss` (the UI-read requirement).** The UI must both *set* and
*display* params, so params are a shared, single-writer array — CPU0 writes
(`set_param`/`set_bend_q16`), CPU0 reads (display/`get_param`), CPU1 reads (render,
block start). This refines §12.1: the note queue carries **events only** (notes);
params and bend are shared values, not queue commands.

```c
/* in aligned .bss (shared, csync); single writer = CPU0 */
extern volatile int32_t param_values[NUM_PARAMS];
extern volatile int32_t bend_q16;
```

**Data structures.**

```c
typedef struct { uint8_t kind;      /* BIND_PARAM | BIND_ACTION */
                 uint16_t source;   /* control/MIDI id: BTN_*, ENC_*, KEY, pad, fader, wheel, cc, note */
                 uint16_t target;   /* param id (BIND_PARAM) */
                 uint8_t action;    /* verb (BIND_ACTION) */
                 uint8_t arg;       /* action arg (context/page id) */
                 uint8_t behavior;  /* absolute/relative/momentary/latch/toggle */
                 uint8_t curve; } ui_binding;

typedef struct { const ui_page *pages; uint8_t n_pages;
                 const ui_binding *bindings; uint8_t n_bindings;
                 void (*on_enter)(void); void (*on_exit)(void); } ui_context;

static uint8_t ui_stack[UI_MAX_DEPTH], ui_sp;   /* context stack; top = active */
static const ui_binding ui_global[];            /* always-on, resolved last */

typedef struct { uint8_t type, row, col, span;  /* LABEL/VALUE/BAR/PARAM_ROW/
                                                   PARAM_COLUMN/LIST/GRID */
                 uint16_t param; const char *text, *unit;
                 int32_t last; } ui_widget;     /* last = drawn value (dirty check) */
typedef struct { const ui_widget *w; uint8_t n; const char *title; } ui_page;
```

**Main loop (resolution + dispatch + redraw).**

```c
for (;;) {
    platform_poll();
    /* events = input edges + encoders + pads/faders/wheels + MIDI */
    for (each event) {
        b = resolve(top_context.bindings, else ui_global, by source);
        if (b.kind == BIND_PARAM) param_values[b.target] = scale(v, b.curve);  /* → CPU1 next block */
        else                      do_action(b.action, b.arg);   /* push/pop/next_page/note_on(→queue)/… */
    }
    /* retained-mode redraw, rate-bounded ~30 Hz: */
    if (now - last_draw >= 33 ms)
        for (each widget on the active page)
            if (param_values[w.param] != w.last) { redraw(w.region); w.last = param_values[w.param]; }
}
```

**The retained-mode dirty/redraw engine** (the tested base): each widget caches the
value it drew (`last`) and redraws only its own region when its bound param changes;
the redraw is rate-bounded (~30 Hz); `LCD_IDLE`/`app_idle` keeps input/MIDI alive
during a DMA strip; the fault handler draws the safe-failure screen independently of
the UI. Hard rule: no display/flash/logging in the audio callback.

**The panel generator (panel.json → ui.c).** Emits `ui_context[]`, `ui_page[]`,
`ui_widget[]`, `ui_binding[]`, `ui_global[]`, and `param_values[]` (sized to the
patch's flattened params). Maps the panel's `param` names to param ids; the dispatch
is a table lookup. The context-stack runtime is shipped; the tables are generated.

**Host UI tests.** scripted keys/knobs/screen captures; a param write is visible on
the next redraw; a mode override (`KEY → set_step`) beats the global (`KEY →
note_on`); no display in the audio callback (lint + disasm).

### 12.7 CLI, build pipeline, and tests

#### 12.7.1 CLI module contracts

One module per command; each exposes `main(argv) -> int`. **Exit codes:** `0` ok,
`1` error, `2` usage, `6` wrong-model (flash). `quick-check`/`deep-check` report the §5.5
status vocabulary. No import side effects; `runner.py` is the WSL2/Docker POSIX
shim; `generate.py` is a pure function.

| Module | Command | Contract |
| --- | --- | --- |
| `cli.py` | dispatch | `argparse` subparsers; `help CMD` documents every option |
| `quick_check.py` | `quick-check` | read-only env report (native/host/target/device/repo); `--json`, `--strict` |
| `setup.py` | `setup` | opt-in, non-silent toolchain+SDK install into the Docker volume + Rust + fm1-emu on the host; `--toolchain auto\|PATH`, `--sdk auto\|PATH`, `--clock 240\|320`, `--no-emulator`, `--dry-run`, `--json`, `--yes`; version- + hash-verifies against `env.lock` (mismatch aborts unless `--force`) |
| `build.py` | `build` | generate + target compile + packager → `.fwsc` (Docker); `blocked` without the toolchain; `--board/--model/--dsp/--clock/--profile` |
| `emu.py` | `emu` | run your firmware in fm1-emu: the GUI (`fm1-live --fwsc`, `--persist`, `--midi`) or headless (`--check` → `fm1-emu` WAV/regression); `_emu.py` holds the shared paths |
| `generate.py` | (internal) | patch + panel → `dsp.c` + `panel.h` (UI tables); `params.json` + `tables.c` are P3-3 |
| `deep_check.py` | `deep-check` | host/web/safety/links/skill checks |
| `inspect.py` | `inspect` | read a `.fwsc` (identity/CRC/model/damage) without a device |
| `flash.py`/`debrick.py` | `flash`/`debrick` | the two device-writing commands (host-side, §8 gates) |
| `scaffold.py` | `scaffold node\|macro\|patch` | generate a skeleton; `--template` copies a shipped template |
| `lib.py` | `lib list` | list the shipped nodes + templates (local only) |
| `lint.py` / `fmt.py` | `lint --c` / `fmt` | the custom safety checks / clang-format |
| `web.py` | `web-build` / `web-serve` | emscripten → `dsp.wasm` + a minimal harness / loopback serve |
| `status.py` / `evidence.py` | `status` / `evidence` | parse the roadmap's per-layer claim ledger / validate an evidence matrix |

#### 12.7.2 The build pipeline (one generated `dsp.c`, three targets)

```text
patch.json + panel.json + node manifests
        │  generate.py  (host, pure Python)
        ▼
dsp.c (engine) + panel.h (UI tables)          (+ params.json + tables.c in P3-3)
        │
        ├──▶ host   → `deep-check --host`  (gcc/clang + test harness  →  vectors)
        ├──▶ WASM   → `web-build`          (emscripten + js adapter   →  dsp.wasm, no import section)
        └──▶ target → `build`              (JieLi clang + RIB runtime →  .fwsc)
```

The three branches are **separate commands**: `build` owns the target branch (and is
`blocked` without the toolchain), `deep-check --host` is the no-toolchain iteration
loop, `web-build` the WASM lab.

The **same** `dsp.c` is the input to all three; the §12.2.2 portability macro makes
it compile everywhere. `generate.py` is deterministic (same inputs → byte-identical).

#### 12.7.3 The test harness

- **host DSP vectors:** silence before note_on; bounded non-silent after; exact
  silence after note_off; `set_param` clamp + bad-id rejection; `quiet` toggles;
  `render(256)` parity vs a scalar reference (proves the inlined form matches the
  tested block form, §12.5).
- **host UI tests:** scripted keys/knobs/screen captures; a param write is visible
  on the next redraw; a mode override beats the global; no display in the audio
  callback.
- **ring tests:** SPSC wrap-around, overrun counter, no lost note-off.
- **evidence matrix:** per §5.5, each layer recorded, `blocked`/`not-run` not passes.

#### 12.7.4 The schematic engine

`scaffold node|macro|patch --name` generates a default from the templates/schemas
(the user fills the process body / wires), or `--template` copies a shipped template;
`lib list` shows the shipped nodes + templates (local only). Everything is also
doable by hand against the schemas (the Angular escape hatch).

#### 12.7.5 Schema close-out (the worked-example gaps)

Add to `patch.schema.json`: (a) the `voice` zone's reserved allocator inputs
`gate`/`note`/`velocity` (bindings, not wires); (b) a named `voice_out` (the
voice-zone signal summed into the global bus); (c) macro params may target node
**state** (applied at note-on) as well as ports. Add `q12` to `node.schema.json`
state kinds. All at P0-1. See `examples/pocket-drone/README.md` §5.

### 12.8 The CLI codebase

**Three layers**, each a separate import surface, no import side effects:

1. **Dispatch** — `cli.py`: `argparse` subparsers, `help CMD`, maps a command to its
   module's `main(argv) -> int` and the return to an exit code.
2. **Commands** — one module per command, each `main(argv: list[str]) -> int`.
3. **Services** — `config.py` (dataclasses), `evidence.py` (the Status/Layer
   vocabulary), `runner.py` (container exec), `generate.py` (the pure generator),
   and `_checks/` (the internal lint/budget/wasm/skill/link checks).

**Package layout.**

```text
umetate/
  __init__.py   cli.py                    # dispatch, help, exit mapping
  config.py     evidence.py               # BuildConfig/EnvConfig; Status/Layer Enum
  runner.py     generate.py               # container exec; the patch generator (pure)
  _ir.py        _frontend.py  _backend.py # generator internals (§12.4): IR, passes, emission
  quick_check.py setup.py build.py deep_check.py inspect.py
  flash.py debrick.py                       # device writes (host-side, §8)
  scaffold.py lib.py                        # the schematic engine
  lint.py fmt.py web.py status.py evidence.py
  _checks/                                # lint checks, budget, wasm, skill, links
  test_cli.py  test_generate.py           # the CLI + generator contract tests
modules/<node>/node.json + node.c         # the node library (§12.5)
```

**The data model.**

```python
# evidence.py — the vocabulary, one place (§5.5)
class Status(StrEnum):
    PASS="pass"; FAIL="fail"; BLOCKED="blocked"
    NOT_APPLICABLE="not-applicable"; NOT_RUN="not-run"
class Layer(StrEnum):
    SOURCE="source"; HOST="host"; BROWSER="browser"; TARGET="target"
    EMULATOR="emulator"; TIMING="timing"; DEVICE="device"; RELEASE="release"

# config.py — frozen, validated on construction
@dataclass(frozen=True)
class BuildConfig:
    board: str = "fm1"; model: str | None = None
    dsp: str = "integer"; clock: int = 320; profile: str = "perf"
@dataclass(frozen=True)
class QuickCheckReport:
    layers: tuple[LayerReport, ...]; summary: dict[Status, int]
```

**`quick-check` vs `deep-check`.** `quick-check` is a fast, read-only presence/version
probe (per §5.5 layer): `source` = git repo + clean tree + `mypy --strict`/`ruff` +
schemas; `host` = container up + `cc`/`cmake`/`ninja`/`python3`/`node`/`emcc` resolve;
`browser` = emscripten present; `target` = `/opt/jieli` toolchain version + SDK asset
hashes vs `env.lock`; `emulator` = fm1-emu present; `timing`/`device` = a host USB
probe + the device identity; `release` = tag + package hashes. `deep-check` is the
deep one (runs the host tests + `_checks/`). `--json` emits
`{"layers":[{"layer","status","detail"}],"summary":{…}}`; `--strict` turns a
non-device `blocked` into a non-zero exit.

**The status ledger (`status.py`).** The roadmap is the single status authority; `status`
parses its step/phase headers and renders a per-layer summary. The convention it reads
(tolerant — a non-matching header is skipped, never an error):

- a step: `**P<n>-<m> — <name>.** — <per-layer status>… **Layer: <layer>.**`
- a phase: `### Phase <n> — <name> (P<n>) — <per-layer status>`

`<per-layer status>` is a comma list of `done|blocked|in progress (<layer>)` pairs,
mapped onto the §5.5 `Layer`/`Status` enums above (e.g. `done (host), blocked
(target/device)` → `HOST=pass, TARGET=blocked, DEVICE=blocked`). Unknown layers and
unparseable headers degrade to a `not-run`/skipped row, so a prose reword never breaks
the command.

**The runner (the platform abstraction).** Everything POSIX — the target build, the
host DSP tests, the WASM build, clang tooling — runs in the pinned container:

```python
def ensure_container() -> None                        # start umetate-host-build if absent
def run(cmd: list[str], *, cwd: str, env: dict) -> int   # docker exec
def probe() -> HostProbe                              # container + toolchain volume present?
```

Model: a **persistent container** (started once, `docker exec` per command), the
`umetate-target` volume mounted read-only at `/opt/jieli`, the repo mounted
read-write. One-shot `docker run` is rejected (too slow per build). On Windows the
runner uses native **`docker.exe`** (Docker Desktop; its WSL2 backend is transparent
to the CLI), falling back to `wsl docker` for WSL-only setups; the docker binary is
overridable via `$UMETATE_DOCKER`, and Windows↔container path translation lives in
one place (`_to_container_path()`). **Device writes are the exception** —
`flash` runs on the *host* over **USB-MIDI SysEx** (mido + python-rtmidi);
`debrick`'s mask-ROM route is the USB_KEY dongle + `jl-uboot-tool` (delegated).
None of these use the runner.

**Command → module → data flow.**

| command | flow |
| --- | --- |
| `build` | `generate.py` (pure) → `runner.run` (target build) → the packager → `.fwsc` |
| `inspect` | read a `.fwsc` (identity/CRC/model/damage) — pure, no runner, no device |
| `quick-check` | `runner.probe()` + a host USB probe → `QuickCheckReport` (read-only) |
| `flash` | host-side **MIDI SysEx** (mido + python-rtmidi, §8 gates) — not the runner |
| `debrick` | USB_KEY dongle → mask-ROM UBOOT → `jl-uboot-tool` (delegated), §8 gates |
| `scaffold`/`lib` | pure Python over templates/schemas — no runner |
| `deep-check` | `runner.run` (host tests) + `_checks/` (lint/wasm/skill/links) |
| `lint`/`fmt` | clang-tidy/clang-format via the runner + the custom `_checks/` |

**The checks (`_checks/`, one module each).** `deep-check` runs the checks for the
requested layers; each reports per the §5.5 vocabulary:

- `lint` (source) — the C standing checks: SEC-1 MAXP bounds, SEC-2 UAC access,
  ROM-address constants, HAL-only MMIO, the flash-busy call graph, no `double`/
  64-bit-div/allocation in the DSP TU (`.clang-tidy` + the custom checks).
- `budget` (target) — the link report: `.dsp_text`/`.pool`/`.cpu1_bss` fit the
  §12.2 flash/RAM map; run by `build`, fails on overage (never silent).
- `wasm` (browser) — `dsp.wasm` is standalone (no import section); P4-1 adds the
  host↔browser parity within tolerance.
- `skill` (source) — the two offline skills (development, safety) have `SKILL.md` +
  `references/` present and valid.
- `links` (source) — the docs' cross-references resolve (no dead links).

Flags: `--host` (host vectors + UI tests), `--safety` (lint), `--web` (wasm),
`--skill`, `--links`, `--all`; `lint --c` runs the `lint` check standalone.

**Config & exit model.** Committed `env.lock` (toolchain/SDK pins + hashes); an
ignored per-checkout env file (toolchain/SDK paths + the `--clock` choice). Build
options are flags. Exit: `0` ok, `1` error, `2` usage, `6` wrong-model; `quick-check`/
`deep-check` return non-zero on a `fail` layer (and on a non-device `blocked` under
`--strict`).

**The CLI's own tests.** `umetate/test_cli.py` — contract tests: every command has
`--help`; `quick-check --json` validates against the §5.5 layer/status shape; a fake
device exercises `flash`/`resume` without hardware; `scaffold` output builds and
passes `make test`.
