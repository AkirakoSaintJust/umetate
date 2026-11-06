# Type P.fm1 plugin plan

Status: milestones 0 to 7 are done, as of 2026-11-04. The JUCE VST3, CLAP and
standalone builds compile on Linux and Windows, render audio, accept MIDI and save
state. The editor, the 64 multi and 128 part banks, and the 32-tap output rate
bridge are in, and the VST3 and CLAP artefacts pass their validators on both
platforms. REAPER renders the Windows VST3 and CLAP builds byte-identically whilst
Renoise loads the Windows VST3 and renders a one-note project, so the Windows DAW
matrix is done, whilst the Docker image adds Ardour and Carla, and the `linux_daws`
CTest covers the Linux DAW matrix. Milestone 7 adds the generator, the three
`umetate plugin-*` commands, and the project template. The macOS build and the AU
target remain open.

This is the plan for the optional JUCE build path in umetate, which is a reusable
plugin host plus a generated `type-p-fm1` project, and the visual language is in
`design/README.md`, the JUCE mapping is in `design/juce.md`, and the firmware
parameter manifest is `firmware/gen/params.json`.

## 1. Scope

Build a real DAW plugin from the same generated DSP that runs on the FM-1, so the
plugin is that engine behind a desktop editor.

In scope:

- VST3 and standalone on Windows, macOS and Linux.
- CLAP through a pinned `clap-juce-extensions` wrapper on the same three
  platforms.
- AU on macOS as a later addition.
- All parameters in the generated manifest.
- The three-page editor from the mockup.
- Device-compatible preset banks.
- 44.1 kHz engine core with output-only resampling to the host rate.
- GPL-3.0-only source, matching umetate. The distributed binary also carries
  JUCE 8's AGPL-3.0-only terms for the JUCE part.

Out of scope for the first release:

- Audio input, sidechain, or an effect version.
- Device flashing or firmware updates from the plugin.
- A sample-accurate automation promise beyond the engine's 32-sample control block.
- Bundling the Digital Desolation Plus brand font. The wordmark is all Zen Dots,
  so the brand font is unused and stays out of the binary.

## 2. Decisions

| # | Decision | Reason |
| --- | --- | --- |
| P1 | Reuse the generated DSP | The firmware engine and the plugin share the same DSP. No C++ reimplementation of the voice graph. |
| P2 | Add instance-safe engine state before the plugin | The generated DSP currently has 332 file-scope statics. Two plugin instances in one process would share them. |
| P3 | Expose every manifest parameter | The host owns automation and state. The UI may hide some behind target selectors. |
| P4 | Apply parameter changes at the 32-sample control block | Matches the device control rate. Sample-accurate automation is a later refinement. |
| P5 | Reuse `synth_midi` | Note, sustain, panic, bend and the generated CC map stay identical to the device. |
| P6 | 44.1 kHz core, resample the output only | The note table, LFO rates, delays and control block are locked to 44.1 kHz. |
| P7 | 1240 logical pixels wide, uniform scale, fixed height | The editor does not reflow. The host can scale the whole canvas. |
| P8 | VST3 first, CLAP second, AU later | VST3 is native to JUCE. CLAP needs an extra wrapper. |
| P9 | GPL-3.0-only source and OFL fonts | The source stays GPL-3.0-only. JUCE 8 is AGPL-3.0-only or commercial, so a distributed plugin binary carries the AGPL terms for JUCE. |
| P10 | Optional host-native build | The Docker firmware gate stays unchanged. The plugin build is separate. |
| P11 | Device-compatible preset banks | 64 multi patches and 128 single-part slots, using the existing record format. |
| P12 | Active part is UI state, not a DSP parameter | It chooses which part the editor shows. Both parts stay addressable by automation. |

## 3. Parameter count

The generated manifest is the authority, and it currently contains **313**
parameters:

| Group | Count | Notes |
| --- | --- | --- |
| per-part timbre | 134 × 2 = 268 | `SYNTH_N_PARAMS` is 134. Operators, envelopes, LFOs, pitch envelope, algorithm, voice mode, part tune. |
| global | 35 | Filters, filter envelopes, wavefolder, key and velocity follow, key and velocity switches. |
| per-part routing | 5 × 2 = 10 | Channel, keyzone low, keyzone high, level, delay. |
| total | 313 | `SYNTH_ROUTING_BASE` is 303. |

The earlier "194 parameters" figure was a pre-manifest estimate and is retired, so
the official number is whatever `params.json` says, which the plugin generator
reads at build time.

Two details matter:

- `params.json` has 139 names ending in `.p0` and 139 ending in `.p1`. That is 134
  timbre parameters plus the 5 routing parameters for each part.
