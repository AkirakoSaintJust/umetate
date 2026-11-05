# umetate roadmap

This is the current map. The detailed design and the chronological log live in git
at `9375ffe:docs/roadmap.md` and earlier, so this file can stay short.

I use it to answer four things: what exists, what is settled, what is open, and
what I don't want to reopen. Read §2 before you change code, §3 before you pick
work, and §5 before you propose a change. §10 maps the old section numbers that
still show up in code comments.

## 1. Baseline

| Item | State |
| --- | --- |
| Framework | `main` was at `9375ffe` before this rewrite, tracking `origin/main`. Version `0.0.0`. Baseline tag `umetate-baseline-2026-10-27`. |
| Type P.fm1 release | `1.0.1`, 2026-11-04, built from framework `31ecc64`. Release repo `publish/type-p-fm1` at `e40d0cb`. The 1.0.1 binaries are unchanged and the docs are newer. It includes the UC25HQ80 flash fix. |
| Release artefacts | Firmware `type-p-fm1.fwsc` (612,216 B), Linux VST3 and CLAP. macOS/AU and Windows plugin archives aren't in the release yet. |
| Engine | 44.1 kHz, integer-first, bit-exact. 20 voices, 2 parts, 4-op FM, 8 algorithms, 12 waveforms, two filters, a wavefolder, and key and velocity follow. |
| Target evidence | Source, host, browser/WASM parity, target package, emulator, and Linux DAW pass. Physical device timing and acceptance are `blocked`. |
| Gate | The full gate is green. It passed host, web, Python, skill, lib, links, pyright, and memory. |
| Docs | Tutorial, DSP study, Type P.fm1 docs, templates, and the voice profile are current. The Type P.fm1 manual includes the panel section, written from `panel.json` with every page, parameter, and flow. Docs skill `1.4.6`. The K5/K5000 guide is in the ignored `doc-test/`. |
| CI | Framework CI covers Linux and Windows, with macOS `continue-on-error`. The release repo workflow builds Linux and Windows VST3/CLAP on a tag. |

The framework has moved past `31ecc64` with the design interview, the voice profile,
and the docs rewrite. The 1.0.1 binaries haven't changed. The release docs are
synced on `main`; a new release is only needed when the binaries change.

## 2. Settled decisions

These are the things I don't want to relitigate without a feature contract and
evidence.

- **Engine core.** 44.1 kHz, integer-first, bit-exact. Adapt at the output boundary
  only. `double` stays out of the DSP, and float remains an opt-in path.
- **Parameters.** Every manifest parameter gets exposed. The list comes from
  `firmware/gen/params.json`, and nobody types it by hand.
- **Evidence.** Source, host, browser, target package, emulator, timing, device, and
  release are separate layers. A lower layer never proves a higher one. `blocked`
  and `not-run` are not passes.
- **Device writes.** A build, test, or edit never gives you permission to write
  hardware. `flash` and `debrick` need an explicit request, identity, verified
  package, rollback, recovery route, and `--device`.
- **Licensing.** The source is GPL-3.0-only. The plugin binary carries JUCE 8's
  AGPL-3.0-only terms, and the brand font stays out.
- **Targets.** VST3 comes first, CLAP sits behind a flag, AU comes later. Linux is
  validated. macOS and the Windows plugin release are still open.
- **Architecture.** 20 voices, 2 parts, 4-op FM, 8 algorithms, 12 waveforms, two
  multimode filters, a wavefolder, per-operator feedback, key and velocity follow,
  and per-part algorithm and FM depth.
- **Identity and clock.** The `_990` identities are frozen: `FM-1_990`,
  `SMK-37 Pro_990`, `SMK-37 Elite_990`, `MKE-P37_990`. Artifact names can change.
  The clock offers 240 or 320 MHz only, because 360 and 396 aren't offered.
- **UI method.** Design comes before code: control map, tokens, signed-off mockup.
  The ten-item gate is in the development skill and `templates/control-map.md`.
- **Docs voice.** The hand-written manual and guide are the calibration. That means
  no em dashes or semicolons, no negative parallelism, heading chains, false
  dichotomies, marketing hooks, aphorisms, or "A, not B" adversatives. Join the
  clauses and end on something concrete.
- **Release.** `umetate publish` writes `RELEASES.md`, `SHA256SUMS`, and
  `release.json`. Vendor dependencies are copied source-only, and build artefacts
  stay in `build/`.
- **Performance.** 45% ISR at 320 MHz with 20 voices, bit-exact. Hand-written asm
  and SIMD are deferred.
