# Porting a synth to a plugin

This is the loop the Type P.fm1 plugin used. It turned a working firmware into a
VST3 and CLAP plugin without changing the 44.1 kHz sound. Use it when a synth is
stable enough that the risk is the host, not the DSP.

## Order

Do not start with the editor. Do not start with the plugin format. Start with the
invariant that is hardest to fix later.

1. **Instance-safe engine state.** No mutable file-scope state in the generated
   DSP, the preset store, or the MIDI path. Two engine objects in one process must
   render the same bytes as two separate processes. If this fails, stop. A plugin
   that shares state is not a plugin.
2. **A host-free engine harness.** Build a small C++ seam over the generated C
   and test it without JUCE. Prove bit-exact parity with the firmware host render
   for a fixed patch, note, and MIDI script.
3. **The host skeleton.** Add the plugin wrapper, the parameter tree, the audio
   callback, the MIDI feed, and state save and load. Keep the editor generic.
4. **The editor.** Design tokens, fonts, pages, the snapshot test. Only now.
5. **Presets and banks.** Reuse the device record pack and unpack functions. Do
   not write a second layout in C++. Round-trip every record.
6. **Rate adaptation.** Keep the core at its native rate. Resample at the output
   boundary only. At the native rate the bridge must be an exact bypass with zero
   reported latency.
7. **Formats and hosts.** VST3 first. CLAP behind a build flag. AU later. Run the
   native validators, then two real DAWs per platform.
8. **Packaging.** The source is part of the product. See the licence section.

## Invariants

- Core rate is bit-exact. Any change that alters it is a regression, not a
  port.
- Every parameter in the manifest is exposed. No orphans, no duplicates, no
  hand-written lists. Generate the parameter table from the manifest.
- State round-trips all parameters and both preset banks. A sample is not enough.
- Device record functions are the only record format. A C++ copy will drift.
- State version moves only when the format changes. Read it when the format
  changes.
- Host automation is read at a fixed control block. Say so in the contract. Do
  not claim sample accuracy the code does not have.
- MIDI is quantised to the control block. Test the offset behaviour as well as
  the block start.
- Editor never owns audio state. It reads scope rings and writes parameters.
- Wordmark is all Zen Dots. Do not bundle the brand font. Ship only the OFL
  fonts whose licence texts travel with them.

## Evidence ladder

Each rung is a test, not a promise. Write it before the code.

| Rung | Evidence |
| --- | --- |
| Engine parity | The plugin engine matches the firmware render, sample for sample. |
| Instance isolation | Two instances do not share state. |
| Parameter coverage | Every manifest id maps to one host parameter and one engine id. |
| State round trip | Save, reload, compare every parameter and both banks. |
| Rate bridge | Native rate is exact. Other rates meet the alias and latency budget. |
| MIDI parity | The same MIDI script produces the same notes, bends, and CC changes. |
| Editor snapshot | Every page and dialog renders at 1x and the controls are reachable. |
| Validators | `pluginval` and `clap-validator` pass at the agreed strictness. |
| DAW matrix | Two real hosts per platform load and render a one-note project. |
| Stress | Extreme parameters, a MIDI storm, state fuzz, and rate changes stay finite. |
| Licence | The binary's obligations and the source path are in `LICENSING.md`. |

Record the exact numbers. "Passed" is not evidence. A frame count, a peak, an RMS,
a hash, a validator summary, and a host name are evidence.

## Failure patterns and what they taught

- **Shared static state in the generated DSP.** The first port attempt changed a
  second instance. Fix the ownership before writing the wrapper.
- **A linear resampler that sounded fine in a DAW.** It passed a smoke test and
  failed a spectral test. Replace it with a windowed-sinc polyphase kernel and
  measure images, THD, passband ripple, and latency.
- **A zero-range host parameter.** JUCE rejects `AudioParameterInt` with
  `min == max`. Give the parameter a 0..1 host range and clamp to the manifest
  range in the sync step.
- **A CLAP wrapper that reports success on random state bytes.** It is an upstream
  wrapper warning. Do not fake a valid state to silence it. Document it and keep
  the processor rejection.
- **GCC attributes and volatile casts reaching MSVC.** Add a compatibility header
  rather than editing generated firmware C. Keep the Windows CTest target green.
- **A headless DAW that cannot be automated.** Zrythm needed a GUI session. Carla
  has a documented no-gui mode, a JACK backend, and an OSC control API. Ardour
  exports a session headlessly. Use tools with a scriptable path.
- **JACK that cannot allocate shared memory in a container.** Set
  `--shm-size=512m`. Record it in the runner and the compose file as well as a
  shell history.
- **A licence assumption that was wrong.** JUCE 8 is AGPL-3.0-only or commercial,
  not GPLv3. Check the actual licence file at the pinned tag before the first
  release, not after the binaries exist.
- **A build artefact copied outside the repo.** Keep build outputs under the
  git-ignored `build/` tree. Stage release bundles from `publish`, never from a
  hand-copied folder.

## Contract

Write one `plugin/feature-contract-<milestone>.md` per milestone. Each one states
the feature, the user-visible behaviour, the platform and HAL changes, the data
and state impact, the MIDI and clock impact, the allowed dependencies, the test
vector, the tolerance, the evidence artefact, the risks, and the rollback. The
template is `templates/feature-contract.md`.

A milestone is done when the contract's evidence exists and the full gate is
green. It is not done when the build links.

## Packaging and licence

A plugin binary is a distribution. Before you publish one:

- Put the complete source in the publish tree, including the host glue, the
  generated DSP, the build files, and the exact dependency pins.
- Check the licence of every linked dependency at the pinned version. JUCE,
  VST3, CLAP, and the wrapper have different terms.
- If the host framework is AGPL, say so in `LICENSING.md` and provide the
  corresponding source. A link to a moving branch is not a pin.
- Keep build artefacts out of git. Stage release bundles from `umetate publish`
  and attach the source archive to the same release.