- A single-part preset stores the 134 timbre parameters, not the routing. The
  multi patch stores the routing and the part references.

## 4. Architecture

```text
host processBlock
  -> MidiBridge (host events to synth_midi_feed, at 44.1 kHz control blocks)
  -> ParamSync (APVTS raw values read at each 32-sample control block)
  -> EngineInstance (one per plugin instance)
       -> generated type_p_fm1_dsp_* functions at 44.1 kHz
       -> int32 interleaved stereo
  -> RateBridge (44.1 kHz to the host rate, bypass at 44.1 kHz)
  -> host output

EngineInstance taps
  -> ScopeFeed (lock-free)
  -> editor timer (30 Hz) for scope, spectro and the routing graph
```

Layers:

- **Generated engine.** `type_p_fm1_dsp_*` from the umetate generator. No edits.
- **Engine bridge.** C++ wrapper that owns one engine state, applies APVTS
  parameter changes and MIDI at 32-sample control blocks, and converts int32 to
  float.
- **Rate bridge.** Output-only resampler. Bypass at 44.1 kHz.
- **Parameter model.** Generated from `params.json` into APVTS and a display
  formatter.
- **Preset model.** Device record functions from `presets.c` for the banks.
- **Editor.** Reusable LookAndFeel, knobs, tiles, tabs, sliders and visualisers.
- **Generated project.** A thin configuration layer: names, page map, parameter
  map, brand line, resources.

## 5. Phase 0: instance-safe engine state

This is the blocking prerequisite, because the generated DSP declares 332
file-scope statics, including per-voice arrays, global state and the parameter
slot table. The device has one engine, so this was correct for firmware, but a DAW
can load two instances, so it is not correct for a plugin.

Required change:

- The generator emits a `type_p_fm1_state` struct containing every state field
  and the parameter storage.
- The generated functions take a `type_p_fm1_state *` argument: `reset`,
  `render`, `note_on`, `note_on_ch`, `note_off`, `all_notes_off`, `set_bend`,
  `lit`, `quiet`, `set_param`, `get_param`, `tap`.
- The parameter slot table becomes a per-state lookup, for example an offset
  table applied to the state base.
- `gen/glue.h` keeps the current firmware API by owning one static instance and
  forwarding to the new functions. The app, the web lab and the host tests keep
  their current calls.
- The firmware build places the single instance in the CPU1 section, as the
  statics are placed today.
- The state size is reported by the generator so the plugin can allocate it.

Exit evidence:

- Device build is byte-identical for a fixed note and patch script.
- Host DSP test is sample-identical.
- Two state instances in one process play two different patches at once with no
  cross-talk.
- State size and instructions per sample stay within the current budget.
- The web lab still builds and matches the host.

This is a generator change that reaches beyond the plugin, so it gets its own
feature contract and its own commit.

Milestone 0 status: **done**, because the generated engine exposes
`type_p_fm1_state` and the `_s` API. The legacy API wraps one static instance, so
the firmware, the web lab and the existing host tests keep their calls. The old
and new host renders of the type-p-fm1 script are byte-identical, two states stay
isolated, the full generator suite passes, the web parity gate is exact, and the
target package builds with the Docker/JieLi toolchain, whilst the host A/B is
slightly faster. It runs at 120.7 us before and 115.1 us after per `render(256)`.
Physical device acceptance and timing remain blocked.

## 6. Engine bridge

C++ class, one per plugin instance:

```cpp
class Engine {
public:
    Engine();
    void reset();
    int setParam(uint32_t id, int32_t value);
    int32_t getParam(uint32_t id);
    void noteOn(uint32_t note, uint32_t velocity, uint32_t channel);
    void noteOff(uint32_t note);
    void allNotesOff();
    void setBend(uint32_t q16);
    void render(int32_t* out, uint32_t frames);
    uint32_t lit(uint32_t base);
    bool quiet();
    const int32_t* tap(uint32_t channel);
private:
    std::unique_ptr<type_p_fm1_state> state_;
};
```

Rules:

- The audio thread never allocates, locks, touches files or calls into the UI.
- Parameter changes are read from the APVTS atomic raw values at each 32-sample
  control block. The message thread does not write engine state directly.
- MIDI events apply at the 32-sample control block that contains their 44.1 kHz
  sample position. Note and bend events apply at that boundary. CC events go
  through `synth_midi_feed`.
- The engine renders int32 interleaved stereo. Convert with `1/32768.0f`.
- All-zero input is silence. The engine has no audio input.
- Two instances share only read-only tables.

## 7. Audio and rate bridge

