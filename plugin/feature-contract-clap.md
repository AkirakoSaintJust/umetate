# Feature contract: the CLAP target and platform matrix

## Identity

- **Feature:** Milestone 6, the CLAP target and the platform matrix.
- **Brief section:** `plugin/README.md` sections 1, 12 and 13, and
  `docs/roadmap.md` 13.23.
- **Owner / date:** P1Onken, 2026-11-04.
- **Disposition:** accepted for the Linux and Windows builds. macOS remains
  untested.

## Player outcome

- **What the player can do that they could not do before:** load Type P.fm1 in a
  CLAP host, not only in a VST3 host, and automate the same 313 manifest
  parameters with the same engine and preset banks.
- **How it sounds or behaves:** identical to the VST3 build. The CLAP wrapper
  carries the same processor, editor, MIDI bridge and output rate bridge. The
  CLAP plugin id is `com.p1onken.typepfm1`.
- **How it fails visibly and safely:** a rejected state chunk leaves the current
  parameters and banks in place. The wrapper returns success for a random chunk,
  so the host cannot see the rejection, but the processor does not apply it and
  does not crash.

## Dependencies and interactions

- **Other features:** the generated engine, the APVTS parameter layout, the
  editor, the device record banks and the output rate bridge.
- **Platform/API/HAL changes:** the JUCE project adds a `type_p_fm1_CLAP` target
  through `clap_juce_extensions_plugin`. `P1_BUILD_CLAP` defaults to ON inside
  the `P1_BUILD_JUCE` path. The dependency is pinned to
  `7adee3a1bd4684d4caa5601100e364abccff4b4d` because tag `0.26.0` includes the
  old `juce_audio_plugin_client/utility/juce_LinuxMessageThread.h` path that
  JUCE 8 removed. The Windows build uses MSVC and adds
  `plugin/engine/msvc_compat.h` to map the firmware GCC attributes to nothing.
  `firmware/hal/fm1_ipc.h` now copies a volatile command struct field by field,
  which GCC and MSVC both accept. JUCE 8 rejects MinGW, so MSYS2 gcc is not a
  supported Windows path.
- **Persistence/version impact:** none. The state version stays 2. CLAP state
  save and load call the existing `getStateInformation` and
  `setStateInformation`.
- **MIDI/clock impact:** none. The wrapper feeds the JUCE MIDI buffer and the
  existing `MidiBridge` keeps the 32-sample control block.

## Parameter and event semantics

- **Parameters, ranges, defaults, curves, units:** every manifest parameter is
  exposed. The manifest remains authoritative.
- **Zero-range parameter:** `fold_type` has `min == max == 0`. JUCE rejects a
  zero-range `AudioParameterInt` and a single-item `AudioParameterChoice`.
  The APVTS exposes it as 0..1 with default 0, and `syncParams` clamps it back to
  the manifest maximum before it reaches the engine. The host can automate the
  synthetic range, but the engine value stays 0.
- **Note/event ordering and ownership:** unchanged. CLAP note and parameter
  events reach the processor through the JUCE wrapper.
- **Voice allocation and stealing:** unchanged, 20 voices.
- **Sustain/panic behaviour:** unchanged.

## Bounds and resources

- **Maximum voices/events/effects:** unchanged.
- **Per-sample and per-block operations:** unchanged from Milestone 5.
- **RAM, flash, stack, pool:** one extra wrapper per plugin instance. The DSP
  engine and the banks are not duplicated.
- **Overflow/overload policy:** the wrapper owns state chunk buffering. The
  processor rejects invalid or empty XML.
- **Division, shift, and range analysis:** no new audio-thread arithmetic. The
  zero-range clamp is an integer `jlimit` in `syncParams`.

## Files and interfaces

- **Files:** `plugin/juce/CMakeLists.txt`, `plugin/juce/PluginProcessor.cpp`,
  `plugin/engine/msvc_compat.h`, `plugin/CMakeLists.txt`,
  `firmware/hal/fm1_ipc.h`, `plugin/tests/plugin_smoke.cpp`,
  `plugin/feature-contract-clap.md`, `plugin/README.md` and
  `docs/roadmap.md`.
- **Public contract/header:** no processor API change. `P1_BUILD_CLAP` is the
  new build option. The CLAP binary exports the JUCE wrapper entry points.
