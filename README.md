# umetate

**umetate** helps you design, build, test, and safely install custom firmware on
the M-VAVE FM-1 and SMK-37, with help from AI agents. The firmware runs on **RIB**
(Rigid Inflatable Boat), a source-owned starter derived from Dinghy/Felucca.

**Author:** P1Onken · **Licence:** GPL-3.0-only · **Status authority:**
[`docs/roadmap.md`](docs/roadmap.md).

## The seven components

1. **CLI (`umetate`)** — the single entry point for environment checks, setup,
   builds, emulation, inspection, device installation and recovery, scaffolding,
   linting, formatting, the web lab, evidence, status, and help. Commands include
   `quick-check`, `setup`, `build`, `emu`, `deep-check`, `inspect`, `flash`,
   `debrick`, `scaffold node|macro|patch`, `lib`, `lint`, `fmt`, `web-build`,
   `web-serve`, `evidence`, `status`, `version`, and `help`.
2. **Development skill** — guides the design-to-build workflow using offline
   references.
3. **Safety skill** — documents the threat model, attack surfaces, and gates for
   writing to a device.
4. **Docker image + volume** — a pinned Linux container; the JieLi toolchain lives
   in a Docker volume at `/opt/jieli` (vendor-terms compliance). It is mounted
   **read-only** for every build/test, and **read-write only for `umetate setup`**
   (the one command that installs the toolchain + SDK).
5. **RIB starter firmware** — dual-core by default, with optional FPU support,
   SMK-37 support, hardware-accelerated DSP, and the `app_audio`/`app_main`
   contract.
6. **Tutorial** ([`docs/tutorial.md`](docs/tutorial.md)) — the guided path from
   environment checks through device validation.
7. **Start guide** — this file, with the first commands and repository map.

The toolkit targets the **FM-1** and **SMK-37** (Pro/Elite/MKE-P37). It also
includes the **fm1-emu** model layer and a **WASM parity lab**.

## First commands

```sh
python -m pip install -e .
umetate quick-check      # verify the environment per evidence layer (read-only)
umetate setup --dry-run  # see exactly what would be installed (opt-in)
umetate deep-check       # run the host-side checks
```

## Repository map

```text
umetate/       the CLI (Python)
firmware/      RIB starter firmware (hardware layer + reference engine)
modules/       the module library: nodes/ (DSP primitives) + macros/ (subgraphs)
build/web/     the WASM parity lab output (`web-build` → standalone dsp.wasm)
skills/        the two installable skills
templates/     fillable forms + the four schemas
docker/        the pinned build container
docs/          roadmap (status), platform-facts, tutorial, dsp-study
examples/      worked examples
```

## Status

[`docs/roadmap.md`](docs/roadmap.md) is the source of truth for the design,
implementation plan, and status of each claim. Device acceptance remains
`blocked` until hardware is available. A successful target build does not establish
that the firmware has been accepted on a device.