- Core always runs at 44.1 kHz.
- Host may run at 44.1, 48, 88.2, 96, 176.4 or 192 kHz.
- At 44.1 kHz the bridge is bypassed and the output is bit-exact with the
  firmware host render.
- At other rates a 32-tap Kaiser-windowed sinc polyphase resampler converts the
  output. It uses 1024 phases, Kaiser beta 8.6 and a cutoff at the lower of the
  core and host Nyquist. The core is never resampled on input.
- The bridge consumes 44.1 kHz frames and produces host frames. It handles block
  sizes from 32 to 1024 frames.
- Editor and visualisers always run on the 44.1 kHz timeline.
- Filter group delay is 15.5 core samples. The reported host latency is 17
  samples at 48 kHz, 34 at 96 kHz and 67 at 192 kHz. At 44.1 kHz the bypass
  reports zero.
- The 32-sample control block is part of the instrument and is not compensated.
- Measured with a 20 kHz core tone: the 20 kHz gain is -0.45 dB. The image
  rejection is -110 dB at 48 kHz and -25.4 dB at 96 and 192 kHz. THD is about
  -25 dB. The 1 kHz and 10 kHz gains are flat. The near-Nyquist 96 and 192 kHz
  result is the expected limit of the 32-tap kernel. Raising the tap count is
  the next quality step if a stricter budget is set.

## 8. MIDI

Use the device MIDI handler so the behaviour does not fork.

- Add `synth_midi_feed(ctx, status, data1, data2)` to `synth_midi.c`. The existing
  `synth_midi_poll` becomes a loop over `midi_get` that calls it.
- The processor feeds `synth_midi_feed` directly from the host `MidiBuffer`. The
  `midi_get` shim exists only so `synth_midi.c` links outside the firmware app.
- Note on and note off go through the generated `note_on_ch` and `note_off`, so
  channel to part routing matches the device.
- Sustain, panic, pitch bend and the generated CC map match the device.
- Program change selects a multi-patch slot after the preset model lands.
- Clock and transport are ignored by the engine.
- Events are applied at 44.1 kHz sample offsets, split into control blocks.

## 9. Editor

Use the tokens and components from `design/`.

Milestone 3 implements:

- `plugin/tools/gen_tokens.py` generates `UiTokens.h` from `design/tokens.json`.
  The JUCE editor reads only that header for colours, type sizes and metrics.
- `DotGothic16` and `Zen Dots` are bundled with `juce_add_binary_data` under the
  SIL Open Font License. The wordmark is all Zen Dots (`type P.fm1`), and the
  brand font is not bundled.
- The editor canvas is fixed at 1240 by 985 logical pixels and scales uniformly
  to the host window. The host cannot reflow the pages.
- Pages: patch settings, operators and fx / mod.
- The active part selector is UI state. The patch page shows both parts. The
  operators page binds to the active part. The fx / mod page uses the active
  part for the key and velocity targets.
- The header algorithm block shows the active part's algorithm. Clicking opens
  the eight-tile picker. The mouse wheel cycles the algorithm without opening
  the picker.
- The output scope and spectro read the host output. The four operator scopes
  and spectros read the operator taps. The two part scopes and spectros read the
  part carrier taps. The audio thread fills lock-free scope rings.
- The key follow and velocity follow are separate cards with on switches, target
  selectors and wipe buttons. The target parameters remain host-automatable.
- The operator envelope puts R1 to R4 on one row and L1 to L3 on the next.
- Dialogs: the algorithm picker, patch rename and part rename. The part menu
  offers rename, copy, paste and init.
- `plugin_editor_snapshot` renders the patch, operators, fx / mod, algorithm
  picker, rename dialog, active part 2 and the 50 percent scale to PNG. It runs
  under `xvfb-run` in the Linux test.
- Text entry, keyboard focus and the cut-polygon tabs follow the design language.
- No filler copy.

The patch and part banks are in, and the editor stores patch and part names as UI
state in the plugin state blob. The rename dialog enforces the device record limit
of 15 characters.

## 10. Presets and state

The plugin state is a versioned blob:

```text
version
APVTS state (313 parameters)
ui_active_part, ui_page
multi bank (64 records, base64)
part bank (128 records, base64)
current multi slot, part source slots
```

- The banks use `preset_multi_pack`, `preset_multi_unpack`,
  `preset_part_pack` and `preset_part_unpack` from `presets.c`. The byte layout
  stays device-compatible.
- The plugin state owns an in-memory bank. It does not write files on the audio
  thread.
- The patch browser edits the 64 multi slots. The part save and load dialogs edit
  the 128 single-part slots.
- DAW presets save the whole state. The bank size is small enough for one state
  blob. The part bank is 128 x 557 bytes and the multi bank is 64 x 63 bytes.
