# Working on umetate

This file is the entry point for an agent working in this repository. It is a
router, not a second manual. The authoritative documents are:

- `README.md` for the user-facing start guide.
- `docs/roadmap.md` for status and design decisions.
- `skills/umetate-development/SKILL.md` for the firmware loop.
- `skills/umetate-documentation/SKILL.md` for the user docs.
- `plugin/README.md` for the plugin plan and evidence ladder.
- `templates/feature-contract.md` for the contract shape.

## Hard rules

- Keep the 44.1 kHz engine core bit-exact. Adapt at the output boundary only.
- Every manifest parameter must be exposed. Generate the list from
  `firmware/gen/params.json`, never type it by hand.
- Every milestone gets a feature contract and a measured evidence artefact.
  "Builds" is not "done".
- Do not commit build artefacts. They stay in the git-ignored `build/` tree.
  Release bundles are staged by `umetate publish`.
- Do not weaken a test to make a build pass. Fix the code or record the limit.
- Do not describe a blocked layer as passed. The physical device pass is
  `blocked` until hardware is available.
- The source is GPL-3.0-only. The plugin binary also carries JUCE 8's
  AGPL-3.0-only terms. Read `LICENSING.md` before packaging a binary.
- Do not bundle the Digital Desolation Plus brand font.

## The plugin loop

When porting a synth to VST3, CLAP, or AU, read
`skills/umetate-development/references/plugin-port.md`. The short version:

1. Instance-safe engine state before any host code.
2. A JUCE-free engine harness with bit-exact parity.
3. The host skeleton, then the editor, then presets.
4. Output-only rate adaptation with an exact bypass at the core rate.
5. VST3 first, CLAP behind a flag, AU later.
6. Validators and two real DAWs per platform.
7. The source and the licence obligations travel with the binary.

The Type P.fm1 evidence is in `plugin/feature-contract-*.md`.

## Documentation voice

Generated user docs follow `skills/umetate-documentation/references/voice.md`.
The reference samples are `examples/type-p-fm1/publish-readme.md` and
`README.md`. The corpus-derived rhythm samples are in
`skills/umetate-documentation/references/voice-samples.md`. Use the front-door,
manual, or reference register as the page requires. No em dashes. No semicolons.
British spelling in prose. No marketing adjectives. No negative parallelism. No
heading chains. No false dichotomies. One concrete example per major section.

The hand-rewritten `examples/type-p-fm1/docs/manual.md` is the manual calibration.
Keep its contractions, asides, light UK slang, and self-description. Do not flatten
it back to a spec sheet. `humanizer-context.md` carries the same rules for the
humanizer skill.

## UI work

Before a panel, screen, editor, or web UI change, read
`skills/umetate-development/references/ui-design.md` and the ten-item gate in
`skills/umetate-development/SKILL.md` section 2. The interface is designed before
it is written: control map, tokens, and a signed-off mockup first. For a firmware
screen, `design/firmware-mockup.html` renders `panel.json` on the 240 by 240
screen with the dot grid and guides. The casebook and research links are in
`ui-dossier.md`. The Type P.fm1 language is `design/README.md`.

## Commands

```sh
python -m umetate.cli deep-check --all          # the full gate
python -m umetate.cli tokens                    # design tokens + hard-coded UI values
python -m umetate.cli build --synth examples/type-p-fm1
python -m umetate.cli plugin-generate --synth examples/type-p-fm1
python -m umetate.cli plugin-build --synth examples/type-p-fm1
python -m umetate.cli plugin-check --synth examples/type-p-fm1
python -m umetate.cli publish --plugins --vendor-deps build/plugin-juce/_deps  # + RELEASES.md, SHA256SUMS, release.json
cmake -S plugin -B build/plugin-juce -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON
cmake --build build/plugin-juce
ctest --test-dir build/plugin-juce --output-on-failure
```

When the UI is meant to change, review the snapshot diff, then accept it with
`python3 plugin/tools/snapshot_check.py --update --actual <build>/juce/snapshots
--golden plugin/tests/snapshots/linux-x86_64`. Commit the golden images with the
code.

The Docker image is the pinned Linux host. See `docker/README.md` and
`umetate/runner.py`. JACK needs `--shm-size=512m`.
