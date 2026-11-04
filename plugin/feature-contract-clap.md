# Feature contract: the CLAP target and platform matrix

## Identity

- **Feature:** Milestone 6, the CLAP target and the platform matrix.
- **Brief section:** `plugin/README.md` sections 1, 12 and 13, and
  `docs/roadmap.md` 13.23.
- **Owner / date:** P1Onken, 2026-11-04.
- **Disposition:** accepted for the Linux build. Windows and macOS remain
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
  JUCE 8 removed.
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
  `plugin/tests/plugin_smoke.cpp`, `plugin/feature-contract-clap.md`,
  `plugin/README.md` and `docs/roadmap.md`.
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
- **CLAP vector:** `clap-validator` 0.4.1 runs 44 tests. The result is 33 passed,
  0 failed, 1 warning and 10 skipped. The warning is
  `state-invalid-random`, because the wrapper returns success for random bytes
  that the processor rejects. The warning is upstream wrapper behaviour and the
  plugin does not crash.
- **VST3 vector:** `pluginval` 1.0.4 at strictness level 5 passes both with the
  editor open and with GUI tests skipped. The same build passes at 44.1, 48, 96
  and 192 kHz with block sizes from 32 to 1024.
- **Physical timing/device check:** blocked, no hardware.
- **Platform matrix:** Linux x86-64 is built and validated. Windows and macOS
  are not built in this container. They need a native build, `pluginval` and
  two DAWs per platform before they count as pass. AU remains later.
- **Tolerance/metric:** zero validator failures. The one warning is documented.
- **Evidence artifact:** the `clap-validator` terminal summary, the `pluginval`
  `SUCCESS` line, and the plugin CTest output.

## Result (2026-11-04)

- The CLAP target configures and builds with JUCE 8.0.9 and the pinned
  `clap-juce-extensions` commit. CLAP 1.2.7 is linked.
- `clap-validator` moved from 21 passed and 12 failed to 33 passed and 0 failed.
- The parameter default failure was fixed by giving `fold_type` a 0..1 APVTS
  range and clamping it to the manifest maximum in `syncParams`.
- The three state reproducibility tests pass after `setStateInformation`
  requests a parameter rescan.
- `pluginval` passes in GUI mode with the editor open and in headless mode with
  GUI tests skipped.
- `plugin_smoke` now proves a full 313-parameter state round trip, not only one
  parameter.
- The remaining warning is in the wrapper state loader, not in the processor.

## Risks and fallback

- **Assumptions/open research:** the pinned wrapper remains compatible with
  future JUCE updates. The warning may disappear when the wrapper starts
  returning a real load result.
- **Safe experiment and stop criterion:** load a saved state in a second CLAP
  instance and compare all 313 values. Stop if any value differs.
- **Smaller alternative:** ship VST3 only and keep CLAP behind `P1_BUILD_CLAP`.
  The current default builds both.
- **Rollback:** remove the `FetchContent` block and the
  `clap_juce_extensions_plugin` call. The VST3, standalone, engine and banks are
  unchanged.