- Import and export of a device preset bank through SysEx is a later milestone.
- The plugin does not rewrite a device bank. A save into a used slot opens a
  confirmation dialog before overwriting. Device bank import and export will
  require explicit confirmation.
- Names use the device record limit of 15 characters.

## 11. Build and toolchain

The plugin build is optional and host-native, and `deep-check --all` does not
build JUCE, so a plugin change needs the explicit plugin commands below. The Linux
container is the pinned host for the Linux plugin build and its CTest suite.

Repository shape:

```text
plugin/
  CMakeLists.txt
  README.md              this plan
  feature-contract-*.md  the milestone contracts
  engine/                the engine bridge, MIDI bridge, rate bridge
  juce/                  the JUCE target, editor pages, bundled fonts
  preset/                record wrappers
  tools/                 parameter/token generators + alias header templates
  tests/                 C++ tests, snapshots and validation scripts
  ui/                    tokens, LookAndFeel, components
```

A generated project is written to `build/plugin/<cname>/` rather than into this
tree, and it holds the synth's rendered C under `gen/`, a `P1Project.cmake` with
the identity, a thin `CMakeLists.txt`, and a README. `plugin/` keeps the
checked-in Type P.fm1 defaults for a plain `cmake -S plugin` build.

Toolchain:

- CMake 3.22 or newer, C++20.
- JUCE 8 pinned by tag and commit, fetched with `FetchContent` or supplied with
  `JUCE_DIR` for offline builds.
- CLAP through `clap-juce-extensions` pinned to the MIT-licensed main commit
  `7adee3a1bd4684d4caa5601100e364abccff4b4d`. The `0.26.0` tag predates the JUCE 8
  Linux message thread path.
- Windows: MSVC 2022 or newer. JUCE 8 rejects MinGW, so the MSYS2 gcc path is
  not a supported Windows build. `plugin/engine/msvc_compat.h` maps the firmware
  GCC attributes away for MSVC and `firmware/hal/fm1_ipc.h` uses a portable field
  copy instead of a volatile struct cast.
- macOS: Xcode command line tools, universal binary if the build host allows it.
- Linux: ALSA and X11 development packages, plus the usual JUCE dependencies.
- Linux DAWs: the Docker image carries Ardour 8.12 and Carla 2.6.0-alpha1.
  Ardour renders a session with `ardour8-export`. Carla runs headless through
  JACK and its OSC API, and renders both VST3 and CLAP. The `linux_daws` CTest
  drives both.

CLI:

- `umetate plugin-generate --synth examples/type-p-fm1`
- `umetate plugin-build --synth examples/type-p-fm1`
- `umetate plugin-check --synth examples/type-p-fm1`

`plugin-generate` renders `build/plugin/<cname>/` and `--check` compares that tree
without writing, whilst `plugin-build` renders the same files, configures
`<out>/build`, builds, and runs ctest. `plugin-check` verifies the generated files
and runs ctest in the existing build tree. The plugin identity comes from
`plugin.json` in the synth project, and `--product-name`, `--bundle-id`,
`--manufacturer-code`, and `--plugin-code` override it for a one-off build.

The generated project includes its own `P1Project.cmake` before it adds `plugin/`
as a subdirectory, so `P1_SYNTH_GEN`, `P1_SYNTH_CNAME`, `P1_PRODUCT_NAME`,
`P1_PLUGIN_TARGET`, `P1_BUNDLE_ID`, `P1_MANUFACTURER_CODE`, `P1_PLUGIN_CODE`, and
`P1_STATE_TREE_ID` come from the synth, not from the checked-in defaults. The
engine and the editor talk to `P1Synth.h` and `P1Product.h`, which are generated
at configure time from `plugin/tools/*.in`. The rendered C is stored in the
project's `gen/`, and the fixed `firmware/gen/math_tables.h` stays in the source
tree and is included after the project's `gen/`.

## 12. Verification ladder

Plugin work adds a new evidence layer, so the firmware layers keep their evidence.

1. **Parameter map coverage.** Every id in `params.json` maps to exactly one page
   control or to a documented advanced group. No duplicate and no orphan. This is
   a Python test over `param-map.json` and `params.json`.
2. **State isolation.** Two engine instances in one process with different
   patches produce the same output as two separate processes.
3. **44.1 kHz parity.** A fixed note, patch and MIDI script renders
   sample-for-sample identical to the firmware host render.
4. **Rate bridge.** At 44.1, bypass is exact. At 48, 96 and 192, measure THD,
   alias rejection, passband ripple and reported latency.
5. **MIDI parity.** The same MIDI file produces the same parameter changes, note
   allocation and bend in the device host and the plugin engine.