- **Done.** Phases 0-7 are complete for host, browser, target package, emulator,
  and Linux. The device layer stays blocked.

## 3. Current work

The pyright gate is green now. I'd take the rest in this order.

| # | Work | Done when | Status |
| --- | --- | --- | --- |
| 1 | Refresh the Type P.fm1 source snapshot | The release `framework/` source matches the current docs and CLI, or the notes explain why the older snapshot is intentional. | optional |
| 2 | Windows VST3/CLAP archives | The release workflow builds them, `RELEASES.md` lists them, and the checksums pass. | open |
| 3 | macOS build and AU | A macOS host builds the VST3/AU, the validators pass, and the CI job stops being `continue-on-error`. | blocked |
| 4 | Signed installers | The platform installers are signed and the release page links them. | open |
| 5 | Vendored JUCE source archive | Every plugin release carries the source archive and the AGPL notice. | open |
| 6 | Usability test | A player who did not design the panel can make a sound and find save without help. | optional |
| 7 | Performance follow-up | Hand-asm or SIMD is measured, bit-exact, and justified by a target need. | deferred |

## 4. Blocked

These wait on something I can't supply from here.

| Work | Missing |
| --- | --- |
| Physical device timing and acceptance | An FM-1 or SMK-37 unit. |
| FPU opt-in and target parity | A device probe. |
| Clock soak | A device. |
| Hardware FFT/vector parity | A device. |
| `mask-rom` debrick | The USB_KEY dongle needs a USB solder. |
| macOS build and AU | A macOS host. |
| Windows plugin release | A Windows release build and signing path. |
| Signed installers | Signing identities. |

## 5. What not to do

These are the rules I don't want to lose.

- Leave the 44.1 kHz engine core alone. Adapt at the output boundary.
- Keep `float` and `double` out of the integer DSP path.
- Regenerate generated files (`firmware/gen/`, `docs/module-library.md`,
  `skills/*/references/`, plugin `gen/`) instead of editing them.
- Never flash as a side effect of a build, test, or edit.
- Never call a blocked layer passed. Don't say "device-accepted" or
  "security-clean" while the device layer is blocked.
- Don't add a parameter outside the manifest or invent a panel name.
- Keep the brand font out.
- Don't rename the frozen `_990` identities. Don't offer 360 or 396 MHz.
- Keep build artefacts in `build/`.
- Don't reopen a settled decision without a feature contract and evidence.
- Don't turn this file into a history. Keep it current.

## 6. Project map

One table for the pieces I need to find quickly.

| Component | What it is | Where | State |
| --- | --- | --- | --- |
| CLI | `umetate` commands | `umetate/` | done (host/browser/target) |
| Development skill | design and build loop | `skills/umetate-development/` | done |
| Safety skill | threat model and device gates | `skills/umetate-safety/` | done |
| Documentation skill | user docs, voice, interview | `skills/umetate-documentation/` | done, 1.4.4 |
| Docker and toolchain | pinned Linux host and JieLi SDK | `docker/`, `umetate/runner.py` | done |
| RIB runtime | dual-core starter firmware | `firmware/` | done (host/target), device blocked |
| Docs | tutorial, DSP study, platform facts, module library | `docs/`, `firmware/README.md` | current |
| Type P.fm1 | worked example and release | `examples/type-p-fm1/`, `publish/type-p-fm1` | 1.0.1 |
| Plugin | JUCE host, VST3/CLAP | `plugin/`, `design/` | Linux done, macOS/AU/Windows open |

## 7. Status ledger

`umetate status` reads these headers, so keep the phase and step format.

