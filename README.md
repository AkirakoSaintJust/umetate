# umetate

**umetate** helps you design, build, test, and safely install custom firmware on
the M-VAVE FM-1 and SMK-37, with help from AI agents. The firmware runs on **RIB**
(Rigid Inflatable Boat), a source-owned starter derived from Dinghy/Felucca.

**Author:** P1Onken · **Licence:** GPL-3.0-only · **Status authority:**
[`docs/roadmap.md`](docs/roadmap.md).

## The eight components

1. **CLI (`umetate`)**, the single entry point for environment checks, setup,
   builds, emulation, inspection, device installation and recovery, scaffolding,
   linting, formatting, the web lab, evidence, status, and help. Commands include
   `quick-check`, `setup`, `build`, `emu`, `deep-check`, `inspect`, `flash`,
   `debrick`, `scaffold node|macro|patch`, `lib`, `lint`, `fmt`, `web-build`,
   `web-serve`, `evidence`, `status`, `version`, and `help`.
2. **Development skill**, guides the design-to-build workflow using offline
   references.
3. **Safety skill**, documents the threat model, attack surfaces, and gates for
   writing to a device.
4. **Documentation skill**, writes the user manual, panel reference, MIDI and
   SysEx reference, patch sheet, installation guide, and release notes for a
   finished project.
5. **Docker image + volume**, a pinned Linux container, the JieLi toolchain lives
   in a Docker volume at `/opt/jieli` (vendor-terms compliance). It is mounted
   **read-only** for every build/test, and **read-write only for `umetate setup`**
   (the one command that installs the toolchain + SDK).
6. **RIB starter firmware**, dual-core by default, with optional FPU support,
   SMK-37 support, hardware-accelerated DSP, and the `app_audio`/`app_main`
   contract.
7. **Tutorial** ([`docs/tutorial.md`](docs/tutorial.md)), the guided path from
   environment checks through device validation.
8. **Start guide**, this file, with the first commands and repository map.

The toolkit targets the **FM-1** and **SMK-37** (Pro/Elite/MKE-P37). It also
includes the **fm1-emu** model layer and a **WASM web app**.

## Try a project in the browser

The web app is the primary, empirical way to hear where a project stands, with no
toolchain and no device. It compiles the same generated DSP to WASM and runs it in
a browser page, bit-exact with the host build.

```sh
umetate web-build examples/type-p-fm1   # compile the project's DSP to standalone dsp.wasm
umetate web-serve                       # serve it, then open the printed URL
```

`umetate web-build` defaults to `examples/type-p-fm1` when no patch is given. The
host and WASM outputs are checked byte-for-byte by `umetate deep-check --web`.

## First commands

```sh
python -m pip install -e .
umetate quick-check      # verify the environment per evidence layer (read-only)
umetate setup --dry-run  # see exactly what would be installed (opt-in)
umetate deep-check       # run the host-side checks
umetate build --synth examples/type-p-fm1   # compose the dogfood firmware (host evidence + package)
umetate emu --check --mhz 240              # boot it in the emulator, hold a chord
```

## Repository map

```text
umetate/       the CLI (Python)
firmware/      RIB starter firmware (hardware layer + reference engine)
modules/       the module library: nodes/ (DSP primitives) + macros/ (subgraphs)
build/web/     the WASM web app output (`web-build` → standalone dsp.wasm + page)
skills/        the three installable skills
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