6. **State round trip.** Save, reload and compare all 313 parameters and both
   banks. Automation writes reach the engine at the next control block.
7. **GUI.** A snapshot of each page and dialog at 1x. Manual keyboard, scroll,
   rename and mute checks on each platform.
8. **Plugin validation.** `pluginval` for VST3 and `clap-validator` for CLAP at
   several strictness levels. Load in at least two DAWs per platform. On Linux
   the `linux_daws` CTest uses Ardour for a headless VST3 render and Carla for
   headless VST3 and CLAP renders.
9. **Performance.** 20 voices at 44.1 and 96 kHz, 32 to 1024 frame blocks. Record
   the real-time factor and the worst block.
10. **Licensing.** GPL-3.0-only source, JUCE 8 AGPL-3.0-only or commercial for
    the binary, OFL font files and notices, no brand font in the binary.
11. **Stability.** Every parameter at both ends of its range, a full polyphony
    burst, a deterministic MIDI storm, zero-frame and mono blocks, rate changes,
    and truncated or bit-flipped state stay finite and do not crash.

## 13. Milestones

| # | Milestone | Exit |
| --- | --- | --- |
| 0 | Instance-safe engine state | done, physical device blocked |
| 1 | Engine bridge harness, no JUCE | done |
| 2 | JUCE host skeleton | done |
| 3 | Editor | done |
| 4 | Presets and banks | done |
| 5 | Rate bridge | done |
| 6 | CLAP and platform matrix | Linux and Windows DAW matrices done, macOS open |
| 6b | Stability sweep | done |
| 7 | Generator and CLI | done |

Milestone 0 is firmware work and can start before any JUCE dependency is added.

Milestone 1 is done, because `plugin/` builds a JUCE-free `p1_engine` library and
an `engine_parity` test. The engine matches the firmware render bit-exactly, two
instances stay isolated, a MIDI script matches the `synth_midi_poll` reference,
and sustain state is per bridge. The full `deep-check --all` remains green.

Milestone 2 is done, because `plugin/juce` builds a VST3 and a standalone app
against JUCE 8.0.9. The processor exposes the 313 manifest parameters through the
APVTS, applies automation at the 32-sample control block, feeds MIDI through
`synth_midi_feed`, renders the 44.1 kHz core bit-exactly, and saves and restores
the parameter state. The generic JUCE editor was the Milestone 2 placeholder. The
48 kHz path used the temporary linear RateBridge at that point, so it rendered
audio but was not release quality. The `plugin_smoke` CTest checks the parameter
count, unique ids, contiguous engine ids, bit-exact 44.1 kHz output, an automation
write at the 32-sample control block, a MIDI offset at its control block and a
state round trip. `engine_parity` remains green.

Milestone 3 is done, and the generic JUCE panel is replaced by the designed
editor. `UiTokens.h` is generated from `design/tokens.json`, the two OFL fonts are
bundled, and the three pages match the v1.1 design. The editor scales the whole
1240 by 985 canvas uniformly. The header algorithm block opens the picker
and cycles on the wheel. The patch, operator and part visualisers read the
lock-free scope rings, the key and velocity follow cards have real on switches and
wipe buttons, and the operator envelopes use the two-row rate and level layout.
The algorithm picker and rename dialogs are in, and `plugin_editor_snapshot`
renders the pages and dialogs under Xvfb, so the PNGs are the visual evidence. The
plugin state now stores patch and part names plus the active part and page.

Milestone 4 is done, and the plugin has 64 multi slots and 128 part slots. The
banks reuse the firmware `presets.c` pack and unpack functions, so a part record
is 557 bytes and a multi record is 63 bytes. Empty slots are `0xFF` and corrupt
records are skipped, whilst the plugin state version is 2 and restores both
banks, the current multi and the part source slots. The patch button opens the
64-slot browser, the part menu opens the 128-slot browser in save or load mode,
and a save into a used slot opens a confirmation dialog before overwriting. A
multi save uses the saved part source slots and puts a part with no source into a
free slot first. `preset_smoke` proves the device record round trip, and
`plugin_smoke` proves the bank state round trip. `plugin_editor_snapshot` saves and
loads a part and a multi through the editor.

Milestone 5 is done, because the temporary linear rate bridge is replaced by the
32-tap polyphase resampler. The 44.1 kHz path is still bypassed and bit-exact,
with zero reported latency. At 48, 96 and 192 kHz the bridge reports 17, 34
and 67 host samples. `rate_bridge_test` measures the passband, images, THD,
latency and block sizes from 32 to 1024, and the 20 kHz image rejection is -110 dB
at 48 kHz and -25.4 dB at 96 and 192 kHz, which is the limit of the 32-tap
kernel. A longer kernel is the next quality step if a stricter budget is set.