- **State owner and publication rule:** the processor owns the engine, the
  APVTS and the banks. After state load, `setStateInformation` calls
  `updateHostDisplay` with `programChanged` so the CLAP wrapper sends a
  parameter value rescan.
- **Forbidden dependencies:** no new audio-thread allocation, locks or file
  access. No change to the generated DSP. No flash or device write path.

## Verification

- **Host vector(s):** `plugin_smoke` sets every manifest parameter to a
  deterministic value, saves the state, loads it into a second processor and
  checks every parameter. The five CTest targets stay green.
- **Browser vector:** unchanged, `deep-check --all` stays green.
- **Target package check:** unchanged.
- **CLAP vector:** `clap-validator` 0.4.1 runs 44 tests on Linux. The result is
  33 passed, 0 failed, 1 warning and 10 skipped. On Windows it is 32 passed, 0
  failed, 1 warning and 11 skipped. The warning is `state-invalid-random`,
  because the wrapper returns success for random bytes that the processor
  rejects. The warning is upstream wrapper behaviour and the plugin does not
  crash.
- **VST3 vector:** `pluginval` 1.0.4 at strictness level 5 passes both with the
  editor open and with GUI tests skipped on Linux and Windows. The same build
  passes at 44.1, 48, 96 and 192 kHz with block sizes from 32 to 1024.
- **DAW vector:** REAPER 7.84 loads the Windows VST3 and CLAP builds. A one-note
  project per format renders 88200 frames at 44100 Hz, and the two WAV files are
  byte identical. Renoise 3.5.4 is installed but only scans VST3 from
  `C:\Program Files\Common Files\VST3`, which the current account cannot write.
- **Physical timing/device check:** blocked, no hardware.
- **Platform matrix:** Linux x86-64 and Windows x86-64 are built and validated.
  macOS is not built here. The full two-DAW matrix is blocked by the Renoise
  VST3 path permission and by the missing macOS host. AU remains later.
- **Tolerance/metric:** zero validator failures. The one warning is documented.
- **Evidence artifact:** the `clap-validator` terminal summary, the `pluginval`
  `SUCCESS` line, the REAPER WAV hashes, and the plugin CTest output.

## Result (2026-11-04)

- The CLAP target configures and builds with JUCE 8.0.9 and the pinned
  `clap-juce-extensions` commit. CLAP 1.2.7 is linked on Linux and Windows.
- `clap-validator` moved from 21 passed and 12 failed to 33 passed and 0 failed
  on Linux. The Windows result is 32 passed and 0 failed.
- The parameter default failure was fixed by giving `fold_type` a 0..1 APVTS
  range and clamping it to the manifest maximum in `syncParams`.
- The three state reproducibility tests pass after `setStateInformation`
  requests a parameter rescan.
- The Windows build passes all five CTests with MSVC 19.51.
- `pluginval` passes in GUI mode with the editor open and in headless mode with
  GUI tests skipped on both platforms.
- REAPER 7.84 renders the Windows VST3 and CLAP builds to byte-identical WAV
  files. Each render is 88200 frames at 44100 Hz, 24-bit stereo, peak 0.609467,
  RMS 0.14412, SHA-256
  `d595f204fe537e74eb512e94a5fcdb0bb1c38b08b3f955d21019b486ae4b47a2`.
- `plugin_smoke` now proves a full 313-parameter state round trip, not only one
  parameter.
- The remaining warning is in the wrapper state loader, not in the processor.

## Risks and fallback

- **Assumptions/open research:** the pinned wrapper remains compatible with
  future JUCE updates. The warning may disappear when the wrapper starts
  returning a real load result.
- **Safe experiment and stop criterion:** load a saved state in a second CLAP
  instance and compare all 313 values. Stop if any value differs.
- **Windows host path limit:** Renoise only scans VST3 from
  `C:\Program Files\Common Files\VST3`. Use an elevated install there, or use a
  host that scans the build tree, before calling the second DAW pass.
- **Smaller alternative:** ship VST3 only and keep CLAP behind `P1_BUILD_CLAP`.
  The current default builds both.
- **Rollback:** remove the `FetchContent` block and the
  `clap_juce_extensions_plugin` call. The VST3, standalone, engine and banks are
  unchanged.
