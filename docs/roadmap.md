# umetate — Architecture & Implementation Roadmap

**Project:** umetate — a simpler, clearer, better toolkit for building custom
M-VAVE FM-1 / SMK-37 firmware, inspired by (but independent of) fm1tk.
**Author:** P1Onken. **Licence:** GPL-3.0-only. **Status authority:** this file
(`docs/roadmap.md`). **Date:** 2026-10-25.

This file is the single source of truth for the design and work order. A fresh
agent should be able to follow it from top to bottom without prior context. Keep
prose spare; each fact has one home.

---

## 1. Decisions (settled)

| # | Topic | Decision |
| --- | --- | --- |
| D1 | Name / authorship | `umetate`; commits credited to P1Onken; not endorsed by M-VAVE. |
| D2 | Starter firmware (RIB) | Dinghy/Felucca lineage, source-owned, integer-first C. Out of the box it supports **SMK-37**, **dual-core**, **single-precision FPU (opt-in)**, and the **JieLi acceleration hardware**. Performance + stability; extendible + maintainable. |
| D3 | Dual-core | **Default and the only architecture.** CPU0 = platform/OS/USB/MIDI/UI/flash/watchdog/installer **+ a split voice-render range** (D3's split-core refinement, §4.2); CPU1 = the remaining voice range. A boot-time core-1 probe + runtime fallback to CPU0 is the *stability* net, not a build profile. |
| D4 | FPU | **Opt-in** (`--dsp float`). Single-precision only; `double` prohibited; only the DSP translation unit uses FP. |
| D5 | Clock | Setup offers **240 MHz or 320 MHz**. 360 MHz and 396 MHz are not offered (see §5.1). Firmware reports the measured clock; never assumes. |
| D6 | On-device identity | **Frozen**: `FM-1_990`, `SMK-37 Pro_990`, `SMK-37 Elite_990`, `MKE-P37_990`. Rename artifacts freely; never rename identity. |
| D7 | CLI device writes | The CLI drives flash/debrick **directly** (`flash`, `debrick`), always behind explicit approval + recovery/backup gates; never as a build/test side effect. |
| D8 | Document set | **Five canonical docs** (see §4.6) + one firmware-internal `firmware/README.md` + JSON schemas (artifacts). |
| D9 | Skills | Two skills (development, safety); each **bundles its references offline**. |
| D10 | Web target | A **WASM parity lab** (AudioWorklet, output at `build/web/`) + **fm1-emu** as the separate pre-hardware model layer. |
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

The `/old-reference` project had too much machinery in some places and left key
decisions open in others. umetate keeps the engineering discipline and drops the
ceremony.

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
  and a depth param; effective value = base + mod·depth at block rate. The node
  declares *capability* (`modulatable: true`); the **patch is the final spec** — it
  decides exposure (the `params:` surface) and wiring, so the end user of the
  finished synth never sees the node flag. The additive form only makes sense for a
  **Q-format (continuous)** param — e.g. `pulse.width` (q15). A **discrete index**
  (`naive_osc.shape`, `osc.waveform`) is *not* additively modulatable: a q15 mod
  signal would swamp a 0..N index, so it is set via `set_param`, and morphing
  between shapes would be a separate node. A param with a natural control input
  (pitch, level, cutoff) stays a wired input. An unwired `<param>_mod` folds to
  `base` at `-O2`, so marking a param modulatable costs nothing until it is used.
- **Shape data:** wavetables, segments, spectra, phase-maps live in `tables:` →
  `const` XIP arrays.
- **Events:** `{kind: note_on|note_off, note, velocity}`; nodes derive gate/trigger.
- **Multiplicity:** patch zones — `voice` = SoA × NVOICE, `global` = single.

**Evaluation is multi-rate, not reactive.** The render is split by rate — sample /
block (`block_derived`) / note (`note_derived`, `note_tune`, `note_cutoff`,
`note_reciprocal`) — never by change-detection. Compute-on-change reactivity and
memoisation are **rejected**: modulation changes every block, so a per-change
dirty-check would only tax the hot path. There is no `param_derived` rung and no
reactive graph.

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
├─ modules/                 # module library (§6.9): nodes/ (reviewed nodes) + macros/ (subgraphs)
│  ├─ nodes/<node>/         #   node.json (manifest) + node.c (per-sample body)
│  └─ macros/<name>/        #   macro.json (a reusable subgraph)
├─ build/web/               # the WASM parity lab output (`web-build` → standalone dsp.wasm + page)
├─ skills/
│  ├─ umetate-development/  # component 2 (SKILL.md + generated references/)
│  └─ umetate-safety/       # component 3 (SKILL.md + generated references/)
├─ templates/
│  ├─ synth-brief.md  project-plan.md  feature-contract.md
│  ├─ supported-load-profile.md  evidence-matrix.md  control-map.md
│  ├─ dsp-algorithm.md  code-structure.md
│  └─ scaffold/             # params.schema.json, node.schema.json, patch.schema.json, panel.schema.json
├─ docker/                  # component 4: Dockerfile, build.sh, compose, .env.example
├─ docs/
│  ├─ roadmap.md            #   THIS document (status authority)
│  ├─ platform-facts.md     #   hardware facts + device safety + recovery taxonomy
│  └─ tutorial.md           # component 6
├─ provenance/              # baseline + release records (evidence, not status)
└─ examples/                # worked example(s)
```

Hard rule: **one firmware root** (`firmware/`, no nesting), **one status
authority** (`docs/roadmap.md`), **one CLI entry point** (`umetate`). Generated
views (`gen/`, skill `references/`, the `build/web/` artifacts, generated `dsp.c` and
param tables) are produced by a generator, never hand-edited.

### 4.2 Runtime ownership (dual-core — the only way)

| Core | Owns | Must not |
| --- | --- | --- |
| CPU0 | boot, OS/runtime, USB (MIDI + UAC), MIDI UART, panel/UI, display, storage/flash, watchdog, update installer, recovery; **the global control prologue + global audio post + its split voice range** | long DSP work; FP when CPU1 owns the FPU |
| CPU1 | DSP render: **its split voice range** | OS calls (incl. `printf`), allocation, flash, USB, blocking |

- **Split-core render (D3 refinement).** The render is three phases: (a) the global
  control prologue (pitch env, LFO, algorithm, glide, delay countdown) — single
  core; (b) the per-voice synthesis (`render_voices_block`, one CONTROL_BLOCK, a
  voice range `[v0, v1)` into a caller bus) — the parallel phase; (c) the global
  audio post (filter/wavefolder) + output — single core. The generator emits
  `render_voices_block` as a `noinline` phase so the voice range can be split
  across cores: CPU0 renders `[0, N0)`, CPU1 renders `[N0, NVOICE)`, the buses are
  summed, then the post runs on one core. Single-core is the same three phases
  with one range `[0, NVOICE)`. The per-voice control temps are file-scope arrays
  (the two cores write *disjoint* `v` ranges, so no race). The `noinline` phase
  costs ~5% single-core render time (measured ISR% 18.2→19.1 M/s @ 6 voices,
  21.7→23.0 @ 8 voices, bit-identical output) — the price of the split-ready seam;
  the parallel speedup dwarfs it.

- **Split dispatch (implemented).** The seam's `render_block` now runs on CPU0 and
  calls the generated `render_split`: per block it runs `render_pre_block`, hands
  CPU1 the `[N0, NVOICE)` range through the mailbox, runs `[0, N0)` on CPU0 in
  parallel, joins, sums the two `render_bus` buffers, then `render_post_block`.
  `N0 = cpu0_voices` (a patch field, default `NVOICE/2`). The mailbox is reached through thin non-inline wrappers
  `fm1_cpu1_dispatch`/`fm1_cpu1_join` (declared in `fm1_ipc.h`, defined in
  `platform.c`), because `fm1_cpu1.h` owns `fm1_c1_main` and must stay a single TU.
  Measured (emulator, 320 MHz, 8 voices): output bit-identical; CPU0's ISR rises to
  ~26% (its 4-voice half) from ~7% (the spin-wait), i.e. the render now spans both
  cores. **Ceiling test (measured):** at `NVOICE` 16 the emulator shows 50% ISR, at
  20 it shows 61% — no halt at either, i.e. the split reaches the stock's 20-voice
  target with headroom. Voice stealing is unaffected and verified: a host test
  fills the pool then adds an 11th note and the *oldest* note (21) is stolen, the
  rest sounding (the score picks `min(voice_age)`; the retrigger/stacking contracts
  in `test_generate` still pass).

- **Steal stress + UB fix.** A 40-note storm on a 20-voice pool (80 voice-requests,
  60 oldest-steals ×3 rounds) under ASan+UBSan passes: no OOB, no stuck notes, the
  oldest notes stolen, silence after all-off. UBSan surfaced a real latent bug in
  two nodes — `(int64_t)x << 16` (a left-shift of a negative signed int64, UB in C)
  in `phasor` (the FM index) and `wavefolder` — fixed to `(int64_t)x * 65536`
  (well-defined, identical on two's-complement). The emulator's `--keys` note
  display uses key indices, so its apparent non-oldest steal is a numbering
  artifact, not a firmware bug (settled by the host test).

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
umetate deep-check  [--host|--web|--safety|--python|--skill|--links|--pyright|--all]
umetate inspect    PACKAGE                   inspect a .fwsc without a device
umetate flash      PACKAGE [--port NAME] [--device] [--yes]   flash; identity + CRC + model checked; resumes a device in update mode
umetate debrick    [--route app-rescue|update-loader|mask-rom]   name a recovery route + its procedure (mask-rom: blocked, needs the USB_KEY dongle)
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

Offline-bundled interactive loop with a **design-first gate**: no code is written
until three artifacts are complete, mutually consistent, and user-confirmed — the
**synth design + voice architecture** (node/macro graph, parameter manifest,
tables), the **GUI design + control flow** (context stack, pages, bindings,
navigation, per-context control meaning), and the **implementation plan**
(milestones, feature contracts, supported-load profile, evidence matrix, the DSP
algorithms, and the exact structure + interface of any custom code). The plan's
DSP-algorithm step requires **online research** (default reference points: ymfm,
SuperCollider UGens, Mutable Instruments, STK, maximilian, musicdsp; credit given
and licences honoured), with performance and memory safety as standing constraints.
A consistency gate cross-checks the artifacts (every binding → a defined param,
every control mapped or explicitly unmapped, the voice count × architecture within
budget) before authoring begins; authoring is then mechanical translation into
`patch.json` + `panel.json`. Workflow: orient → design interview → GUI interview →
plan → consistency gate → author (nodes/macros/patches via `scaffold`) → first
slice → shared DSP → panel/display → MIDI/persistence → verify (evidence matrix) →
handoff. Refuses device writes unless the user explicitly requests that action and
§8 gates pass.

`references/` (generated, offline — byte-for-byte copies of the canonical docs,
verified by `deep-check --skill`): AC79 facts, flash maps + protected ranges, the
port-kit mapping patterns, the node/macro/patch schemas, the recovery taxonomy, the
evidence vocabulary, the code conventions. The synth-project templates
(`templates/*.md`, including `dsp-algorithm.md` + `code-structure.md`) are
referenced by repo path, not copied into the bundle.

### 6.3 Skill: umetate-safety

Offline-bundled. Triggers on memory-safety review, USB/UAC/MIDI/OTA attack
surfaces, package identity, flash writes, and any device write. Maps each surface
(USB EP0/EP1/EP3, UAC tap/FIR/DMA, MIDI SysEx, OTA parser, update loader,
flash/store, package identity, host installer, build supply chain) to code, a test,
or an explicit gate. Owns the device-write gate (§8). Its `references/` are the
generated recovery taxonomy + code conventions (same drift-checked copies).

### 6.4 Docker image + volume

- Image (`umetate-host-build:latest`): Python 3.11+, Node 20+, Git, CMake 3.20+,
  Ninja, a C compiler, Pillow, jsonschema, ruff, mypy, pyright, Emscripten 6.0.13.
- Volume (`umetate-target`): JieLi pi32v2 toolchain + AC79 SDK assets
  (`uboot.boot`, `cfg_tool.bin`, `eq_cfg_hw.bin`), mounted read-only at `/opt/jieli`.
  **Not** baked into the image (vendor-terms compliance). `umetate setup` populates it:
  auto-fetch (toolchain from `pkgman.jieliapp.com`, SDK from gitee, both with opt-in
  consent) or a user-supplied path; version- + hash-verified against `env.lock`.
- Windows: everything through WSL2 → Docker.
- **The image/container are rebuilt, not edited:** after a `docker/Dockerfile` or
  `env.lock` pin change, rebuild the image and recreate the persistent
  `umetate-host` container — a stale image silently drops a tool (e.g. pyright).
  `deep-check` must report a missing tool as *not-run* and fail, not crash with
  `FileNotFoundError`.

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
This section summarizes the rules; the full detail stays in `firmware/README.md`.

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
  `firmware/tools/gen_math_tables.py`), enforced in the build, plus
  `disallow_any_explicit` + `disallow_any_unimported` — **`Any` is banned**. Every
  public function/module is annotated; the fm1tk-lineage `firmware/tools/` +
  `tests/` are excluded (strangler-fig'd, not typed in place). Modern style: PEP 585
  (`list[int]`), PEP 604 (`int | None`), `from __future__ import annotations`,
  `TypeAlias` for callable/union aliases, `Protocol` for structural typing across
  module boundaries (avoids import cycles), `NamedTuple` for tiny value types.
  **Pyright (Pylance) checks the same files in strict mode** (`[tool.pyright]` in
  `pyproject.toml`, run by `deep-check --pyright`) — a second engine that catches the
  "partially unknown" cases `mypy`'s flags can't see (an `argparse` attribute in a
  `list[str]`, `field(default_factory=dict)`, a `NotRequired` key indexed with `[]`),
  so the editor and CI agree.
- **Manifests are typed, not `Any`.** Every JSON manifest (`patch`, `macro`,
  `node`, `panel`, `tables`, `params`, `env.lock`, the evidence matrix) is a
  `TypedDict` in `umetate/_schema.py` mirroring its `templates/scaffold/*.schema.json`.
  The JSON boundary (a `json.loads` result) is narrowed by one `as_*` loader per
  manifest — an `isinstance` check on the required keys, then a single `cast` to the
  concrete `TypedDict` — so downstream code is fully checked. The fm1tk boundary
  (`firmware/tools/fm1_install.py`) is the one trusted `cast` to the `Installer`
  `Protocol` (in `_installer.py`); the raw module stays available as
  `load_installer_module()` for the package-synthesis tests.
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
`params.js`, skill `references/`, the `build/web/` artifacts carry `// GENERATED — do not
edit`; the generator is authoritative.

### 6.9 Module library (the batteries)

Shipped, reviewed nodes in `modules/nodes/`, each = `node.json` + `<node>.c` + a host
test + a budget annotation; shipped macros in `modules/macros/`, each =
`macro.json` (a reusable subgraph, same shape as a patch's `macros:` entry). The
node library is generated from the manifests into
[`docs/module-library.md`](module-library.md) — one row per node (summary + ports +
params + state); `umetate lib generate` rewrites it and `deep-check --lib` fails on
any drift, so it cannot lag the library.

`umetate lib list` shows the library; `umetate scaffold --template` starts from a shipped template; user
nodes conform to `node.schema.json`, patches to `patch.schema.json`.

The **fourop-fm dogfood** (`examples/fourop-fm/`) surfaced two known gaps (recorded,
not fixed there):

- **Patch `params:` `default` is ignored.** `patch.schema.json` accepts a `default`
  on a param binding, but the generator uses the node param's literal as the DSP
  initial value and never reads the binding's `default` (the generated `params.json`
  `default` is the node value). A patch's per-node `params` are the real source of
  the initial value today.
- **`svf` has a sub-LSB limit cycle.** The Chamberlin SVF never reaches *exactly*
  zero after the input stops (a ~±3 LSB, ≈ −80 dBFS fixed-point limit cycle), so a
  patch with a post-voice filter fails the strict "silent after off" host contract;
  the dogfood adds a decay-to-near-silence contract instead.

The `table` node makes `tables:` shapes audible: `triangle`/`square`/`saw`/`pulse`
are `tables:` `wavetable` shapes + `table` (data), and the **spectral oscillator**
is `tables:` `spectrum` (additive/IFFT) + `table`.

**Backlog (post-baseline, proposed order).** The `/`-suffixed names above are the
planned half of each shipped node; the full follow-up, classified by the "one node
= one algorithm; shape/spectrum/envelope = data" rule:

| Item | Kind | Note |
| --- | --- | --- |
| ring mod | — | already `vca` with an audio-rate CV |
| high-pass | — | the `svf` high-pass output |
| `comb` | — | `delayN` with feedback (already shipped); no macro needed |
| `apc` / `dual_apc` | macro | square `table` + env / two cross-modulated squares |
| `vps` | macro | DAFx-11 (Kleimola et al.): 2-D inflection point `p=(d,v)`, multi-breakpoint, audio-rate modulation — dynamic phase distortion, generalizes `phase_map`. The single-breakpoint, control-rate case is now `phase_shape` (and `phase_dist` = the `v=0.5` classic); the multi-breakpoint/audio-rate macro is the remaining extension. Follow-up: the `phase_shape` slope divisions (2 signed 64-bit per voice per block, ~10–20% of a block at 20 voices) should be hoisted to note-rate when `d`/`v` are unmodulated, or replaced with reciprocals |
| `formant` (K5000-style) | macro | bank of `svf` band-passes + vowel presets |
| `granulator` (Xenakis) | node(s) | phase-granular (no audio buffer) + a separate stochastic/GENDYN node |
| SN76489 tone | example | naive square + the chip's 16-step volume ladder as `tables:` data — the "decaying pulse / gloomy" character; no new nodes |
| `k5000` additive | example | additive/IFFT via the spectral oscillator (`tables: spectrum`), reduced harmonic count for the pi32v2 (post-baseline) |

`svf`, `wavefolder`, and `fm_op` shipped first (the "batch 1" build); `lpg`, the
spectral oscillator, the `table` reader, and the band-limited `saw` followed. The
`saw` is a 2nd-order polyBLEP: `note_derived` sets its `inc` and `note_reciprocal`
sets `inv_inc = 2^32/inc` at note-on (a Q32 reciprocal, so `ph·inv_inc` is the Q32
fractional phase `ph/inc` with no per-sample divide); its anti-aliasing is verified
host-side by a spectral test (the near-Nyquist harmonic is ~2.5× lower than a naive
saw, and the full-scale wrap jump is gone). The **note-derived cutoff** feature
(`note_cutoff`, `field = 2·sin(π·note_to_inc·ratio/2^32)`) and its consumer
`track_bp` + the `pitched_noise` macro (`noise` → note-tracked band-pass) closed
out the generator feature list. The **phase shaping** pair (`phase_shape` = VPS,
`phase_dist` = classic PD with `v=0.5`) and the **naive oscillator** (`naive_osc` +
`naive_vco` macro, saw/sine/triangle/square, non-band-limited by design) followed:
the naive VCO is `tuned_phasor` (octave/semi/cent tuning, note-derived via
`fm1_tune_q16` = 2^(octave+semi/12+cent/1200)) → `phase_dist` (PWM) → `naive_osc`.
The **band-limited oscillator trio** is complete: `saw`, `pulse` (square/PWM via a
modulatable `width` param, two BLEPs), and `triangle` (the polyBLEP'd square through
a leaky integrator) share one `fm1_poly_blep` residual in `fm1_math.h` (Tale /
Martin Finke); `saw`/`pulse` attenuation and the triangle's 1/n² spectrum are
verified host-side. The **D23 modulation mechanism** is now implemented: a
`modulatable` param (e.g. `pulse.width`) gets a synthesized `<param>_mod` control
input + `<param>_depth` param, and its value becomes `base + mod·depth` at block
rate (verified by a host test that an LFO wired to `width_mod` changes the output
only when `width_depth` is non-zero). Shipped macros live in `modules/macros/`; a
patch's own `macros:` section shadows them.

The **fourop-fm dogfood** (`examples/fourop-fm/`) closed the runtime-algorithm
gap: `dx_env`, `osc.waveform` (12 waveforms, the OPZ+OPL union), `vca.level`,
`mix4` (the 2-input `mix` → 4-input `mix4`), `route4`, `route`, `lfo` (the
control-rate vibrato/tremolo source), and the `fm_op` rewrite (per-op tremolo +
a `pitch` input), with the **algorithm as a runtime `routing` matrix** — a
`tables:` entry applied by `route`/`route4` rather than a compile-time graph —
plus the `<<16` FM-index scale on `phasor.fm`.

Build order: `fm_op` + `svf` + `wavefolder` → `ifft` + `lpg` → `pitched_noise` +
`formant` + the cheap macros → `granulator` last (research-driven). Band-limited
oscillators and the Xenakis stochastic engine are the two research-heavy items;
credit sources and honour licences per the development skill.

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
- **Theme (palette):** a small, verified-contrast colour set — background / surface /
  text / muted / accent / success / warning / error — with a **dark-mode default**
  meeting the applicable WCAG 2.1 subset (1.4.3 contrast, 1.4.11 non-text,
  2.4.7/2.4.13 focus, 1.4.1 not-colour-alone). `umetate theme check|generate|emit`
  does the WCAG math + a contrast report + a C header; the shipped gfx.c palettes
  were re-verified and the three low-contrast label steps (AMBER/CYAN/RED) brightened
  to >= 4.5:1 (`test_theme.py` locks it). The theme is **wired into the firmware**:
  `firmware/theme.json` -> `firmware/gen/theme.h` (generated), gfx.c maps
  `C_WHITE` to the theme accent (selection) + `C_OK`/`C_WARN`/`C_ERR` for status,
  and ui.c draws the mute flag in `C_WARN` (with the "MUTE" text, so not colour-alone).
- **`scope` + `spectro` widgets** (shipped): the oscilloscope plots the last render
  block's left channel (`scope_push` in the audio ISR stores a bounded snapshot;
  `scope_at` reads it — one writer / one reader, no lock, a torn frame is harmless),
  and the spectrogram is an integer **Goertzel bank** over linearly-spaced bins
  (log-power, log2 scale — no float, no 64-bit divide on the soft-FP target). Both
  redraw on `scope_seq` (a new snapshot), bounded by the ~30 Hz retained-mode
  redraw. The core is **multi-channel** (`SCOPE_CH`): `scope_push_ch`/`scope_at_ch`/
  `scope_spectrum_ch` address a per-op/per-part tap channel (`<name>_dsp_tap`,
  §6.11.4), ch 0 = the final mix; the app glue pushes `N_TAP_CH` tap channels each
  block. Host-tested: snapshot round-trip, a 2000 Hz sine peaks at the right bin,
  per-channel isolation, and the 120-bin spectrum costs ~0.08 ms (well under a UI
  frame).

The panel schema is `templates/scaffold/panel.schema.json`; the interview fills
`templates/control-map.md`.

**Interaction design rules** (learned on the fourop-fm FM-1 exercise, and now in the
skill + tutorial):

- **Know each control's kind.** A smooth analog *pot* (the FM-1's `MASTER`) is
  volume and platform-owned — never bind it to a page slot; a detented *encoder* is
  a parameter control. Distinguish *dedicated* knobs (`ALGORITHM`, `PRESETS`) from
  *page-slot* knobs (`KNOB1–4`). Name collisions exist (`SELECT` knob vs `SEL`
  button) — read the `platform.c` enums.
- **Respect the silkscreen.** A control's printed label fixes its meaning; the
  firmware means what it says.
- **Keys are a menu surface.** The keybed is not just notes — keys double as
  shortcuts (operator select, mute).
- **Prefer the page-slot model.** A small fixed set of encoders whose meaning
  changes per page, with the labels shown on screen.

**fourop-fm panel.** The panel maps to the **real FM-1** control surface:
`ALGORITHM` is the always-on algorithm encoder; the **4-param page** model puts the
current page's params on `KNOB1–4`, `SELECT` cycles sub-pages (pitch → env-rates →
env-levels → tremolo → mute), `SEL` selects the operator (wrapping 1→4), and
`EDIT`/`FX`/`GLO` switch contexts (`op` = the operator editor, `fx` = the output
chain, `glo` = the global vibrato + pitch envelope). The three are **siblings**
(a `switch` replaces the current mode rather than stacking — so `FX` → `EDIT`
goes straight to the operator editor without passing through `HOME`); `HOME`
pops home from anywhere. The pages are operator-relative (`operators` +
`OP_ROW`/`OP_PARAM`), and each op page opens with a **`status` readout** (`ALG <n> ·
OP <n>/4 · MUTE`) so the algorithm, selected operator, and mute stay visible while
editing. **Mute** is a sub-page — the four knobs toggle op1–4 directly (no
long-press primitive). The **envelope graph** is an `envelope` widget that draws the
DX rate/level curve as **straight line segments** (an approximation — no curve
fitting), with stage length = the one-pole time constant `65536/rate`, and
deliberately **no "now-playing" stage cursor**: tracking live envelope state from
CPU1 is CPU-heavy and unsafe for the audio core. The widget declares its 7 params
explicitly (`params: [r1..r4, l1..l3]`), resolved to a per-operator `ENV_PARAM[n_op ×
7]` table — no "7 consecutive flattened ids" assumption. The `glo` page edits the
global pitch envelope (`penv_base`/`penv_rate`) and the vibrato. `feedback` is
**per-op + carrier**: each operator's `opN_feedback` (the op page) is summed with
the carrier-gated `feedback` master (the HOME knob) via `algo.fb1..fb4`; `master`
is dropped — the `MASTER` pot is the volume. `ratio` is the operator's **frequency
multiplier** — a q16 runtime param (`inc = note_to_inc(note) · ratio >> 16`, so
65536 = 1.0), not a raw increment.

---

### 6.11 fourop-fm firmware — the full-synth program

**Status:** done (F1–F8). This section records the plan that turned fourop-fm from
a patch-level generator dogfood into a complete example **firmware**, and folded
every lesson from that work back into the toolkit (interview loop, node library,
generator rails for voice management, presets/sysex/settings, CLI, and the
polyphony budget tool).

#### 6.11.1 Goal

A complete, worked firmware — `examples/fourop-fm/` builds a real FM-1 firmware —
that demonstrates the toolkit's full capability: polyphony + voice management,
velocity, MIDI (notes / CC / sustain / panic / bend), presets (save / load /
export / import via SysEx), system settings, and **2-part multitimbrality** with
split, layering, and MIDI-channel routing. Building it forces the toolkit
strengthening below.

#### 6.11.2 Lessons (from the work since `f0ff875`)

| # | Lesson | Fix (where) |
| --- | --- | --- |
| L1 | The control surface was fictional until late (`ENC_KNOB5–7`, `BTN_STOP`). | **Source-vocabulary check** — the panel generator validates `panel.json` sources against the board's `BTN_*`/`ENC_*` enums (a `lint`/`build` gate, not a doc note). |
| L2 | Param *semantics* were iterated 3× (feedback op1→carrier→per-op+carrier; `master` VCA→dropped). | `templates/synth-brief.md` §2.2 gains a **semantics** column — each param's *behaviour* is pinned before code, not just its range/curve. |
| L3 | Velocity / MIDI / persistence were "non-goals" and got skipped, not decided. | Interview rule (skill): a non-goal is a **written, justified decision**; the example must walk the full path (velocity → MIDI CC → preset) or defer each with a reason. |
| L4 | "Example" was ambiguous (patch dogfood ≠ firmware). | Tutorial + README define **two tiers** — patch-level (generator only) vs full-firmware (app glue) — and the path between them. |
| L5 | App glue (voice alloc, MIDI, presets) is hand-written per synth. | Ship a reusable **app framework** + generator **voice-management rails** (below). |
| L6 | Control/audio separation discovered late. | Already fixed (`cmul`/`csum` + the generic test); keep as a first-class invariant. |
| L7 | Nodes added reactively (`gain`, `cmul`, `csum`, `algo`, `mute`, `pitch_env`). | Review the node/macro library against the full-synth target for completeness. |
| L8 | The UI was **underspecified** — button meanings, page contents, and per-param semantics were decided during implementation, so the first emulator pass was "buggy, incomplete, cryptic" and a whole navigation/control map had to be re-derived *after* code existed. | **The UI interview must be written before the panel is coded** (control-map.md + synth-brief §3 as a *checked gate*, not a note): every button's meaning, every page's contents, the always-visible header, the shortcuts/chords, and each param's display form, all in one place. §3.1–3.5 + §2.1a/2.1b below are that spec now; a change to the panel must change them in the same commit. |
| L9 | A per-param *display scale* was missing — the panel showed raw integers (cutoff `8000`, ratio `65536`, mute `0/1`), and a relative encoder moved ±1 raw (thousands of detents across a 0..65535 range). | The `params:` `display` form + the curve-driven stepping (linear = a fraction of the range, log = multiplicative, clamped) — `ui_param_disp[]` (§12.6). |
| L10 | The *development skill* did not force a UI spec deep enough — it asked for a "context stack + pages + bindings", but not the **button-by-button meaning, page-by-page contents, the always-visible header, the modifier chords, the per-param display form, or the exact INIT-patch defaults** — so those were invented during code. | **Revamp the dev skill's GUI interview** so its *minimum bar* is the exact 10-item checklist below (button map · page map · header · param placement · per-param display + stepping · widget layout · preset browser · exact INIT PATCH/PART defaults · screen rules) — the fourop-fm restructure is the worked example. **Open** — not yet written back into `skills/umetate-development/SKILL.md`/templates. |
| L11 | A knob could slide *below* its display's minimum — RATIO read "0.50" while the internal value had gone below it, so scrolling back up showed nothing until the value re-entered the range (and an on/off could read "on" from a *negative* value); the range/unit/step resolution hadn't been settled up front. | The **user-facing range + clamp + unit + resolution is part of the param spec** — `params:` `min`/`max` + `display` are the clamp the stepper *and* the display both honour (a value never sits outside its range, and the display never disagrees with it); a *mute* reads inverted (`onoff_inv`: 0 = not muted = "on"); the GUI interview must settle each param's range, unit, and detent resolution before authoring the panel. |

**The GUI interview's minimum bar (L10 — exact).** The development skill's GUI
interview must treat the UI as *unspecified* until it has pinned, in writing, every
one of the following — a checkable list, not a sketch. fourop-fm (synth-brief §3)
is the worked example of the depth; the skill generalizes it to any synth.

1. **Button map, button-by-button.** Every physical button and encoder — its exact
   single-press meaning, *and* every multi-tap and hold-chord, *and* what each chord
   *replaces* (a chord that mutes must not also fire a note; a page removed from a
   menu is named as removed). fourop-fm: `ENV`/`LFO`/`EDIT`/`FX`/`GLO`/`HOME` select
   menus; `ARP`/`SEQ`/`PLAY`/`REC` are **operator mutes 1–4** (the EDIT mute
   sub-page is removed); `SCL` tap = next active operator, double-tap = switch the
   active part, `SCL`+`ARP`/`PLAY` = part 1 mute, `SCL`+`SEQ`/`REC` = part 2 mute,
   `SCL`+key = operator mute chord (not a note); the `PRESETS` encoder opens the
   patch browser; `KNOB1–4` edit the current page's params; `SELECT` = page up/down
   (wrapping).

2. **Menu/page map, page-by-page.** Every menu, its pages *in order*, the exact
   page count, and each page's exact contents. fourop-fm: `HOME` = 5 pages — (1)
   4-op envelope graphs, (2) 4-op oscilloscope, (3) 4-op spectrogram, (4) 2-part
   oscilloscope, (5) 2-part spectrogram; `ENV` = the op amplitude envelope in two
   pages (rates r1–r4, then levels l1–l3) followed by the per-part pitch envelope;
   `LFO` = the op amplitude LFO, then the per-part vibrato; `EDIT` = ratio · level ·
   feedback · waveform (one page); `FX` = filter (on/off, cutoff, rez, type, then
   its ADSR → cutoff) then fold (on/off, threshold, folds, type); `GLO` = per-part
   level + delay, single-part name, per-part voice mode (poly / unison / legato +
   unison voice count + detune + portamento time), single-part save/load from the
   preset store, MIDI channel, keyboard split, `INIT PART`; then multi-patch
   settings — multi-patch name, `INIT PATCH`.

3. **The always-visible header.** The exact fields shown on *every* page, at all
   times — fourop-fm: active part, active operator, each part's and operator's
   ON/OFF (mute) state, the current algorithm, the current menu, and the page N/M
   (`HOME 1/5`). No page may hide any of it.

4. **Param placement.** Which menu *owns* each param — no param is reachable only
   by accident. fourop-fm: filter + fold live in `FX` (the per-part pitch envelope
   lives in `ENV` after the per-op amplitude envelope, and the per-part vibrato in
   `LFO` — *not* in `FX`).

5. **Per-param display form + range/clamp/unit/resolution.** Every editable param's
   `display` form (raw / ratio / pct / pct_inv / onoff / onoff_inv / off_pct / hz /
   semi), its user-facing **[min, max] range** and unit, and the curve-driven
   stepping (linear = a fraction of the range, log = multiplicative, **clamped to
   the range so the display and the value never disagree**) — §12.6, L11.

6. **Widget layout.** Which widget each visual page draws and the ordering —
   fourop-fm: one widget per row in a column layout, part 1 / operator 1 on top.

7. **The preset browser + the save chooser.** The popup trigger, timeout, and
   load/erase rule — fourop-fm: the `PRESETS` encoder opens the **multi-patch
   (2-part)** browser as a popup; after 2 s with no preset-encoder input the
   selected patch loads and the popup clears, unless it is already loaded (then it
   just clears). Single-part presets load from `GLO`. **Saving** is a modal
   chooser (not a silent write): `SAVE` opens a two-row dialog — `single part` /
   `multi-patch` — `KNOB1` selects the row, `KNOB2` picks the slot, `SAVE` commits
   and `HOME` cancels (no idle timeout: a save is destructive and persistent).

8. **`INIT PATCH` defaults, exact.** fourop-fm: the **additive** algorithm; every
   operator gate-type envelope (instant rise to max on note-on, instant fall to 0
   on note-off), waveform 0, no feedback, ratio 1, all operators ON, part 2 OFF,
   part 1 active, operator 1 active, no pitch envelope / vibrato / tremolo, level 75.

9. **`INIT PART` defaults, exact.** The single-part equivalent of item 8, pinned as
   a list — the skill must not accept "same as INIT PATCH" without the values.
   (fourop-fm's exact `INIT PART` values are written when the `GLO` menu lands.)

10. **Screen rules.** Redraw model + rate, no display in the audio callback, full
    clear on page/menu change, held notes stay playable.

The GUI interview is *done* only when items 1–10 are all written in the brief;
L8's gate (§3.1–3.5 + §2.1a/2.1b) is that written spec, re-checked on every panel
change. **Open:** rewrite `skills/umetate-development/SKILL.md` and the
`templates/control-map.md` prompt to *require* items 1–10 and refuse to author the
panel until each is filled in — this list is that rewrite's spec.

#### 6.11.3 Locked decisions

- **Velocity** is a per-voice **control signal** (routable), applied to **three
  separate depth targets**: `vel_amp` (amplitude), `vel_rate` (envelope
  rate/time), `vel_fm` (FM index) — each 0..32767, default 0.
- **Parts**: 2, each an **independent timbre** (its own 68-param 4-op voice — the
  `fm_op` macro's 17 × 4 operators) plus
  `level` (amplitude), `delay` (note-onset offset, ms), `channel` (MIDI channel
  or omni), `low`/`high` (keyzone). Notes route by **channel + keyzone**;
  **layering** (two parts on the same channel/keyzone) is allowed and must be
  easy — building a sound out of partials is a first-class FM technique.
  Per-part parameter sets are the general multitimbral model the toolkit's
  voice-management rails must support.
- **MIDI CC**: fixed, generator-assigned (one CC per param, emitted from
  `params.json`), documented — not user-editable on-device.
- **Presets**: two tiers, as most synths do — **single parts** (one timbre:
  its 68 params + name) and **multi-patches** (a composition: which single part
  each of the 2 parts uses + each part's `level`/`delay`/`channel`/`keyzone` +
  name). 128 single-part slots and 64 multi-patch slots (chunked across the
  flash slot area's measured 16 372 B ceiling), flash, CRC + version; save /
  load / name; SysEx export / import. System settings (base MIDI channel, master
  tune) are a separate global record.
- **SysEx**: a shared, versioned envelope every firmware uses, with a
  per-firmware payload.
- **Polyphony**: `voices` is the **total shared pool** across both parts (not
  per-part — §6.11.4); the dogfood ships **20 voices**. Per-voice render cost is
  ~6.5% of a 320 MHz core block, linear. The **split-core render** (D3, §4.2)
  distributes the pool across both cores — 20 voices runs at ~61% ISR per core, no
  halt, with headroom to ~28–30 voices (single-core, before the split, the ceiling
  was ~15 voices at 320 MHz). Two render passes landed — the phasor's block-constant pitch multiply
  moved out of the sample loop, and the 12-wave `osc` switch became a precomputed
  `fm1_wave[12·1024]` table with a block-rate base — ~30% less render time.

  The **gap to the stock** is now pinned. The stock is a port of Google's **msfa**
  (the Dexed core, integer fixed-point, `AL-255/FM-1-RE`), and its efficiency over
  ours is *compiler codegen*, not hardware: the pi32v2 dual-issues (explicit VLIW
  `ins1 # ins2`) and has a `rep` zero-overhead loop, and the stock's compiler emits
  both (16 634 parallel pairs, 3 585 `rep`) while our **clang 4.0.1 emits neither**
  (`-mcpu=r3` vs `r3s` are byte-identical; only the hand-written `.S` files
  dual-issue). No community toolchain fixes this — the whole Felucca family is
  pinned to the same closed-source clang 4.0.1 fork. **Float is not the answer
  either**: the pi32v2 has a single-cycle 32×32→64 MAC (`r3_r2 += r1*r0`), so our
  integer Q15 multiply is already ~2 instructions, and float loses phase precision
  (24-bit mantissa < 32-bit phase). Remaining lever: hand-written asm for the hot
  loop (what the stock did; breaks the generated-C model).

  **Two source-level "obvious" optimisations were tried and rejected by the guard:**
  - the `fm1_q15_mul(x, 32768)` identity — folding the route's 0/1 weights to
    boolean selects (`w ? a : 0`) measured *no faster* (a data-dependent branch per
    term vs the straight-line MAC). The 32767 "1" keeps its 0.003% routing rounding
    (inaudible, documented in `dsp-algorithm.md`).
  - the **global-algo routing select** — hoisting the route's `alg` clamp to
    `block_derived` measured *no faster*: `alg` is a *global* scalar, so gcc already
    hoists its load + clamp + pointer arithmetic out of the sample loop, and the
    hoist forced a per-voice array read instead.

  **Universal lesson (the `block_derived` rule):** hoisting block-constant work to
  block rate wins when the value is **derived from per-voice state** — a per-voice
  array read the compiler *cannot* hoist out of the sample loop (the `osc`'s
  `waveform<<10` base and the `phasor`'s pitch-scaled `step` are the ~30% win, line
  908) — but is redundant or slightly worse when the value is **derived from global
  state** (the compiler already hoists a global scalar). `block_derived` is for
  per-voice array-derived block-constants, not global ones.

  **The asm lever is now a reusable library, not a break of the model.** The
  pi32v2 assembler syntax was pinned by experiment (the disassembler's "arithmetic"
  form is *not* what the parser accepts — the parser form is in the header): `rep
  <counter> { <body> }` (zero-overhead loop, body size auto-computed, counter is a
  runtime register that is clobbered and wraps on 0); `ins1 # ins2` VLIW dual-issue
  (an A-slot arith op pairs with a B-slot load/store — two ALU ops do not pair);
  `rA_rB += [rC ++= i1]*[rD ++= i2]` 64-bit memory-MAC (two auto-incrementing
  loads, immediate strides, `h[..]` for a 16-bit operand); `r1_r0 = r0 * r0` square.
  These are wrapped in `hal/fm1_dsp_kernels.h` as `static inline` helpers with a
  bit-identical C fallback for host/WASM, so a kernel is a plain C call — the
  composable "one node = one algorithm" model is untouched. First kernels:
  `fm1_kernel_sum_i32` (rep sum) and `fm1_kernel_dot_i32` (rep + memory-MAC dot,
  64-bit accumulate), host-tested for bit-parity.
  The kernels target *vector* inner loops (a sum/dot over N-element arrays). The
  shipped node set is entirely scalar — every `node.c` is a per-sample expression
  with no loop — and the two hot accumulators don't map onto them without breaking
  bit-parity: the voice mix is a *saturating* add (a guard, not a plain wrap-sum),
  and the `route4` dot is 4 terms against `int16_t` 0/1 weights (already unrolled).
  So the kernels are **ready, not yet emitted**: they become the default the moment
  a vector-shaped node ships (`ifft`/additive, a multi-tap filter, the granular
  engine), and a render-time budget regression guard (§12.7.3) proves any future
  kernel emission is a real win. Still open: SIMD `+|+`/`*|*` (syntax known from the
  stock, semantics TBD) and re-measuring against clang.

#### 6.11.4 Design (concrete)

**Velocity routing.** Add `static int32_t voice_velocity[NVOICE]` (velocity 0..127
scaled to q15 by `velocity << 8`), stored in `note_on`. Make `velocity` a
resolvable reserved input exactly like `gate` — a node/macro declares
`ins: { velocity: { rate: "control", default: "voice_velocity[v]" } }`. The
`fm_op` macro then consumes it three ways, each with a depth param:

- `vel_amp` → `level_eff = level · (32768 − vel_amp + vel_amp · velocity) >> 15`
  (unity when velocity is 0 or `vel_amp` is 0).
- `vel_rate` → envelope rate/time scaling (higher velocity = faster attack).
- `vel_fm` → modulator `level` scaling (higher velocity = more FM depth).

**Parts (voice-management rails).** The patch gains a `parts:` concept; the
generator emits part-aware allocation:

- `note_on_ch(note, velocity, channel)` — an *additive* seam function (the frozen
  `note_on(note, velocity)` stays and forwards with channel 0 = omni).
- Each part: an independent timbre (its own parameter set) + `channel` (or omni)
  + `low`/`high` keyzone. A note routes to every part whose channel matches (or
  is omni) *and* whose keyzone contains the note — so one note may fire both
  parts (layering).
- **Shared voice pool**: `voices` is the total; all parts share it and the
  allocator steals across parts (one busy part can use another's idle voices).
- **`parts:` schema is parallel arrays** (not a list of per-part objects):
  `{"count": N, "channel": [...], "low": [...], "high": [...], "level": [...],
  "delay": [...]}`. Chosen so a future firmware can add an `engine: [...]` array
  and point *different parts at different patch engines* (one FM, one additive,
  one subtractive VA) without restructuring — each part is then an independent
  param block for its engine. Out of scope for F3 but the shape reserves the
  seam.
- Per-part `level` is a gain and `delay` is a note-onset offset (the envelope
  attacks `delay` ms after note-on, held silent before).
- Params are **per-part**: the id space is `part × param` (part-major, so a part's
  timbre is one contiguous block — trivial part-patch save/load), and a voice
  reads its part's params through a `voice_part[v]` tag set at note-on.

**SysEx envelope (shared base).**

```
F0 00 21 1D <model> <cmd> <ver> <payload…> <crc16-lo> <crc16-hi> F7
```

- Shared: the manufacturer id `00 21 1D`, the envelope frame, the **CRC-16-CCITT**
  (poly `0x1021`, init `0xFFFF`, no reflect, over `<cmd>…<payload>`, little-endian
  bytes), and five commands every firmware answers — `0x01` *identity request*
  (→ identity response), `0x02` *param dump*, `0x03` *part-patch dump* (with a slot
  byte), `0x04` *multi-patch dump* (with a slot byte), `0x05` *settings dump*;
  responses echo the command with the high bit set. `0x7F` = unknown command.
- Per-firmware: `<model>` (one byte), the payload layout — which params, their
  order, count, and Q-format (the generated `sysex-layout`, emitted alongside
  `params.json`). Multi-byte payload values are **7-bit packed** (7 data bytes →
  8 MIDI bytes with the collected top bits; unpacked before CRC/parse).
- A 4-op patch is **not** DX7-compatible (DX7 is 6-op); DX7 `.SYX` import is
  explicitly out of scope for fourop-fm.

**Preset formats (concrete byte layouts, all little-endian).** Every record is a
self-validating unit — a `u8 version` (`0xFF` = empty slot), a body, and a
**CRC-32** (poly `0xEDB88320`, init `0xFFFFFFFF`, reflected — the platform's
`crc32`) over version+body — so a corrupt record is skipped, never the whole bank.

- **Part patch** (one timbre; `N` = the per-part voice-param count, fourop-fm 74 —
  the node voice params + the six per-part voice-mode params):

  ```
  u8 version | char name[16] | i32 params[N] | u32 crc32
  ```

- **Multi patch** (a composition; `N_PART` parts, fourop-fm 2):

  ```
  u8 version | char name[16] | u8 part_slot[N_PART] | i32 level[N_PART] |
  i32 delay[N_PART] | i32 channel[N_PART] | i32 low[N_PART] | i32 high[N_PART] |
  u32 crc32
  ```

  `part_slot[i]` = the part-patch slot each part uses (`0xFF` = none).
- **Settings** (one global record):

  ```
  u8 version | i32 base_channel | i32 master_tune | u32 crc32
  ```

**Flash layout (on the existing `store.h`).** The 128 single parts are one bank
chunked across three flash slots (51 records per `SLOT_MAX` = 16 372 B slot; a
record never straddles a slot), the 64 multi patches one bank in the slot that
follows (all 64 fit one slot), the settings record in the settings sector —
reusing `slot_load`/`slot_save`/`settings_load`/`settings_save` (magic + length +
crc32 + header-last commit stays the transport integrity). The 40 576 B part bank
does not fit CPU0's 96 KiB `.bss`, so both banks live in `.pool` (app.ld's big-
buffer region): flash is the persistence, RAM is a per-boot working copy. The slot
count is the measured hardware answer: `SLOT_MAX` = 16 372 B, the fourop-fm 317 B
part record fits 51 per slot — 128 spans 3 slots, 64 multi patches fit 1. Per-record
CRC + version on top: a fresh (erased) bank reads all-empty (`0xFF`); a cut save is
caught by the area CRC, a single flipped bit by the record CRC. Writes happen only
when silent (`dsp_quiet`, the existing rule) and only on an explicit save, never on
a knob step.

**MIDI CC map.** The generator emits a `const` `cc -> param id` table from
`params.json` (one CC per param, ascending from a base), plus the reversed
`param id -> cc` for MIDI-learn-less fixed mapping. A multitimbral patch's params
overflow the 7-bit CC space, so the patch declares its surface: the patch-level
`cc:` list names the CC-exposed params (absent = every param). Documented in
`control-map.md`.

**Scope taps (`taps:`).** The patch declares per-op scope/spectro taps — a list
of `<instance>.<port>` audio-rate voice-zone outputs (fourop-fm: `op1..op4.audio`
+ `route.car`, resolved through the macro bindings to each operator's post-mute
output and the per-part voice mix). The generator emits `N_TAP × N_PART` tap
channels (`N_TAP_CH`), one per operator per part plus the per-part mix, accumulated
in `render_voices_block` as the sum over that part's gated voices (part-level
scaled, so a muted part reads silence) into a per-block
`[N_TAP_CH][UMETATE_DSP_BLOCK_FRAMES]` buffer, and a seam getter
`<name>_dsp_tap(ch)` (channel `ch` = `tap × N_PART + part`) returning the last
block's Q15 samples. The scope widget resolves its source dynamically: `channel`
0..3 = "op N of the active part" (`1 + N·n_part + part`), `mix_part` = "part N
mix" (`1 + n_op·n_part + part`, the `route.car` tap) — so the HOME 4-op scope
follows the active part and the 2-part scope shows each part's mix. The tap write
is bounded to one `UMETATE_DSP_BLOCK_FRAMES` window (host tests render larger
`frames`), and the zero/combine live in the block loop (`taps_clear`, split-core
`tap0 += tap1`).

**Polyphony budget tool.** A new `umetate budget --voices N` (and `--parts N`)
that generates the patch at N voices, compiles on host, times a worst-case
`render(256)` (all voices sounding, envelope open), and reports the render time
against the 2.9 ms budget. The device fit is the **emulator leg** (F7e):
`umetate emu --check --mhz 240` boots the built package and holds a chord — the
dogfood run halts never and peaks at full scale, so the fit is measured, not
estimated. The development skill's interview gains a **polyphony budget** step:
the voice count is a measured claim, not an estimate.

**Voice modes (retrigger / mono / unison / legato / portamento).** The voice
manager is a **generator emission** — a reusable `umetate/_voice.py` module, F3's
"rails", which the seam inlines — owning the per-voice state and the
allocation/mode/glide logic; it is parameterized by `NVOICE` at AOT time, so
`dsp.c` stays one standalone file (no separately-compiled runtime). The generator
emits the synth-specific note→increment glue alongside it. Decisions (all
settled):

- **Retrigger is the default** in every mode. A `voice_trig[v]` one-shot flag (set
  on note-on, cleared after the control prologue) resets the envelope; `dx_env`
  gains a `trigger` input (default `voice_trig[v]`) that resets to attack
  *regardless of stage* — this also fixes the current steal bug (a stolen voice
  kept the old note's envelope).
- **Mono**: one sounding note, `note_priority` (last/highest/lowest, default
  last). On note-off, the next-held note (by priority) takes over.
- **Unison**: `unison_count` stacked voices per note, **linear detune spread**
  (±cents around the note).
- **Legato** (mono): overlapping notes don't retrigger the envelope — the pitch
  jumps instantly to the new note. Legato never glides; only `portamento` glides.
- **Portamento**: **constant-rate** (interval-proportional glide time), a
  **linear ramp** `inc += step·sign(target − inc)` — no LUT, one add per voice per
  block (a one-pole would be constant-time/exponential, a different feel).
- **Takeover retrigger** (mono note-off → next held note): retriggers iff `legato`
  is off; `portamento` (glide) is orthogonal and applies whenever it is set.
- All mode params — `mode`, `unison_count`, `unison_detune`, `legato`,
  `portamento`, `note_priority` — are **per-part** in a multitimbral patch (each
  part has its own poly/mono/unison + counts + times) and **per-preset** (global)
  in a single-timbre patch.

Per-voice state (SoA, `.cpu1_bss`): `voice_gate`/`voice_note`/`voice_age`/
`voice_velocity` (existing) + `voice_trig` (uint8 one-shot), `voice_target_inc`
(uint32 glide target), and the unison detune (a q16 ratio, per voice). The emitted
interface is `voice_init`, `voice_note_on(note, velocity, picked[])` (returns the
assigned voice indices), `voice_note_off`, `voice_all_off`, and `voice_glide`
(the per-block ramp).

**Status (F3):** the voice manager is now the generator rails module
`umetate/_voice.py` (per-voice SoA state, the `voice_mono_active` priority helper,
and the `note_on`/`note_off`/`all_notes_off`/`reset` emission). The six mode
params are per-part in a multitimbral patch (in each part's voice block, so a part
patch carries them) and global (appended last) in a single-timbre patch. Landed:

- **`trigger` reserved input** — `voice_trig[v]` (one-shot, set in `note_on`,
  cleared after the control prologue); `dx_env` retriggers on it regardless of
  stage, so a stolen voice re-attacks (F3a).
- **The six mode params** — `mode` (poly/mono/unison), `unison_count`,
  `unison_detune` (cents, linear spread), `legato`, `note_priority`
  (last/highest/lowest), and `portamento` (Q16 glide rate, 0 = off).
- **Mono** — one voice (voice 0), a 128-note held tracker + `note_priority`;
  `note_off` does priority takeover; legato gates the retrigger on overlap.
- **Unison** — `unison_count` stacked voices with a linear ±cents detune folded
  into each voice's base increment.
- **Portamento** — `voice_inc[v]` ramps toward `voice_target_inc[v]` at a constant
  rate (linear in the increment, `step = target × portamento >> 16`, clamped; no
  LUT, one add per voice per block), re-deriving `<name>_note_derived(v)` each
  block. A fresh voice snaps; a steal glides.
- The note→increment glue is `<name>_note_derived(v)`, parameterized by voice index
  and driven by `voice_inc[v]` (note_to_inc × detune) — shared by note-on, mono
  takeover, and the glide ramp.
- **Parts (multitimbral)** — `parts: {count, channel[], low[], high[], level[],
  delay[]}` (parallel arrays); the voice-zone params become `[N_PART]` arrays read
  as `param[voice_part[v]]`, and the id space is `part × param` (part-major,
  contiguous per part). `note_on_ch(note, velocity, channel)` routes a note to every
  matching part (channel + keyzone) — one note may layer several parts — each
  allocating a distinct poly voice from the shared pool (`voice_part[v]` tag).
  `note_on` is the frozen omni forwarder.
- **Per-part `level` + `delay`** — `level` (q15 gain) scales a voice in the mix
  (`bus += voice × part_level[voice_part[v]] >> 15`); `delay` (onset offset, ms) is
  a per-voice `voice_delay[v]` countdown — a delayed voice is allocated but held
  silent (gate off) until it expires, then it attacks (`gate`+`trig`+increment), so
  the envelope attacks `delay` ms after note-on. Allocator treats pending voices as
  taken; `note_off`/panic/reset clear the countdown.
- **Per-part voice modes** — the six mode params are per-part arrays when
  `n_parts > 1`: each part allocates by its own `mode` (poly one-voice / mono with
  a per-part held-note tracker + `part_mono_voice[p]` + legato/priority / unison
  `unison_count` stacked voices), read through `vm_mode[voice_part[v]]` etc. A
  mono part's takeover and a unison part's stack-steal are per-part; the
  `voice_mono_active` helper takes the part index. The single-timbre path is
  unchanged (global scalars, voice 0 mono).

Still open: none — per-part mono/unison landed (F3, this increment).

#### 6.11.5 Milestones (ordered)

| # | Milestone | Acceptance |
| --- | --- | --- |
| F1 | **Interview loop hardening** (L1–L7). | synth-brief semantics column + multi-timbrality + MIDI-spec prompts; control-map menu→page→mode-tree prompt; skill non-goal rule + two-tier example definition; source-vocabulary check runs. |
| F2 | **Velocity routing.** — **done** | `voice_velocity[]` + `velocity` reserved input + `vel_amp`/`vel_fm`/`vel_rate` in `fm_op` (velocity → amplitude, → FM, → envelope rate via a `dx_env` rate-scale input); host tests prove a higher velocity is louder and attacks faster. |
| F3 | **Voice-management rails.** — **done** | `_voice.py` rails + `trigger`/retrigger + mono (note_priority/legato) + unison (detune) + portamento (glide) + the six mode params (per-part in multitimbral patches) + `parts:` (per-part param arrays, `voice_part[v]`, `note_on_ch` channel/keyzone routing, layering, per-part `level`/`delay`, and per-part poly/mono/unison); host tests prove mono/unison/legato/glide/routing+layering+level+delay + per-part mono priority/takeover + poly isolation + unison stacking. |
| F4 | **Presets + settings + SysEx.** — **done** | 128-slot single-part store + 64-slot multi-patch store (chunked across the slot area's measured 16 372 B ceiling; F7d) + settings record (`_records.py`/`presets.c`, byte-parity-tested), the shared SysEx envelope + 7-bit packing (`_sysex.py`), the generated `sysex-layout`, the bank ↔ `.syx` export/import (`_presets.py`), the `umetate preset export/import` CLI, and the C bank save/load over `store.h` (silent-only writes). Host tests prove the export→import round-trip and the C/Python byte parity. The device-side SysEx command handler landed with F7a. |
| F5 | **MIDI CC map.** — **done** | `generate_cc_map` + `generate_cc_header`: one CC per param, ascending from base 16, skipping the reserved CCs (sustain 64, channel-mode 120..127), plus the reversed `param → cc`; a GenError when the params don't fit. Host tests prove the map is complete/unique/ascending and that a CC write through the generated `cc_map.h` table reaches a real, writable param. |
| F6 | **Polyphony budget tool.** — **done** | `umetate budget` generates the patch at each `--voices`/`--parts`, compiles for host, and times a worst-case `render(256)` (all voices sounding, envelopes open) — per-voice cost + linearity; the skill interview consumes it (a measured claim, not an estimate). The device fit is the emulator's job (F7e: `umetate emu --check --mhz 240` boots the built firmware and holds a chord — no halt, full-scale audio). |
| F7 | **fourop-fm firmware assembly** — **done** | `examples/fourop-fm/` builds a firmware: 2 independent-timbre parts, velocity, CC, presets, settings, sustain/panic, `app_main`/`app_audio` glue on the shipped framework. Landed: F7a `synth_sysex` (envelope + five commands + 7-bit packing, byte-parity with `_sysex.py`); F7b `synth_midi` (note routing, CC→param with 7-bit→[min,max] scaling, sustain, panic, bend); F7c `synth_runtime` (a multi patch applies its part-patch refs + routing through set_param) + the generated `synth_layout.h` (model byte, param counts, the routing base) + the patch-level `model` field; F7d `umetate build --synth <dir>` — the composition (rib.c is now the frozen framework: platform + UI kit + the synth services, the demo moved to `rib_app.c`), the generated `dsp.h` seam header + `.dsp_text` SRAM placement, the patch-level `cc:` list (the multitimbral CC surface), 128 single-part + 64 multi-patch preset slots (chunked across the slot area), and the dogfood app glue (`examples/fourop-fm/app.c`): the host leg renders sound on cue and the target leg builds `umetate-fm1-pro-fourop_fm.fwsc` through the JieLi toolchain (82 060 B image, `.dsp_text` 8 796 B in SRAM, checks green); F7e the emulator run — `umetate emu --check --mhz 240` boots the package and holds a chord: **no halt, full-scale audio peak (16 383)** — the device fit is measured, not estimated. |
| F8 | **Docs / tutorial / skill finalization** — **done** | tutorial + README + skill describe the full path; roadmap §6.11/§7/§12 updated; every milestone green. |

Each milestone: mypy + ruff + pyright clean; all test modules green; `_skill` +
`_links` in sync; `lint.c_checks` clean; roadmap updated in the same commit.

---

### 6.12 The composition model (node → macro → patch → firmware)

The toolkit is a **layered compiler**: five authoring levels compose ahead of
time into one fused engine, one panel, and one firmware. Each level has a typed
contract, and the generator combines them without runtime interpretation. The
CLI, RIB rails, agent, tutorial, and docs all follow this model.

| Level | Authoring artifact | Compiles to | Ships in |
| --- | --- | --- | --- |
| 1 · Node | `modules/nodes/<n>/{node.json,node.c}` | an inlined body | `modules/nodes/` |
| 2 · Macro | `modules/macros/<m>/macro.json` | an expanded subgraph | `modules/macros/` |
| 3 · Patch | `patch.json` | `dsp.c` (the `<synth>_dsp_*` seam) | the project |
| 4 · Panel | `panel.json` | `panel.h` (`ui_tables`) | the project |
| 5 · Generator | — (the AOT compiler) | `dsp.c`, `panel.h`, `params.json`, `tables.{c,h}`, `cc-map`, `sysex-layout` | `umetate/` |
| 6 · Firmware | `app.c` (the app glue: `app_audio` + `app_main` + the service contexts) | the device binary (via `umetate build --synth`) | the project + `firmware/` |

**Level 1 — Node** is *one DSP algorithm*. `node.json` declares `ins`/`outs`/
`params`/`state` with Q-formats; `node.c` is the body template with the
`${in.x}`/`${out.x}`/`${param.x}`/`${state.x}` placeholders. Contract: a node
with only `control`/`event` ports is **control-rate** (once per `CONTROL_BLOCK`);
any `audio` port makes it **audio-rate** (per sample). `delay1`/`delayN` carry the
`@@read@@`/`@@write@@` split (the cycle-breakers). Every node has a host parity
test. *Universal rule:* one node = one algorithm; shape/spectrum/envelope = data.

**Level 2 — Macro** is a *reusable subgraph*. `macro.json` declares `ins`/`outs`/
`params` + inner `nodes`/`wires`. Contract: a macro is **expanded** (inlined) into
leaf nodes; `params` map to inner node params *or state* (`ratio → phasor.inc`
via `note_derived`); the graph is a DAG (feedback only via `delay1`). `fm_op` is
the FM-specific macro; the *mechanism* (compose nodes, map params inward) is
universal.

**Level 3 — Patch** is the *complete engine declaration*. `patch.json` declares
`voices`, `params` (the manifest), `tables` (XIP data), `voice`/`global` zones,
`voice_out`, and `parts` (F3, done). Compiles to the frozen `<synth>_dsp_*` seam
(§12.1). The reserved allocator inputs `note`/`gate`/`velocity`/`trigger` are
bindings, not edges; `velocity` is a per-voice control (F2), `trigger` a note-on
edge (F3).

**Level 4 — Panel** is the *UI declaration*. `panel.json` declares contexts /
pages / widgets / bindings + `operators` / `mute`. Compiles to `panel.h`
(`ui_tables`). Sources are validated against the board's `BTN_*`/`ENC_*` enums
(L1); params resolve against the patch's `param_ids`.

**Level 5 — Generator** is the *deterministic AOT compiler*. Emits the fused
monomorphic `dsp.c` (no per-sample dispatch), `panel.h`, `params.json` (manifest +
metadata), `tables.{c,h}`, the voice-management rails (`_voice.py`: allocator +
modes + `parts:`, F3), the `velocity` routing (F2), the `cc → param` map + the
`<synth>_dsp.h` seam header (F5/F7d), and the `synth_layout.h` constants (F7c).
One patch + one panel → byte-identical output every time.

**Level 6 — Firmware** is the *frozen framework + the synth's app glue*.
`firmware/src/rib.c` ships the platform (boot, USB/MIDI, panel, display, storage,
recovery, the UI kit) and the **synth services** — `synth_midi` (notes / CC /
sustain / panic / bend; a CC value scales to the param's [min, max], the CC
surface is the patch's `cc:` list), `synth_sysex` (the envelope + the five
commands), `synth_runtime` (a multi-patch applies its parts through `set_param`),
over `presets.c` (the 128+64-slot record store, chunked across the measured slot area).
The *per-voice* allocator (assignment, mono/unison/legato/portamento/retrigger/
glide, `parts:`) is **generator rails** (`umetate/_voice.py`, F3) — not
hand-written C. A synth project supplies only the **app glue** (`app.c`:
`app_audio` + `app_main` + `app_idle` + the `ui_act_*` hooks + the three service
contexts), and `umetate build --synth <dir>` composes framework + generated code
+ glue into the firmware (F7, done).

**The multitimbral patch** (F3). `parts: N` declares N independent timbres. Each
part is its own parameter set (the id space is `part × param`) plus routing
(`channel`, `low`/`high` keyzone) and gain/timing (`level`, `delay`). A voice is
tagged `voice_part[v]` at note-on and reads its part's params. `note_on_ch(note,
velocity, channel)` routes a note to every part whose channel matches (or is
omni) *and* whose keyzone contains it — one note may fire many parts (layering).

**The persistence model** (F4). Three records: **single parts** (one timbre,
128 slots), **multi-patches** (which single part each part uses + routing + gain/
timing, 64 slots), and **system settings** (base channel, tune — one global
record). This mirrors the classic patch / performance / system split. The slot
count is the *measured* hardware answer: the slot area holds 16 372 B (store.h
`SLOT_MAX`), the fourop-fm 317 B part record fits 51 per slot — 128 single parts
span 3 slots, 64 multi patches fit 1.

**The gaps** (what's still hand-written or missing): the docs/tutorial/skill
finalization (F8); the **dev-skill GUI interview revamp** (L10 — raise its minimum
spec depth to the fourop-fm restructure spec); device acceptance, flash, debrick,
the FPU probe, and the clock soak stay blocked until hardware arrives.

**Universal vs fourop-fm-specific.** Of the four-op-FM work, the *universal*
tooling is: `gain`/`cmul`/`csum` (the control/audio-separated gain family),
`mute`, `pitch_env`, the separation invariant + its generic test, the `velocity`
reserved input, the `trigger` reserved input, the `parts:` multitimbral model, the
two-tier preset model, the shared SysEx envelope, the generator CC map (with the
patch-level `cc:` surface for multitimbral patches), the per-op scope `taps:`
surface (patch-declared audio tap points → per-part channels, §6.11.4), the
polyphony budget tool,
the source-vocabulary check, the firmware framework (`rib.c` + `synth_midi` /
`synth_sysex` / `synth_runtime` + `presets.c`), and the `build --synth`
composition. The *fourop-fm-specific* bits are `algo`/`route`/`route4`, the
`fm_op` macro, the 12-waveform `osc` union, the 8-algorithm `routing` table, the
DX `dx_env`, and `examples/fourop-fm/app.c` — each an instance of a universal
mechanism (the selector, the router, the operator, the wave reader, the matrix,
the rate/level envelope, the app glue).

**Two halves of one architecture.** The composition model above is the
*structure*; the **workflow loop** is the *process* that produces it — orient →
design interview (synth + GUI) → implementation plan → consistency gate → author
(mechanical translation) → verify → recovery/handoff (the development skill,
`SKILL.md` §0–8). They stay reconciled through two invariants: the **seam**
(`<synth>_dsp_*` + `panel.h` + `params.json`, emitted by the generator or
hand-written as an escape hatch) and the **rails** (`_voice.py`, the reserved
inputs, the mode params). A decision that changes one level is reflected in the
model *and* the loop — never only in the code.

### 6.13 The development loop (granularity)

Umetate development and synth projects both follow a fine-grained loop: **one
decision-set per increment**, the smallest coherent, verifiable change. The work
runs through two nested loops.

- **Design loop** — decide before code: write the decision into its canonical
  artifact (the roadmap for umetate itself; the brief / control-map / plan for a
  synth), make it mutually consistent, confirm it with the user. No code until
  the decision is confirmed.
- **Implementation loop** — translate in small increments; after each, run the
  full gate (`umetate deep-check --all`: mypy + ruff + pyright; the Python test
  modules; the firmware host route; `_skill`/`_links`/`lint --c`) and **commit
  with the canonical artifact updated in the same commit** (the roadmap is the
  single source of truth — never out of sync with the code).

Rules: never batch unrelated decisions into one increment; never implement before
the design is confirmed; never weaken a test to make a build pass; a lower
evidence layer never proves a higher one. This is how F2/F3 and F7 were built —
F3a `trigger` → F3b rails/modes → glide → F3c `parts:` → level/delay, and F7a
SysEx handler → F7b MIDI → F7c runtime → F7d composition → F7e emulator run —
each a separately tested and committed slice.

---

## 7. Implementation roadmap (ordered)

Each task lists its goal, actions, and acceptance/evidence (per §5.5). A task is
"done" only when its acceptance is met and the claim ledger in `docs/roadmap.md`
is updated in the same commit.

> The **fourop-fm firmware program** (finishing the example into a full firmware +
> the toolkit strengthening it forces) ran on top of the P-phases below and is
> **done** — milestones F1–F8 in §6.11.

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

### Phase 2 — RIB runtime + generator (P2) — **done (host + target), blocked (device)**

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

**P2-2 — Dual-core bring-up (default).** — **done (source/host/target), blocked (device)**
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
device probe needs hardware. **Layer: source/host/target.**

**P2-3 — Hardware acceleration HAL.** — **done (source/host/target), blocked (device)**
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
(`vector_*`) are **deferred** (blocked on device parity). *Blocked:* the hw FFT/vector DSP + hw-vs-sw parity
(the target link now works; the device acceptance is `blocked`). **Layer: source/host/target.**

**P2-4 — FPU opt-in (`--dsp float`).** — **blocked** (the flag is accepted but the
float DSP TU is unwired; the DSP is integer-only) — DSP-TU-only FPU; no `double`;
prove context ownership. *Acceptance:* no soft-float helpers in DSP; no FP outside
the DSP object; host integer-vs-float parity; device `blocked`. **Layer: source/host/target.**

**P2-5 — Clock profiles (240/320).** — **done (CLI), blocked (device)** — the CLI
rejects 360/396 (`--clock 240|320`); the app reports the bootloader's clock and never
sets it. *Acceptance:*
`status`/screen reports measured clock + revision; 360/396 rejected at the CLI.
Device soak `blocked`. **Layer: source/target.**

**P2-6 — SMK-37 board layer.** — **done (builds), blocked (device)** — Velocity keybed,
16 RGB pads, 4 faders, 8 encoders,
wheels, outer keys, per-model identities, SMK flash map + owner tag; FM-1
byte-identical (`BOARD_SMK37`). *Acceptance:* all three SMK models build; FM-1
byte-identical; flash-map test covers every object. **Layer: source/host/target.**

**P2-7 — Recovery & safety in firmware.** — **done (host), blocked (device)** —
App-level rescue, boot guard, running
chord, custom loader (`ota-<identity>` + resume + model check), single-bank-OTA
`uboot.boot`, protected-range guards, `SEC-1`/`SEC-2` fixes. *Acceptance:* host
`bootguard` test; `lint --c` encodes SEC-1/SEC-2 + flash allow-list. Device `blocked`.
**Layer: source/host.**

**P2-8 — Patch generator (the AOT compiler).** — **done (host + WASM + target)**
— A compiler pipeline (the §12.4 spec): `_ir.py` (Port/Edge/PortSpec NamedTuples,
`NodeSpec`, `NodeInstance`, `CompiledGraph`, `GenError`), `_frontend.py` (parse →
macro expand → wire resolve → type-check → cycle-check + topo), `_backend.py` (rate
split → state alloc → allocator → emission), and `generate.py` (the thin pure entry).
The node library lives in `modules/nodes/<node>/node.json + node.c` and the macro
library in `modules/macros/<name>/macro.json` (§12.5): a manifest +
a per-sample C template with `${in.*}`/`${out.*}`/`${state.*}`/`${param.*}`
placeholders (zone-agnostic auto-wrap) and `@@read@@`/`@@write@@` cycle breakers;
a leftover placeholder is a `GenError`. It type-checks wires (rejects `audio→event`
+ Q-format mismatches), cycle-checks with `delay1`/`delayN` removed as breakers, and
emits the **rate split** (control prologue every `CONTROL_BLOCK`=32, audio loop per
sample) + the §12.1 seam + the note→inc allocator (`ratio` via a note-derived state
binding). *Verified:* the pocket-drone two-op FM example (op macro + delay1 feedback
+ global chain) compiles; a delay-free env/vca patch renders non-silent then silent;
an `audio→event` edge is rejected; `mypy --strict` + `ruff check` + `ruff format
--check` are clean over the owned Python. *Followed up:* the flattened `params.json`
table + `const` XIP `tables:` landed in P3-3, the WASM build in P4-1, the target build
in P3-2 (the `model`-enum dispatch idea was superseded by the monomorphic inlining —
no dispatch at all). **Layer: host/WASM/target.**

**P2-9 — UI base + panel generator.** — **done (host + target), blocked (device)**
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

**Exit P2:** **met (host + target)** — RIB is the dual-core, integer-by-default runtime
for FM-1 + SMK-37; the generator compiles patches to the invariant `<synth>_dsp_*`
seam and panels to the shipped UI kit. Every device gate is explicitly
`blocked`/`not-run`.

### Phase 3 — CLI (P3) — **done (host/browser/target), blocked (device)**

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
(`lib list` — the shipped nodes + macros + templates, local only), `lint.py` (`lint --c` — the
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

**P3-4 — `flash`, `debrick` (direct, gated).** — **done (host), blocked (device)** —
`flash.py` wraps the inherited `fm1_install.py` (strangler-fig, not a rewrite): the
§8 `--device` gate, package identity/CRC verification before any MIDI, the named
recovery routes, then the installer (wrong-model exits 6). `debrick.py` names the
recovery routes + prerequisites; `mask-rom` is **blocked** (USB_KEY dongle pending a
USB solder; FM-1 ~10 days). *Verified:* `flash` refuses without `--device`; a damaged
package exits 2; a wrong-model fake device exits 6 (the inherited `install_test.py`
`backend` seam); `debrick` lists the routes; `mypy --strict` + `ruff` + `test_cli`
green. Real-device acceptance is `blocked`. **Layer: host.**

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

### Phase 4 — Web lab + emulator (P4) — **done**

**P4-1 — WASM parity lab.** — **done (browser)** — the P3-5 harness grew an
**AudioWorklet** (`worklet.js`: wasm instance, 128→256 block conversion, Q15→float) +
a **versioned message protocol** (`{v: 1, op: …}`, rejected unless v1) + a
**gesture-gated start** (`main.js`/`index.html`), and `deep-check --web` now proves
**host == wasm parity**: the same generated `dsp.c` compiled by gcc (host) and emcc
(wasm, run via node — the browser's WebAssembly semantics) render an identical script
and the 512 `int32` samples match **exactly**. *Verified:* `deep-check --web parity: ok
(host == wasm, exact)`; `test_web` (standalone wasm + the exact parity) green; `mypy
--strict` + `ruff` clean. (Also fixed the latent `--out` path bug in `_emcc_args`.)
**Layer: browser.**

**P4-2 — fm1-emu as model layer.** — **done (emulator)** — `umetate setup` (no flags)
now installs Rust (rustup) and builds fm1-emu at the pinned commit — the `fm1-emu`
batch interpreter *and* the `fm1-live` GUI. `umetate emu` runs the GUI (`--fwsc`,
`--persist`, `--midi`, `--mhz`) or `--check` (headless `fm1-live --shot` → panel +
audio peak). *Verified:* `umetate emu --check` boots `umetate-fm1-pro.fwsc` (audio peak
10378, chord LEDs lit, no halt) and `umetate-smk37-pro.fwsc` (SMK-37 pads rendered,
audio peak 6720, no halt); `quick-check` reports the `emulator` layer as `pass`. RIB
runs unchanged in the emulator. No device-acceptance claim. **Layer: emulator.**

### Phase 5 — Skills (P5) — **done**

**P5-1 — umetate-development skill.** **done** — `SKILL.md` (a **design-first**
workflow: orient → design interview (voice architecture + parameter manifest +
tables) → GUI interview (context stack + pages + bindings + control flow) →
implementation plan → a **consistency gate** cross-checking the three artifacts →
then mechanical authoring of nodes/macros/patches via `scaffold` → first slice →
shared DSP → panel → MIDI/persistence → verify → recovery/handoff) + generated
offline `references/` (AC79 facts, flash maps, recovery taxonomy, evidence
vocabulary, code conventions from `firmware/README.md`, and the node/macro/patch
schemas). The 5 synth-project templates (`synth-brief`/`project-plan`/
`feature-contract`/`supported-load-profile`/`evidence-matrix`) + `control-map.md`
now live in `templates/` and are referenced by repo path (not copied into the
bundle). *Acceptance:* `deep-check --skill` passes; it drives `scaffold`/patch
authoring and refuses device writes without §8 gates. **Layer: docs.**
*Follow-up (open, L10):* the GUI interview's **minimum bar** is now pinned at
§6.11.2 — the 10-item checklist (button map, page map, header, param placement,
per-param display + stepping, widget layout, preset browser, exact INIT
PATCH/PART defaults, screen rules); the `SKILL.md` GUI-interview step and the
`templates/control-map.md` prompt must be rewritten to require it before authoring
any panel.

**P5-2 — umetate-safety skill.** **done** — `SKILL.md` (the threat model + surface
map, memory-safety + attack-surface workflow, package identity, the §8 device-write
gate, reporting) + generated offline `references/` (recovery taxonomy + code
conventions). *Acceptance:* `deep-check --skill` passes; maps every surface to
code/test/gate; preserves "not security-clean while SEC-1 device validation is
blocked." **Layer: docs.**

**Exit P5:** **met** — both skills are offline-bundled; `references/` are generated
copies of the canonical docs (drift is a hard failure); `deep-check --skill` proves
them in sync. No device-layer claim.

### Phase 6 — Tutorial + start guide final (P6) — **done**

**P6-1 — Tutorial.** **done** — `docs/tutorial.md` is now the full 13-stage learner
path: stages 1–9 (no hardware) give real commands + flags, the dual-core/FPU/clock
facts, the framework authoring flow (`scaffold` → `patch.json`/`panel.json` →
`<synth>_dsp_*`), and the evidence levels; stages 10–13 are concise + `blocked`/
device-only (install gates, the recovery taxonomy → `platform-facts.md` §4). The
`links` check (`_links.py`) verifies the canonical docs' Markdown links resolve
(file paths, `#anchor`/URLs skipped); `deep-check --links` is wired. *Acceptance:* a
reader follows the no-hardware path to a target package; device steps `blocked`;
`deep-check --links` passes. **Layer: docs.**

**P6-2 — Start guide.** **done** — `README.md` finalized (repo map corrected to
`build/web/`); a new reader names the toolkit, the firmware component, and the
first command. **Layer: docs.**

**Exit P6:** **met** — a reader can reach a target package without hardware, with
device steps clearly `blocked`; the docs' cross-references are machine-checked.

### Phase 7 — Release & provenance (P7) — **done**

**P7-1 — Baseline tag + provenance.** **done** — `provenance/` (`README.md` naming +
required fields, `baseline-2026-10-27.md`) records the commit/tag, the four package
identities + SHA-256 hashes, the toolchain/SDK/emscripten/fm1-emu pins, and the
per-claim status. Verified by a **clean clone** → `deep-check --all` → four target
builds (all `pass`). The verification surfaced and fixed two latent target-build
defects (`.dsp_text` check relative-vs-absolute; math helpers not inlined → XIP
calls). No "security-clean"/"device-accepted" wording while blocked. **Layer: release.**

**P7-2 — Publish only on request.** **done** — nothing pushed/published; `origin`
exists but is not written to. **Layer: release.**

**Exit P7:** **met** — `umetate-baseline-2026-10-27` tagged on a clean tree; a clean
clone reproduces the checks + four packages; nothing is published.

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

This blueprint specifies files, structs, functions, data flow, and memory for
each subsystem so an implementer does not have to make design decisions. Read it
with §7 for the implementation order. Sections: 12.1 the invariant seam; 12.2 the
memory and emission contract; 12.3 the RIB runtime; 12.4 the generator; 12.5 the
node library; 12.6 the UI kit; 12.7 CLI/build/tests; 12.8 the CLI codebase.

### 12.1 The invariant seam — the `<synth>_dsp_*` contract

**Role.** The single interface every synth engine implements — generated from a
patch or hand-written — that the runtime calls. It is where the framework (the
generator) meets the hardware layer (`app_audio`).

**Interface (frozen).**

```c
void     <synth>_dsp_init(uint32_t rate);                      /* once at boot */
void     <synth>_dsp_render(int32_t *out, uint32_t frames);    /* fill out = L R L R…, Q15 ±32767 */
void     <synth>_dsp_note_on(uint32_t note, uint32_t velocity);/* note = MIDI number, vel 1..127 */
void     <synth>_dsp_note_on_ch(uint32_t note, uint32_t velocity, uint32_t channel);
                                                               /* parts: 0xFFFFFFFF = omni; additive
                                                                  to note_on (F3). note_on forwards
                                                                  to note_on_ch(…, omni). */
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

**Future: asynchronous ping-pong.** To drop the ISR wait, core 1 renders
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
the build fails on overage, never silently.** Reconciled at F7d (when the generator
first emitted `.cpu1_bss`/`.dsp_text`), before the first target package — e.g. trim
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
- **Deferred (future):** the §12.1 ping-pong `dsp_blocks[2][512]` + `ready`/`done`
  handshake (asynchronous, no ISR wait).

**Key structs (grounded in the imported code).** `fm1_in` (input matrix,
`hal/fm1_input.h`: notes/buttons/edges/encoders/LED layers, debounced, 10 kHz
tick); `dsp_cmd`/`dsp_status` (§12.1); `store` (`store.h`: settings/blobs/slots,
magic + CRC); the flash map (`fm1_flash_map.h` allow-list + `_Static_assert`s).

**Boot/init sequence.** `crt0.S → platform_init (clock, SFC, RAM) →
fm1_input_init → (dual-core: release CPU1 + probe) → app_init (engine_init) →
app_main` loop.

**Memory reconciliation (closes the §12.2 budget).** Reconciled at F7d, when the
generator first emitted `.cpu1_bss`/`.dsp_text` — e.g. trim `.pool` (delay lines are
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
modules/nodes/<node>/   # node.json (manifest) + node.c (per-sample body template)
modules/macros/<name>/  # macro.json (a reusable subgraph)
```

**Inputs.** node manifests (`node.schema.json`, from `modules/nodes/` + user nodes); the
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
    note_derived: dict[str, str]                       # field -> ratio param name (q16, note_on·r)
    note_cutoff: dict[str, str]                        # field -> ratio (2·sin(π·inc·r/2^32))
    reciprocals: dict[str, str]                        # field -> source (2^32/src at note-on)
    body: str                                          # the node.c per-sample template

@dataclass
class NodeInstance:
    id: str; type: str; zone: str                      # zone: "voice" | "global"
    spec: NodeSpec; params: dict[str, str]
    in_expr: dict[str, str]                            # input port -> C expr (resolved)
    note_derived: dict[str, str]                       # state -> ratio param name (q16, note-on)

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
   `note` (a MIDI note → `inc = (note_to_inc(note) · ratio) >> 16`, the q16 `ratio`
   a runtime param stored in each phasor's `inc` state), `gate` (event → the `env`
   nodes), `velocity` (control → the `vca` levels) — drive the allocator. These are
   **bindings, not graph edges** (the note→inc uses a table at note-on). Emit
   `note_on`: pick a free/stealable voice, set each phasor's `inc`, set `velocity`,
   trigger `gate`. Emit `note_off` (clear `gate`), `all_notes_off`, `quiet`, `lit`,
   `set_bend_q16` (the shared slot), and the `set_param`/`get_param` shared-array
   accessors.

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
reserved allocator inputs `gate`/`note`/`velocity`/`trigger` are **bindings, not
wires**; a
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
  /* modules/nodes/osc/node.c */
  ${out.audio} = fm1_sin(${in.phase});
  ```
  ```c
  /* modules/nodes/delay1/node.c */
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

The node library is generated from the manifests into
[`docs/module-library.md`](module-library.md) — one row per node (summary + ports +
params + state), with `deep-check --lib` failing on any drift. The `ifft`
additive/IFFT spectral oscillator is **planned**, not shipped (see the build
order; `add` is the `mix` synonym).

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
typedef struct { uint8_t kind;      /* BIND_PARAM | BIND_ACTION | BIND_PAGE_SLOT */
                 uint16_t source;   /* control/MIDI id: BTN_*, ENC_*, KEY, pad, fader, wheel, cc, note */
                 uint16_t target;   /* param id (BIND_PARAM) */
                 uint8_t action;    /* verb (BIND_ACTION) */
                 uint8_t arg;       /* action arg (context/page id), or the slot (BIND_PAGE_SLOT) */
                 uint8_t behavior;  /* absolute/relative/momentary/latch/toggle */
                 uint8_t curve; } ui_binding;

typedef struct { const ui_page *pages; uint8_t n_pages;
                 const ui_binding *bindings; uint8_t n_bindings;
                 void (*on_enter)(void); void (*on_exit)(void); } ui_context;

static uint8_t ui_stack[UI_MAX_DEPTH], ui_sp;   /* context stack; top = active */
static uint8_t ui_selected_op;                  /* 0..3, for op_next/op_prev/op_mute */
static const ui_binding ui_global[];            /* always-on, resolved last */

typedef struct { uint8_t type, row, col, span;  /* LABEL/VALUE/BAR/PARAM_ROW/
                                                   PARAM_COLUMN/LIST/GRID/OP_ROW/
                                                   ENVELOPE/STATUS/CUSTOM */
                 uint16_t param; const char *text, *unit;
                 int32_t last; } ui_widget;     /* OP_ROW `param` = an op-param slot;
                                                   STATUS `param` = the algorithm param id;
                                                   ENVELOPE `param` is unused */
typedef struct { const ui_widget *w; uint8_t n; const char *title; } ui_page;
```

**The per-param display scale** (the fix for "the ranges are shown as the raw
integer"): a patch `params:` entry may declare a `display` form, and the generator
emits a `ui_param_disp[n_params]` table (per param id) that the runtime uses to
both **format** and **step** the value. Forms: `raw` (the integer), `ratio` (a Q16
frequency multiplier → `"1.00"`, `65536` = base pitch), `pct` (0..100% of
`[min,max]`), `pct_inv` (100..0%, e.g. damping shown as resonance), `onoff`
(`off`/`on`), `off_pct` (`≤0` → `off`, else %), `hz` (a Q32 rate → `N.N Hz`), and
`semi` (a bipolar Q15 → `±N.NN st`). A relative encoder steps per the curve: a
`linear` param moves by `(max-min)/128` a detent, a `log` param moves
multiplicatively (`v·(1 ± 1/32)`), both clamped to `[min,max]` — so a knob
reaches the whole range in a sane number of turns and never runs off the end. This
replaces the earlier "relative = raw ±1" (which made a 0..65535 param take
thousands of detents).

**Navigation + rendering corrections** (the first hands-on pass exposed these):
page-slot resolution counts only the five param-bearing widget types, so the
`status` readout (which carries `param: algorithm`) is *not* slot 0; `EDIT`/`FX`/
`GLO` are **siblings** — a `switch` action replaces the current mode instead of
stacking, so `FX → EDIT` needs no `HOME` in between; `op_next`/`op_prev` wrap; a
`page` action steps pages bidirectionally and wraps (so the last sub-page is not a
dead end); a page/context change clears the whole screen first (a retained-mode
redraw otherwise leaves the previous page's stale pixels); a param row draws the
label dim and the value bright, right-aligned.

**Two binding extensions** (added for the fourop-fm operator editor): `BIND_PAGE_SLOT`
maps a source to *the Nth param-bearing widget on the current page* (so the rightmost
four encoders follow the sub-page), and an operator group — `op_next`/`op_prev`
cycle `ui_selected_op` (0..3), `op_mute` toggles the selected operator's mute param
(the panel's top-level `mute: [opN_mute, …]` → a `MUTE_TBL`). An `OP_ROW` widget's
`param` is an index into an `OP_PARAM[n_op × n_op_param]` table, resolved through
`ui_selected_op` — so the operator-relative pages show the *selected* operator's
params (`operators: [op1..op4]`, a widget param `opN.<rest>` is operator-relative).
An `envelope` widget declares its 7 params explicitly (`params: [r1..r4, l1..l3]`),
resolved to an `ENV_PARAM[n_op × 7]` table read at `ui_selected_op * 7 + i`; a
`status` widget reads the algorithm param + `ui_selected_op` + the mute table and
renders `ALG <n> · OP <n>/4 · MUTE`.

**Recommended interaction pattern** (the fourop-fm FM-1 exercise): the **page-slot
model** — `BIND_PAGE_SLOT` maps a fixed row of encoders (`KNOB1–4`) to the current
page's params, so a few knobs reach every parameter with the labels shown on screen
(the screen says what the knobs do). Dedicated knobs stay dedicated (`ALGORITHM`,
`PRESETS`); the smooth `MASTER` pot is platform volume, never a slot. The keybed is
a menu surface (keys as operator/mute shortcuts). This keeps navigation ≤ 2 contexts
deep on a 240×240 screen.

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
| `build.py` | `build` | generate + target compile + packager → `.fwsc` (Docker); `blocked` without the toolchain; `--board/--model/--dsp/--clock/--profile`; **`--synth <dir>`** composes a synth project (patch.json + panel.json + app.c) — generate into `firmware/gen/`, host-build + run the project's script (WAV + screens), then the target package `umetate-<board>-<model>-<synth>.fwsc` |
| `emu.py` | `emu` | run your firmware in fm1-emu: the GUI (`fm1-live --fwsc`, `--persist`, `--midi`) or headless (`--check --mhz` → the shot + audio peak); the default package is the newest composed synth package, else the demo; `_emu.py` holds the shared paths |
| `generate.py` | (internal) | patch + panel → `dsp.c` + `panel.h` (UI tables); `params.json` + `tables.c` are P3-3 |
| `deep_check.py` | `deep-check` | host/web/safety/python/links/skill/pyright checks; `--all` is the complete gate |
| `inspect.py` | `inspect` | read a `.fwsc` (identity/CRC/model/damage) without a device |
| `flash.py`/`debrick.py` | `flash`/`debrick` | `flash` writes a `.fwsc` (§8 gates, wrong-model exits 6); `debrick` names the recovery routes (mask-rom blocked) |
| `scaffold.py` | `scaffold node\|macro\|patch` | generate a skeleton; `--template` copies a shipped template |
| `lib.py` | `lib list` | list the shipped nodes + templates (local only) |
| `lint.py` / `fmt.py` | `lint --c` / `fmt` | the custom safety checks / clang-format |
| `web.py` | `web-build` / `web-serve` | emscripten → `dsp.wasm` + a minimal harness / loopback serve |
| `status.py` / `evidence.py` | `status` / `evidence` | parse the roadmap's per-layer claim ledger / validate an evidence matrix |
| `version.py` | `version` | print the installed `__version__` (authority: `pyproject.toml`) |

#### 12.7.2 The build pipeline (one generated `dsp.c`, three targets)

```text
patch.json + panel.json + node manifests        (+ the project's app.c)
        │  generate.py  (host, pure Python)
        ▼
dsp.c (engine) + dsp.h (seam) + panel.h (UI tables)   (+ params.json + tables.{c,h}
        │                                      + cc_map.h + synth_layout.h, F4–F7)
        │
        ├──▶ host   → `build --synth` host leg / `deep-check --host`  (gcc/clang + harness → WAV + screens)
        ├──▶ WASM   → `web-build`          (emscripten + js adapter   →  dsp.wasm, no import section)
        └──▶ target → `build` / `build --synth` (JieLi clang + the rib.c framework + app.c →  .fwsc)
```

The three branches are **separate commands**: `build` (and `build --synth`) owns the
target branch (blocked without the toolchain), `deep-check --host` is the
no-toolchain iteration loop, `web-build` the WASM lab. The synth composition adds
the framework half: `rib.c` includes the platform + the synth services + the
project's `app.c` (the dogfood packages as `umetate-fm1-pro-fourop_fm.fwsc`).

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
- **safety regressions (UB/OOB/voice-alloc):** the generated fourop-fm DSP is built
  with `-fsanitize=address,undefined -fno-sanitize-recover=all` and run under
  worst-case load (128 held notes → repeated voice steals across the 20-voice pool),
  so an OOB read/write, signed overflow, shift, or divide-by-zero fails the gate;
  the polyphony ceiling + steal policy (a 5th note steals the oldest of 4, the pool
  never grows past NVOICE) is asserted through `dsp_lit`. Both live in
  `umetate/test_generate.py`.
- **performance regression guard:** compile the generated `dsp.c` and time a fixed
  render on host; fail over a per-patch threshold. The emulator ISR% (`emu --check
  --mhz 320`) is the higher-fidelity gate when the toolchain is present. Implemented
  as `umetate/test_perf.py` (the fourop-fm dogfood, 20 voices, min-of-3, ~2.8x the
  ~140 us baseline), wired into `deep-check --python`/`--all`.
- **evidence matrix:** per §5.5, each layer recorded, `blocked`/`not-run` not passes.

#### 12.7.4 The schematic engine

`scaffold node|macro|patch --name` generates a default from the templates/schemas
(the user fills the process body / wires), or `--template` copies a shipped template;
`lib list` shows the shipped nodes + templates (local only). Everything is also
doable by hand against the schemas (the Angular escape hatch).

#### 12.7.5 Schema close-out (the worked-example gaps)

Add to `patch.schema.json`: (a) the `voice` zone's reserved allocator inputs
`gate`/`note`/`velocity`/`trigger` (bindings, not wires); (b) a named `voice_out` (the
voice-zone signal summed into the global bus); (c) macro params may target node
**state** (applied at note-on) as well as ports. Add `q12` to `node.schema.json`
state kinds. All at P0-1. See `examples/pocket-drone/README.md` §5.

### 12.8 The CLI codebase

**Three layers**, each a separate import surface, no import side effects:

1. **Dispatch** — `cli.py`: `argparse` subparsers, `help CMD`, maps a command to its
   module's `main(argv) -> int` and the return to an exit code.
2. **Commands** — one module per command, each `main(argv: list[str]) -> int`.
3. **Services** — `evidence.py` (the Status/Layer vocabulary), `runner.py` (container
   exec), `generate.py` (the pure generator), the internal `_ir`/`_frontend`/
   `_backend`/`_tables`/`_panel`/`_installer`/`_emu`/`_skill`/`_links` helpers, and
   the checks (`lint.c_checks`, `_skill.check`, `_links.check`, `web.check_parity`)
   — inline in their command modules, no separate `_checks/` package.

**Package layout.**

```text
umetate/
  __init__.py   cli.py                    # dispatch, help, exit mapping
  evidence.py   version.py                # Status/Layer Enum; the __version__ authority
  runner.py     generate.py               # container exec; the patch generator (pure)
  _ir.py        _frontend.py  _backend.py # generator internals (§12.4): IR, passes, emission
  _tables.py    _panel.py                 # the table/panel generators
  _installer.py _emu.py                   # the fm1_install loader; the fm1-emu paths
  _skill.py                               # the skill references/ generator + drift check (P5)
  _links.py                               # the docs' cross-reference check (P6)
  quick_check.py setup.py build.py deep_check.py inspect.py
  flash.py debrick.py                       # device writes (host-side, §8)
  scaffold.py lib.py                        # the schematic engine
  lint.py fmt.py web.py status.py emu.py    # lint.py holds the C standing checks
  test_cli.py  test_generate.py test_panel.py test_web.py
modules/nodes/<node>/node.json + node.c      # the node library (§12.5)
modules/macros/<name>/macro.json             # the macro library (§6.9)
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
```

Build/check options are `argparse` flags on their command modules (`build.py`
`--board/--model/--dsp/--clock/--profile`); there is no separate `config.py`
dataclass layer.

**`quick-check` vs `deep-check`.** `quick-check` is a fast, read-only presence/version
probe (per §5.5 layer): `source` = git repo + clean tree + `mypy --strict`/`ruff` +
schemas; `host` = container up + `cc`/`cmake`/`ninja`/`python3`/`node`/`emcc` resolve;
`browser` = emscripten present; `target` = `/opt/jieli` toolchain version + SDK asset
hashes vs `env.lock`; `emulator` = fm1-emu present; `timing`/`device` = a host USB
probe + the device identity; `release` = tag + package hashes. `deep-check` is the
deep one (runs the host tests + the checks). `--json` emits
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

**The runner (the platform abstraction).** The target build, host DSP tests,
WASM build, and clang tooling all run in the pinned POSIX container:

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
| `quick-check` | `runner.probe()` + a host USB probe → a per-layer report (read-only) |
| `flash` | host-side **MIDI SysEx** (mido + python-rtmidi, §8 gates) — not the runner |
| `debrick` | USB_KEY dongle → mask-ROM UBOOT → `jl-uboot-tool` (delegated), §8 gates |
| `scaffold`/`lib` | pure Python over templates/schemas — no runner |
| `deep-check` | `runner.run` (host tests) + the checks (lint/wasm/skill) |
| `lint`/`fmt` | clang-tidy/clang-format via the runner + `lint.c_checks` |

**The checks (inline in the command modules).** `deep-check` runs the checks for the
requested layers; each reports per the §5.5 vocabulary:

- `lint` (source) — `lint.c_checks`: the C standing checks: SEC-1 MAXP bounds,
  SEC-2 UAC access, ROM-address constants, HAL-only MMIO, the flash-busy call
  graph, no `double`/64-bit-div/allocation in the DSP TU (`.clang-tidy` + the
  custom checks).
- `budget` (target) — run by `build` (the firmware link report): `.dsp_text`/
  `.pool`/`.cpu1_bss` fit the §12.2 flash/RAM map; fails on overage (never silent).
- `wasm` (browser) — `web.check_parity`: `dsp.wasm` is standalone (no import
  section) + the host↔browser parity: the gcc (host) and wasm (node) renders match
  exactly (`deep-check --web`).
- `skill` (source) — `_skill.check`: the two offline skills (development, safety)
  each have `SKILL.md` + generated `references/` in sync with the canonical docs
  (byte-for-byte; drift is a hard failure).
- `links` (source) — `_links.check`: the docs' cross-references resolve (no dead
  Markdown links; file paths, `#anchor`/URLs skipped).
- `pyright` (source) — the strict Python type-check (`[tool.pyright]`, §6.8):
  `Any` is banned and the "partially unknown" diagnostics (e.g. an `argparse`
  attribute in a `list[str]`) are errors; run alongside `mypy --strict` + `ruff`.
- `python` (source) — the owned Python layer, one deterministic pass: `ruff
  check` + `ruff format --check`, `mypy --strict`, and the four test modules
  (`test_generate`/`test_panel`/`test_web`/`test_cli` — the last runs the
  `build --synth` composition, so it is the target build's per-increment gate).

Flags: `--host` (host vectors + UI tests), `--safety` (lint), `--web` (wasm),
`--python` (ruff + mypy + the test modules), `--skill`, `--links`, `--pyright`,
`--all` (the complete gate); `lint --c` runs the `lint` check standalone.

**Config & exit model.** Committed `env.lock` (toolchain/SDK pins + hashes); an
ignored per-checkout env file (toolchain/SDK paths + the `--clock` choice). Build
options are flags. Exit: `0` ok, `1` error, `2` usage, `6` wrong-model; `quick-check`/
`deep-check` return non-zero on a `fail` layer (and on a non-device `blocked` under
`--strict`).

**The CLI's own tests.** `umetate/test_cli.py` — contract tests: every command has
`--help`; `quick-check --json` validates against the §5.5 layer/status shape; a fake
device exercises `flash`/`resume` without hardware; `scaffold` output builds and
passes `make test`.