Milestone 6 is done for the Linux and Windows builds, where the JUCE project
creates a CLAP target next to VST3 and standalone. `P1_BUILD_CLAP` defaults to ON
inside the `P1_BUILD_JUCE` path and fetches `clap-juce-extensions` at the pinned
MIT commit, and the CLAP plugin ID is `com.p1onken.typepfm1`. `clap-validator`
reports 33 passed, 0 failed, 1 warning and 10 skipped on Linux, and 32 passed, 0
failed, 1 warning and 11 skipped on Windows. The warning is the wrapper returning
success for random state bytes even though the processor rejects them, and the
plugin does not crash, though the wrapper gives it no way to report the rejection.
`pluginval` passes strictness level 5 both with the editor open and with GUI tests
skipped on both platforms, and the VST3 checks cover 44.1, 48, 96 and 192 kHz and
blocks from 32 to 1024.

Milestone 6b is done, because `plugin_stability` drives every manifest parameter
to its minimum and maximum, holds 256 notes at once, runs a deterministic
9600-event MIDI storm, sends a zero-frame block and a mono block, walks the sample
rate from 44.1 to 192 kHz and back, fuzzes the state with 200 truncated and
bit-flipped blobs, and checks the voice tail decays. Every sample stays finite and
the reported latency matches each rate, and the test passes in 0.14 seconds in the
Linux container. It is a host-side test, so it does not stand in for a device or a
DAW.

REAPER 7.84 loads the Windows VST3 and CLAP builds, and a one-note project renders
88200 frames at 44100 Hz from each format, so the two WAV files are byte
identical. The VST3 bundle was installed in
`C:\Program Files\Common Files\VST3`, where Renoise 3.5.4 scans. Renoise
loaded `P1Onken: Type P.fm1` and rendered a one-note project to 39200 frames at
44100 Hz, 24-bit stereo, peak 0.225197 and RMS 0.105559. The Windows DAW matrix
now has REAPER and Renoise.

The Docker image carries Ardour 8.12 and Carla 2.6.0-alpha1, and the `linux_daws`
CTest copies the VST3 and CLAP to an isolated `$HOME`, scans them with Ardour's
VST3 scanner, builds a one-note Ardour session and exports it headlessly, then
starts a dummy JACK server, runs Carla headless, adds each plugin through Carla's
OSC API, sends a MIDI note and records the plugin output with `jack_rec`. The
Ardour render is 88200 frames at 44100 Hz, 24-bit stereo, peak 0.609467 and RMS
0.196450. The Carla VST3 and CLAP renders are 132300 frames at 44100 Hz,
24-bit stereo, peak 0.609467. The Linux DAW matrix is now automated, and the macOS
build and AU remain open.

Milestone 7 is done, because `umetate/_synthgen.py` is the single generation step
behind `umetate build --synth` and `umetate plugin-generate`, so the firmware and
the plugin render the same C from one `patch.json`, `panel.json`, and `app.c`. The
fixed `type_p_fm1_*` calls in the bridge are gone.
`plugin/tools/P1Synth.h.in` maps `P1_STATE`, `P1_RESET`, `P1_SET_PARAM`, and the
rest to the synth's generated names, and `P1Product.h.in` carries the product name
and the APVTS state tree id. `plugin-build` renders, configures, builds, and runs
ctest. `plugin-check` verifies the generated tree and runs ctest in the existing
build tree. The Python tests cover the generate/check round trip and the identity
validation. `publish` copies `plugin.json` into `src/` and stages only the real
artefacts, not the Linux DAW test's isolated copies. It also writes `RELEASES.md`,
`SHA256SUMS`, and `release.json`, which cover the firmware and the plugin
archives. The plain `cmake -S plugin` build keeps the checked-in Type P.fm1
defaults, so the existing validator and DAW evidence does not depend on the
generated project. The generated project built in
`build/plugin/type_p_fm1/build` and passed the same eight CTest cases as the plain
tree. `plugin-build` defaults to four jobs because an unbounded compile can
exhaust a small Docker VM.

Plain checkout, bridge only:

```sh
umetate build --synth examples/type-p-fm1   # regenerate firmware/gen first
cmake -S plugin -B build/plugin
cmake --build build/plugin
ctest --test-dir build/plugin --output-on-failure
```

Generated project, JUCE VST3, CLAP and standalone build:

```sh
umetate plugin-build --synth examples/type-p-fm1
```

