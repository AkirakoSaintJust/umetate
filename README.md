# umetate

The **umetate** toolkit — an opinionated framework for designing, building,
testing, and safely installing custom firmware on the M-VAVE FM-1 and SMK-37,
using AI agents. Built on **RIB** (Rigid Inflatable Boat), a source-owned starter
firmware derived from Dinghy/Felucca.

**Author:** P1Onken · **Licence:** GPL-3.0-only · **Status authority:**
[`docs/roadmap.md`](docs/roadmap.md).

## The seven components

1. **CLI (`umetate`)** — one entry point: `doctor`, `setup`, `build`, `check`,
   `package`, `install`, `flash`, `debrick`, `scaffold node|macro|patch`, `add`,
   `lib`, `lint`, `fmt`, `web-build`, `web-serve`, `status`, `help`.
2. **Skill: development** — an agentic design → build loop (offline references).
3. **Skill: safety** — threat model, attack surfaces, device-write gates.
4. **Docker image + volume** — a pinned Linux container; the JieLi toolchain lives
   in a Docker volume at `/opt/jieli` (vendor-terms compliance).
5. **RIB starter firmware** — dual-core by default, FPU opt-in, SMK-37 out of the
   box, hardware-accelerated DSP, the `app_audio`/`app_main` contract.
6. **Tutorial** ([`docs/tutorial.md`](docs/tutorial.md)) — the learner path.
7. **Start guide** (this file).

Targets: **FM-1**, **SMK-37** (Pro/Elite/MKE-P37), the **fm1-emu** model layer,
and the **WASM parity lab**.

## First commands

```sh
python -m pip install -e .
umetate doctor            # verify the environment per evidence layer (read-only)
umetate setup --dry-run   # see exactly what would be installed (opt-in)
umetate check             # run the host-side checks
```

## Repository map

```text
umetate/       the CLI (Python)
firmware/      RIB starter firmware (hardware layer + reference engine)
modules/       the node library (reviewed DSP primitives)
web-synth/     the WASM parity lab
skills/        the two installable skills
templates/     fillable forms + the four schemas
docker/        the pinned build container
docs/          roadmap (status), platform-facts, tutorial, dsp-study
examples/      worked examples
```

## Status

[`docs/roadmap.md`](docs/roadmap.md) is the single source of truth for the design,
the status of every claim, and the implementation plan. Device acceptance is
`blocked` until hardware exists; a target build is not device acceptance.
