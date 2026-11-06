# Provenance records

This directory contains baseline and release records. They document evidence, and
they do not track current project status, so see `docs/roadmap.md` for that.

## Naming

- `baseline-YYYY-MM-DD.md`, a frozen source baseline and its inputs.
- `release-vX.Y.Z.md`, a published or candidate release.
- `incident-YYYY-MM-DD.md`, a security or recovery event with its evidence.

## Required fields

Each record should include:

- source commit/tag and whether the tree was clean.
- board/model(s) and package identity.
- toolchain/SDK versions and hashes.
- Emscripten version and WASM result, if applicable.
- build commands/flags.
- `SEC-1`/`SEC-2` gate status.
- evidence layers that passed, failed, or are blocked.
- backup/rollback/recovery notes.
- who approved any device write or publication.

## Current records

- [`baseline-2026-10-27.md`](baseline-2026-10-27.md) records the toolkit baseline
  after P0–P6. Its tag is `umetate-baseline-2026-10-27`.