That writes `build/plugin/type_p_fm1/` and builds in
`build/plugin/type_p_fm1/build`, and `umetate plugin-check` re-verifies the
generated files and reruns ctest. Pass `--deps-dir <juce build>/_deps` to
`plugin-build` to reuse an existing JUCE and CLAP checkout instead of fetching them
again. `--jobs` defaults to 4, so raise it on a large host and lower it if the
Docker VM runs out of memory.

JUCE VST3, CLAP and standalone build:

```sh
cmake -S plugin -B build/plugin-juce -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON
cmake --build build/plugin-juce
ctest --test-dir build/plugin-juce --output-on-failure
```

On Windows, run this from a Developer Command Prompt or after
`vcvars64.bat`, with Ninja and CMake from the Build Tools on `PATH`:

```bat
cmake -S plugin -B build\plugin-juce -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON
cmake --build build\plugin-juce --parallel 8
ctest --test-dir build\plugin-juce --output-on-failure
```

`P1_BUILD_CLAP` defaults to ON when `P1_BUILD_JUCE` is ON, and the CLAP wrapper is
fetched at the pinned commit. In a plain checkout the artefacts are under
`build/plugin-juce/juce/type_p_fm1_artefacts/Release/VST3`,
`build/plugin-juce/juce/type_p_fm1_artefacts/Release/CLAP` and `Standalone`. A
generated project puts them under `<out>/build/p1plugin/juce/` with the same
`type_p_fm1_artefacts` leaf. On Windows the same paths use backslashes and the
VST3 bundle contains `Contents\x86_64-win`. The editor snapshots are under the
build tree's `juce/snapshots`, where the `plugin_editor_snapshot` CTest uses
`xvfb-run` when it is available. `plugin_editor_snapshot_diff` compares the PNGs
with the committed Linux golden set.

`plugin_stability` is the edge-case sweep, and it sets every manifest parameter to
both ends of its range, fires 256 simultaneous notes, runs a deterministic
9600-event MIDI storm, sends a zero-frame block and a mono block, walks the
sample rate from 44.1 to 192 kHz and back, fuzzes the state with truncated and
bit-flipped blobs, and checks the voice tail decays. It needs no device and no
DAW:

```sh
ctest --test-dir build/plugin-juce -R plugin_stability --output-on-failure
```

`plugin_editor_snapshot_diff` is the visual gate, which compares the ten editor
PNGs with `plugin/tests/snapshots/linux-x86_64` and fails on a missing, extra,
or changed image. The gate runs only in the Linux container. Font rasterisation
differs on other hosts. When the UI is supposed to change, review
the diff overlays under `build/plugin-juce/juce/snapshot-diff`, then accept the
change deliberately:

```sh
python3 plugin/tools/snapshot_check.py --update \
  --actual build/plugin-juce/juce/snapshots \
  --golden plugin/tests/snapshots/linux-x86_64
```

Commit the new golden PNGs, `manifest.json`, and the code in the same commit.

`umetate tokens` is the token gate, which checks `design/tokens.css` against
`design/tokens.json`, runs `gen_tokens.py` and checks that every colour, font,
size and space token is in the generated `UiTokens.h`, checks that
`firmware/gen/theme.h` matches `firmware/theme.json`, and scans the plugin and
firmware sources for raw colours, raw font families, raw `RGB()` calls, and
undefined `THEME_*` macros. The firmware palettes and chrome colours are now in
`firmware/theme.json`, so `gfx.c` has no colour literals. After editing
`firmware/theme.json`, regenerate the header with
`umetate theme write firmware/theme.json firmware/gen/theme.h`.

```sh
umetate tokens
```

To stage release bundles, run `umetate publish --plugins --vendor-deps
build/plugin-juce/_deps`. The publish tree carries the plugin source, the exact
dependency pins in `DEPENDENCIES.md`, and the zipped VST3 and CLAP builds under
`plugins/<platform>/`.

Build outputs stay in the git-ignored `build/` tree, so they are not committed to
this repo and they are not copied to a folder outside it. The publish output is
the release staging area, and the source archive and binaries should travel in
the same GitHub release.

Validator commands on Linux, with the plugin paths from the build tree:

```sh
xvfb-run -a clap-validator validate --only-failed \
  "build/plugin-juce/juce/type_p_fm1_artefacts/Release/CLAP/Type P.fm1.clap"
xvfb-run -a pluginval --validate \
  "build/plugin-juce/juce/type_p_fm1_artefacts/Release/VST3/Type P.fm1.vst3" \
  --strictness-level 5
```

On Windows the same checks run without Xvfb:

```powershell
clap-validator.exe validate --only-failed `
  "build\plugin-juce\juce\type_p_fm1_artefacts\Release\CLAP\Type P.fm1.clap"