### Phase 0, Governance & skeleton (P0), **done**
### Phase 1, Docker image + volume (P1), **done**
### Phase 2, RIB runtime + generator (P2), **done (host + target), blocked (device)**
**P2-2, Dual-core bring-up.**, **done (source/host/target), blocked (device)**, the core-1 probe and CPU0 fallback are in. Device acceptance waits on hardware.
**P2-3, Hardware acceleration HAL.**, **done (source/host/target), blocked (device)**, the HAL and fallback are in. Hardware parity waits on a device.
**P2-4, FPU opt-in (`--dsp float`).**, **blocked**, the flag is accepted, the DSP path is not wired, and target parity waits on a device.
**P2-5, Clock profiles (240/320).**, **done (CLI), blocked (device)**, the setup and CLI are in. The soak waits on a device.
**P2-6, SMK-37 board layer.**, **done (builds), blocked (device)**, the board layer builds. Device acceptance waits on hardware.
**P2-7, Recovery and safety in firmware.**, **done (host), blocked (device)**, the host tests and gates are in. The device check waits on hardware.
### Phase 3, CLI (P3), **done (host/browser/target), blocked (device)**
**P3-4, Flash and debrick.**, **done (host), blocked (device)**, the gates and wrong-model exit 6 are in. The real-device pass waits on hardware.
### Phase 4, Web lab and emulator (P4), **done**
### Phase 5, Skills (P5), **done**
### Phase 6, Tutorial and start guide (P6), **done**
### Phase 7, Release and provenance (P7), **done (Linux), blocked (device)**
**P7-1, Baseline tag and provenance.**, **done**, `provenance/` and the baseline tag are in.
### Phase 8, Post-release (P8), **done (Linux/docs), open (macOS/AU/Windows)**
**P8-1, Type P.fm1 1.0.1.**, **done (Linux)**, the firmware and Linux VST3/CLAP are published. macOS/AU and Windows archives are open.
**P8-2, Documentation voice pass.**, **done**, tutorial, DSP study, Type P.fm1 docs, templates, and the voice profile are current.
**P8-3, Pyright gate.**, **done**, the 14 errors in `interview.py`, `publish.py`, and `test_cli.py` are fixed.
**P8-4, Windows plugin archives.**, **open**, the release workflow needs a Windows build and signed archives.
**P8-5, macOS build and AU.**, **blocked**, no macOS host.
**P8-6, Physical device acceptance.**, **blocked**, no hardware.
**P8-7, Signed installers.**, **open**, no signing identity.
**P8-8, Vendored JUCE archive.**, **open**, the release should carry the source archive and notice.
**P8-9, Usability test.**, **open**, optional, a player who did not design the panel.

## 8. Evidence and definition of done

- Every feature gets a feature contract in `templates/feature-contract.md` and a
  measured evidence artefact.
- The layers are source/static, host, browser/WASM, target package, emulator,
  physical timing, device acceptance, and release provenance.
- A lower layer never proves a higher one, and `blocked` or `not-run` is not a pass.
- `deep-check --all` is the gate. It's green now.
- A release needs the source, licence, notices, checksums, and manifest. The device
  layer stays blocked until hardware and approval exist.

## 9. Risks and open questions

- **Release source snapshot.** The 1.0.1 binaries came from `31ecc64`. The release
  docs are synced at `e40d0cb`, but the `framework/` source snapshot still matches
  the 1.0.1 binaries. Refresh it only if the release should include the later CLI
  and source.
- **Plugin editor scope.** The editor pages and host tests are built around Type
  P.fm1. A different synth needs its own pages, tests, and company override.
- **Platforms.** macOS/AU and the Windows plugin release are open. Linux is
  validated.
- **Device.** Physical acceptance, timing, FPU parity, clock soak, hardware
  FFT/vector parity, and the mask-ROM route all wait on hardware or a solder.
- **Deferred performance.** Hand-written asm/VLIW, SIMD for the post path, and
  silent-operator skip. The 45% ISR budget is already met.
- **Deferred features.** The VPS multi-breakpoint/audio-rate macro, ping-pong DSP
  blocks, and the per-operator-pass restructure.
- **Open questions.** The exact MCU part/revision, and whether the FM-1 enables the
  FPU by default. Both need a device probe.

## 10. Old section numbers still cited in code

The detailed design is in git at `9375ffe:docs/roadmap.md`. Code comments still cite
these old section numbers, so this table is the bridge.

| Old | Use now |
| --- | --- |
| §3.1 | `templates/scaffold/node.schema.json`, `patch.schema.json` |
| §3.2 | `templates/scaffold/panel.schema.json` |
| §6.2 | `skills/umetate-development/SKILL.md` |
| §6.8 | `umetate/_schema.py` |
| §6.9 | `modules/nodes/` |
| §6.10 | `firmware/src/scope.c`, `firmware/theme.json` |
| §6.11 | `umetate/_panel.py`, `examples/type-p-fm1/panel.json` |
| §6.11.4 | `firmware/src/presets.h`, `umetate/_presets.py`, `umetate/_records.py`, `umetate/_sysex.py` |
| §6.14 | `umetate/publish.py` |
| §12.1 | `firmware/README.md`, `docs/dsp-study.md` |
| §12.4 | `umetate/_frontend.py`, `umetate/_backend.py`, `umetate/_ir.py`, `umetate/_tables.py` |
| §12.6 | `firmware/src/ui.c`, `firmware/src/ui.h` |
| §12.7.2 | `umetate/web.py` |
| §12.7.3 | `umetate/test_perf.py` |
| §12.8 | `umetate/cli.py`, `umetate/status.py` |
