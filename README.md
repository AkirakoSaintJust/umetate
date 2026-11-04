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
   `debrick`, `scaffold node|macro|patch`, `interview`, `lib`, `lint`, `fmt`,
   `web-build`, `web-serve`, `evidence`, `status`, `version`, and `help`.
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

## Plugins

The same engine builds as a VST3 and a CLAP plugin. The source is in `plugin/`.
The 44.1 kHz engine core stays bit-exact and the sample rate is adapted at the
output boundary, so the device render stays the reference.

```sh
umetate plugin-generate --synth examples/type-p-fm1
umetate plugin-build --synth examples/type-p-fm1
umetate plugin-check --synth examples/type-p-fm1
```

`plugin-generate` renders the synth's `patch.json`, `panel.json`, and `app.c`
into `build/plugin/<cname>/`, including `gen/` and a `P1Project.cmake` with the
plugin identity from `plugin.json`. `plugin-build` configures and builds that
project and runs ctest. `plugin-check` verifies the generated files and reruns
the tests. A plain checkout still builds the checked-in Type P.fm1 defaults
directly:

```sh
cmake -S plugin -B build/plugin-juce -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON
cmake --build build/plugin-juce
ctest --test-dir build/plugin-juce --output-on-failure
```

Type P.fm1 passes `pluginval` at strictness 5 and the CLAP validator on Linux and
Windows, and renders in REAPER on Windows. The macOS build, the AU target, and the
macOS DAW matrix are still open. The evidence is in `plugin/`.

## Ship a project

`umetate publish` stages a release: the user docs, the `.fwsc` firmware, the
framework source, the plugin bundles, the third-party licences, and optionally the
vendored dependency source. It writes `RELEASES.md`, `SHA256SUMS`, and
`release.json` so the firmware and plugin downloads carry checksums and source
links. Build artefacts stay in the ignored `build/` tree.

```sh
umetate publish --plugins --vendor-deps build/plugin-juce/_deps
```

A hand-written `publish-readme.md` in the project is copied verbatim as the release
front door. Without one, `publish` writes a README from its template.

## Write the docs

`umetate interview --synth examples/type-p-fm1 --write` generates a synth-specific
design interview form from the project's `patch.json`, `panel.json`, and
`synth-brief.md`. The questions use the synth's own architecture and words, not a
fixed FM template. The documentation skill uses the answers to write the manual
preface: personal history, the synthesis lineage, the design decisions, the
trade-offs, and the first patch. The raw notes stay in the project and out of the
release. `umetate interview --next 3` prints the next gaps, and `--check` lists
every open question.

## Continuous integration

`.github/workflows/ci.yml` runs the Python gate and the plugin build on Linux and
Windows. macOS is reported without blocking while the macOS build and the AU
target remain open. The workflow runs on pushes to `main` and on pull requests.

The published `type-p-fm1` repository has its own release workflow. A `v*` tag
builds the VST3 and CLAP archives for Linux and Windows from the bundled
`framework/plugin` source, updates `plugins/`, `RELEASES.md`, `SHA256SUMS`, and
`release.json`, and attaches the firmware, plugin archives, manifests, and a
source archive to a GitHub Release. The firmware is the committed `.fwsc`, so
that workflow does not need the JieLi toolchain.

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
plugin/        the JUCE VST3/CLAP target and its tests
design/        design tokens, the plugin mockup, the firmware screen mockup
build/web/     the WASM web app output (`web-build` → standalone dsp.wasm + page)
skills/        the three installable skills
templates/     fillable forms + the four schemas
docker/        the pinned build container
docs/          roadmap (status), platform-facts, tutorial, dsp-study
examples/      worked examples
.github/       CI workflows
```

## Status

[`docs/roadmap.md`](docs/roadmap.md) is the source of truth for the design,
implementation plan, and status of each claim. Device acceptance remains
`blocked` until hardware is available. A successful target build does not establish
that the firmware has been accepted on a device.