pluginval.exe --validate `
  "build\plugin-juce\juce\type_p_fm1_artefacts\Release\VST3\Type P.fm1.vst3" `
  --strictness-level 5
```

On Linux, install `pkg-config`, `libasound2-dev`, the X11, Xrandr, Xcursor,
Xinerama, Xcomposite and Xrender headers, freetype and fontconfig, and the
OpenGL headers. JUCE 8.0.9 is fetched at configure time.

The Docker image already carries those packages plus Ardour, Carla, JACK, Xvfb
and the Qt runtime, so build it with `docker/build.sh`. `ctest` then runs
`linux_daws` automatically when `ardour8-export`, `carla-jack-single` and
`jack_rec` are on `PATH`. The test keeps its own `$HOME` under the build tree
and does not touch the host plugin folders. The container needs
`--shm-size=512m` for JACK, which `umetate/runner.py` and `docker/docker-compose.yml`
set.

Platform matrix:

| Platform | VST3 | CLAP | Standalone | Evidence |
| --- | --- | --- | --- | --- |
| Linux x86-64 | built, pluginval pass, Ardour and Carla render | built, clap-validator pass, Carla render | built | Linux container, 2026-11-04 |
| Windows x86-64 | built, pluginval pass, REAPER and Renoise render | built, clap-validator pass, REAPER render | built | Windows host, MSVC 19.51, 2026-11-04 |
| macOS arm64 and x86-64 | not built | not built | not built | no macOS runner |

The Windows VST3 and CLAP builds render equivalent one-note REAPER projects to
byte-identical WAV files, and REAPER 7.84 and Renoise 3.5.4 both load the Windows
VST3 build and render it. The `linux_daws` CTest renders the Linux VST3 in
Ardour 8.12 and renders both Linux formats in Carla 2.6.0-alpha1, so both DAW
matrices are done. The macOS rows are not evidence of support, because they need
a native build, `pluginval` and two DAWs per platform before they move to pass. AU
remains a later macOS target.

The bridge build is host-native and optional, and it stays separate from the
firmware Docker gate. The generated `firmware/gen` must exist before CMake
configures.

## 14. Risks

| Risk | Trigger | Response |
| --- | --- | --- |
| State refactor changes the sound | Any sample difference in the parity test | Stop, compare the generated state access, fix before plugin work |
| Two instances still share state | A second instance changes the first | Treat as a Milestone 0 failure |
| JUCE fetch is unavailable | No network in the build environment | Support `JUCE_DIR` and a pinned local archive |
| CLAP wrapper rots | The extension lags JUCE | Keep VST3 as the primary target, CLAP behind a flag |
| Carla source drifts | The build fails or CLAP breaks | Keep the commit pin, rebuild the image, rerun `linux_daws` |
| JACK shared memory is too small | `jackd` cannot start in the container | Keep `--shm-size=512m` in the runner and compose file |
| Firmware C stops compiling on MSVC | GCC attributes or volatile casts reach the plugin build | Keep `msvc_compat.h` and the Windows CTest target green |
| CLAP state load reports success on invalid bytes | `clap-validator` warning | Document it, keep the processor rejection, do not fake a valid state |
| Rate bridge colors the sound | THD or alias above the budget | Raise the tap count or change the filter, never change the core rate |
| Parameter map misses a control | Coverage test fails | Fix the map, not the test |
| Device preset round trip breaks | Byte mismatch | Use the C record functions, never a C++ copy |
| Name limit surprises users | More than 15 characters typed | Show the limit in the rename dialog, keep device compatibility |
| Brand font creeps into the binary | The wordmark looks different | Keep the wordmark all Zen Dots and never bundle Digital Desolation Plus |

## 15. Open questions

- CLAP is part of the first build on Linux. VST3 remains the primary target and
  CLAP stays behind `P1_BUILD_CLAP`.
- Is AU required on macOS in the first release?
- Does the first release need device preset import and export, or only the
  in-plugin banks?
- Block-accurate automation is accepted for v1. The processor reads the APVTS at
  the 32-sample control block. A sample-accurate promise is not part of v1.
- Should the plugin expose both parts on the operators page at once, or keep the
  active-part model from the mockup?
- How should a DAW preset relate to a device multi patch when names are limited
  to 15 characters?

## 16. Handoff

Read in this order:

1. `design/README.md`
2. `design/juce.md`
3. `design/agent-workflow.md`
4. `firmware/gen/params.json`
5. `firmware/src/synth_midi.h`, `synth_runtime.h`, `presets.h`
6. `examples/type-p-fm1/patch.json`

Start with Milestone 0 rather than the editor, because a plugin that cannot run
two instances is not a plugin yet.
