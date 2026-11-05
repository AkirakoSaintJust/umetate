# umetate

umetate is the framework I use to design, build, test, and safely install custom
firmware on the M-VAVE FM-1 and SMK-37, with AI agents working alongside. It keeps
the synth project, the generated DSP, the browser build, the plugin, the tests, the
docs, and the licence trail in one tree. The firmware runs on RIB (Rigid Inflatable
Boat), a source-owned starter derived from Dinghy/Felucca.

**Author:** P1Onken · **Licence:** GPL-3.0-only · **Status authority:**
[`docs/roadmap.md`](docs/roadmap.md).

## Components

- **CLI.** Everything starts at `umetate`. It checks the environment, sets up
  the toolchain, builds and emulates, inspects, flashes and recovers, scaffolds
  nodes, macros and patches, lints and formats, runs the web lab, and reports
  evidence and status. The commands are `quick-check`, `setup`, `build`, `emu`,
  `deep-check`, `inspect`, `flash`, `debrick`, `scaffold node|macro|patch`,
  `interview`, `lib`, `lint`, `fmt`, `web-build`, `web-serve`, `evidence`, `status`,
  `version`, and `help`.
- **Development skill.** It guides the design-to-build workflow with the offline
  references.
- **Safety skill.** It holds the threat model, the attack surfaces, and the gates
  for writing to a device.
- **Documentation skill.** It writes the user manual, the panel section, the MIDI
  and SysEx reference, the patch sheet, the install guide, and the release notes for
  a finished project. Its voice method is the humanizer skill in
  `skills/umetate-humanizer/`.
- **Docker image and volume.** The build host is a pinned Linux container. The
  JieLi toolchain lives in a Docker volume at `/opt/jieli`, separate from the
  repository for the vendor terms, mounted read-only for every build and test, and
  read-write only for `umetate setup`, the one command that installs the toolchain
  and SDK.
- **RIB.** The starter firmware is dual-core by default, with optional FPU support,
  SMK-37 support, hardware-accelerated DSP, and the `app_audio`/`app_main` contract.
- **Tutorial.** [`docs/tutorial.md`](docs/tutorial.md) is the guided path from
  the environment check through device validation.

This file is the start guide, with the first commands and the repository map.

The toolkit targets the FM-1 and SMK-37 (Pro/Elite/MKE-P37). It also includes the
fm1-emu model layer and a WASM web app.

## Try a project in the browser

The web app is the first place I go to hear a project before I flash anything.
There's no toolchain and no device. It compiles the same generated DSP to WASM and
runs it in a browser page, bit-exact with the host build.

```sh
umetate web-build --synth examples/type-p-fm1   # build the browser app
umetate web-serve                              # serve it, then open the printed URL
```

`web-build` defaults to `examples/type-p-fm1` when no project is given. The host and
WASM outputs are checked byte-for-byte by `umetate deep-check --web`.

## Plugins

The same engine builds as a VST3 and a CLAP plugin. The source is in `plugin/`. The
44.1 kHz engine core stays bit-exact and the sample rate is adapted at the output
boundary, so the device render stays the reference.

```sh
umetate plugin-generate --synth examples/type-p-fm1
umetate plugin-build --synth examples/type-p-fm1
umetate plugin-check --synth examples/type-p-fm1
```

`plugin-generate` renders the synth's `patch.json`, `panel.json`, and `app.c` into
`build/plugin/<cname>/`, including `gen/` and a `P1Project.cmake` with the plugin
identity from `plugin.json`. `plugin-build` configures and builds that project and
runs ctest. `plugin-check` verifies the generated files and reruns the tests.

A plain checkout still builds the checked-in Type P.fm1 defaults directly:

```sh
cmake -S plugin -B build/plugin-juce -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON
cmake --build build/plugin-juce
ctest --test-dir build/plugin-juce --output-on-failure
```

Type P.fm1 passes `pluginval` at strictness 5 and the CLAP validator on Linux and
Windows, and renders in REAPER on Windows. The macOS build, the AU target, and the
macOS DAW matrix are still open. You'll find the evidence in `plugin/`.

## Ship a project

`umetate publish` stages a release: the user docs, the `.fwsc` firmware, the
framework source, the plugin bundles, the third-party licences, and optionally the
vendored dependency source. It writes `RELEASES.md`, `SHA256SUMS`, and
`release.json`, so the firmware and plugin downloads carry checksums and source
links. Build artefacts stay in the ignored `build/` tree.

```sh
umetate publish --plugins --vendor-deps build/plugin-juce/_deps
```

A hand-written `publish-readme.md` in the project is copied verbatim as the release
front door. Without one, `publish` writes a README from its template.

## Write the docs

`umetate interview --synth examples/type-p-fm1 --write` generates a synth-specific
design interview form from the project's `patch.json`, `panel.json`, and
`synth-brief.md`. The questions use the synth's own architecture and words, rather
than a fixed FM template. The documentation skill uses the answers to write the
manual preface: personal history, the synthesis lineage, the design decisions, the
trade-offs, and the first patch. The raw notes stay in the project and out of the
release. `umetate interview --next 3` prints the next gaps, and `--check` lists every
open question.

## Continuous integration

`.github/workflows/ci.yml` runs the Python gate and the plugin build on Linux and
Windows. macOS is reported without blocking while the macOS build and the AU target
remain open. The workflow runs on pushes to `main` and on pull requests. Its plugin
jobs are framework tests, so they keep the product build path honest without
publishing an archive.

The published `type-p-fm1` repository has its own release workflow. A `v*` tag, or
a manual run with `1.0.2` or `v1.0.2`, builds the VST3 and CLAP archives for Linux
x86_64, Linux aarch64, and Windows x86_64 from the bundled `framework/plugin`
source. A manual run tags the dispatched `main` commit when the tag does not exist,
and it refuses a version that does not match the newest `CHANGELOG.md` heading. The
workflow attaches the firmware, the per-platform plugin archives, the manifests,
and a source archive to a GitHub Release, then records `RELEASES.md`, `SHA256SUMS`,
and `release.json` on `main`. Build outputs and plugin archives stay out of the
repository. The firmware is the committed `.fwsc`, so that workflow does not need
the JieLi toolchain.

## First commands

```sh
python -m pip install -e .
umetate quick-check      # check the environment, read-only
umetate setup --dry-run  # see what setup would install, before it does
umetate deep-check       # run the host-side checks
umetate build --synth examples/type-p-fm1   # compose the dogfood firmware (host evidence and package)
umetate emu --check --mhz 240              # boot it and hold a chord
```

## Repository map

```text
umetate/       the CLI (Python)
firmware/      RIB starter firmware (hardware layer + reference engine)
modules/       the module library: nodes/ (DSP primitives) + macros/ (subgraphs)
plugin/        the JUCE VST3/CLAP target and its tests
design/        design tokens, the plugin mockup, the firmware screen mockup
build/web/     the browser app output (`web-build` → the page + `firmware.wasm`)
skills/        the four skills: development, safety, documentation, humanizer
templates/     fillable forms + the four schemas
docker/        the pinned build container
docs/          roadmap (status), platform-facts, tutorial, dsp-study, opm-file-format, opm-to-type-p-fm1, type-p-fm1-envelope-design
examples/      worked examples
.github/       CI workflows
```

## Status

[`docs/roadmap.md`](docs/roadmap.md) is the source of truth for the design,
implementation plan, and status of each claim. Device acceptance remains `blocked`
until hardware is available. A successful target build does not establish that the
firmware has been accepted on a device.
