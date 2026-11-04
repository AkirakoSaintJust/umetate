# Type P.fm1 plugin plan

Status: Milestone 6 done, 2026-11-04. The JUCE VST3, CLAP and standalone host
build on Linux and Windows, render audio, accept MIDI and save state. The
designed editor, the 64 multi and 128 part banks and the 32-tap output rate
bridge are in. The VST3 and CLAP artefacts pass their validators on both
platforms. REAPER renders the Windows VST3 and CLAP builds byte-identically. The
macOS build and the full two-DAW matrix remain open.

This is the plan for the optional JUCE build path in umetate: a reusable plugin
host plus a generated `type-p-fm1` project. The visual language is in
`design/README.md`, the JUCE mapping is in `design/juce.md`, and the firmware
parameter manifest is `firmware/gen/params.json`.

## 1. Scope

Build a real DAW plugin from the same generated DSP that runs on the FM-1. The
plugin is not a rewrite and not a sample pack. It is the firmware engine behind a
desktop editor.

In scope:

- VST3 and standalone on Windows, macOS and Linux.
- CLAP through a pinned `clap-juce-extensions` wrapper on the same three
  platforms.
- AU on macOS as a later addition.
- All parameters in the generated manifest.
- The three-page editor from the mockup.
- Device-compatible preset banks.
- 44.1 kHz engine core with output-only resampling to the host rate.
- GPL-3.0-only, matching umetate.

Out of scope for the first release:

- Audio input, sidechain, or an effect version.
- Device flashing or firmware updates from the plugin.
- A sample-accurate automation claim beyond the engine's 32-sample control block.
- Bundling the Digital Desolation Plus brand font until its licence is confirmed.

## 2. Decisions

| # | Decision | Reason |
| --- | --- | --- |
| P1 | Reuse the generated DSP | One engine, one sound. No C++ reimplementation of the voice graph. |
| P2 | Add instance-safe engine state before the plugin | The generated DSP currently has 332 file-scope statics. Two plugin instances in one process would share them. |
| P3 | Expose every manifest parameter | The host owns automation and state. The UI may hide some behind target selectors. |
| P4 | Apply parameter changes at the 32-sample control block | Matches the device control rate. Sample-accurate automation is a later refinement. |
| P5 | Reuse `synth_midi` | Note, sustain, panic, bend and the generated CC map stay identical to the device. |
| P6 | 44.1 kHz core, resample the output only | The note table, LFO rates, delays and control block are locked to 44.1 kHz. |
| P7 | 1240 logical pixels wide, uniform scale, fixed height | The editor does not reflow. The host can scale the whole canvas. |
| P8 | VST3 first, CLAP second, AU later | VST3 is native to JUCE. CLAP needs an extra wrapper. |
| P9 | GPL-3.0-only and OFL fonts | The repository and JUCE GPL path are compatible. |
| P10 | Optional host-native build | The Docker firmware gate stays unchanged. The plugin build is separate. |
| P11 | Device-compatible preset banks | 64 multi patches and 128 single-part slots, using the existing record format. |
| P12 | Active part is UI state, not a DSP parameter | It chooses which part the editor shows. Both parts stay addressable by automation. |

## 3. Parameter count

The generated manifest is the authority. It currently contains **313** parameters:

| Group | Count | Notes |
| --- | --- | --- |
| per-part timbre | 134 × 2 = 268 | `SYNTH_N_PARAMS` is 134. Operators, envelopes, LFOs, pitch envelope, algorithm, voice mode, part tune. |
| global | 35 | Filters, filter envelopes, wavefolder, key and velocity follow, key and velocity switches. |
| per-part routing | 5 × 2 = 10 | Channel, keyzone low, keyzone high, level, delay. |
| total | 313 | `SYNTH_ROUTING_BASE` is 303. |

The earlier "194 parameters" figure was a pre-manifest estimate and is retired.
The official number is whatever `params.json` says. The plugin generator reads it
at build time.

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

This is the blocking prerequisite. The generated DSP declares 332 file-scope
statics, including per-voice arrays, global state and the parameter slot table.
The device has one engine, so this was correct for firmware. A DAW can load two
instances, so it is not correct for a plugin.

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

- The device build is byte-identical for a fixed note and patch script.
- The host DSP test is sample-identical.
- Two state instances in one process play two different patches at once with no
  cross-talk.
- State size and instructions per sample stay within the current budget.
- The web lab still builds and matches the host.

This is a generator change, not a plugin-only change. It gets its own feature
contract and its own commit.

Milestone 0 status: **done**. The generated engine exposes `type_p_fm1_state`
and the `_s` API. The legacy API wraps one static instance, so the firmware, the
web lab and the existing host tests keep their calls. The old and new host
renders of the type-p-fm1 script are byte-identical, two states stay isolated,
the full generator suite passes, the web parity gate is exact, and the target
package builds with the Docker/JieLi toolchain. The host A/B is slightly faster,
120.7 us before and 115.1 us after per `render(256)`. Physical device acceptance
and timing remain blocked.

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

- The core always runs at 44.1 kHz.
- The host may run at 44.1, 48, 88.2, 96, 176.4 or 192 kHz.
- At 44.1 kHz the bridge is bypassed and the output is bit-exact with the
  firmware host render.
- At other rates a 32-tap Kaiser-windowed sinc polyphase resampler converts the
  output. It uses 1024 phases, Kaiser beta 8.6 and a cutoff at the lower of the
  core and host Nyquist. The core is never resampled on input.
- The bridge consumes 44.1 kHz frames and produces host frames. It handles block
  sizes from 32 to 1024 frames.
- The editor and the visualisers always run on the 44.1 kHz timeline.
- The filter group delay is 15.5 core samples. The reported host latency is 17
  samples at 48 kHz, 34 at 96 kHz and 67 at 192 kHz. At 44.1 kHz the bypass
  reports zero.
- The 32-sample control block is part of the instrument and is not compensated.
- Measured with a 20 kHz core tone: the 20 kHz gain is -0.45 dB. The image
  rejection is -110 dB at 48 kHz and -25.4 dB at 96 and 192 kHz. THD is about
  -25 dB. The 1 kHz and 10 kHz gains are flat. The near-Nyquist 96 and 192 kHz
  result is the expected limit of the 32-tap kernel. Raising the tap count is
  the next quality step if a stricter budget is set.

## 8. MIDI

Use the device MIDI handler so the behavior does not fork.

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
  SIL Open Font License. The brand font is not bundled. The `TYPE P.` prefix uses
  Arial Black, with a default bold sans fallback on systems that lack it. `fm1`
  always uses Zen Dots.
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

The patch and part banks are in. The editor stores patch and part names as UI
state in the plugin state blob. The rename dialog enforces the device record
limit of 15 characters.

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

The plugin build is optional and host-native. It does not run in the firmware
Docker image and does not change `deep-check --all`.

Repository shape:

```text
plugin/
  CMakeLists.txt
  README.md              this plan
  cmake/                 JUCE fetch, warnings, packaging
  host/                  reusable C++/JUCE code
  ui/                    tokens, LookAndFeel, components
  engine/                the engine bridge and rate bridge
  preset/                record wrappers
  type-p-fm1/            generated project
  tests/                 C++ tests and validation scripts
```

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

CLI, later phase:

- `umetate plugin-generate --synth examples/type-p-fm1 --out build/plugin/type-p-fm1`
- `umetate plugin-build --synth examples/type-p-fm1`
- `umetate plugin-check`

The first prototype may live as a plain CMake project under `plugin/`. The CLI
wraps it once the host is stable.

## 12. Verification ladder

Plugin work adds a new evidence layer. It does not replace the firmware layers.

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
   several strictness levels. Load in at least two DAWs per platform.
9. **Performance.** 20 voices at 44.1 and 96 kHz, 32 to 1024 frame blocks. Record
   the real-time factor and the worst block.
10. **Licensing.** GPL-3.0-only, JUCE GPL path, OFL font files and notices, no
    brand font in the binary.

## 13. Milestones

| # | Milestone | Exit |
| --- | --- | --- |
| 0 | Instance-safe engine state | done, physical device blocked |
| 1 | Engine bridge harness, no JUCE | done |
| 2 | JUCE host skeleton | done |
| 3 | Editor | done |
| 4 | Presets and banks | done |
| 5 | Rate bridge | done |
| 6 | CLAP and platform matrix | plugin and validators done, DAW matrix blocked |
| 7 | Generator and CLI | `plugin-generate`, `plugin-build`, `plugin-check`, template and docs |

Milestone 0 is firmware work and can start before any JUCE dependency is added.

Milestone 1 is done. `plugin/` builds a JUCE-free `p1_engine` library and an
`engine_parity` test. The engine matches the firmware render bit-exactly, two
instances stay isolated, a MIDI script matches the `synth_midi_poll` reference,
and sustain state is per bridge. The full `deep-check --all` remains green.

Milestone 2 is done. `plugin/juce` builds a VST3 and a standalone app against
JUCE 8.0.9. The processor exposes the 313 manifest parameters through the APVTS,
applies automation at the 32-sample control block, feeds MIDI through
`synth_midi_feed`, renders the 44.1 kHz core bit-exactly, and saves and restores
the parameter state. The generic JUCE editor was the Milestone 2 placeholder.
The 48 kHz path used the temporary linear RateBridge at that point, so it
rendered audio but was not release quality. The `plugin_smoke` CTest checks the parameter count,
unique ids, contiguous engine ids, bit-exact 44.1 kHz output, an automation
write at the 32-sample control block, a MIDI offset at its control block and a
state round trip. `engine_parity` remains green.

Milestone 3 is done. The generic JUCE panel is replaced by the designed editor.
`UiTokens.h` is generated from `design/tokens.json`, the two OFL fonts are
bundled, and the three pages match the v1.1 design. The editor scales the whole
1240 by 985 canvas uniformly. The header algorithm block opens the picker and
cycles on the wheel. The patch, operator and part visualisers read the lock-free
scope rings. The key and velocity follow cards have real on switches and wipe
buttons. The operator envelopes use the two-row rate and level layout. The
algorithm picker and rename dialogs are in. `plugin_editor_snapshot` renders the
pages and dialogs under Xvfb and the PNGs are the visual evidence. The plugin
state now stores patch and part names plus the active part and page.

Milestone 4 is done. The plugin has 64 multi slots and 128 part slots. The banks
reuse the firmware `presets.c` pack and unpack functions, so a part record is
557 bytes and a multi record is 63 bytes. Empty slots are `0xFF` and corrupt
records are skipped. The plugin state version is 2 and restores both banks, the
current multi and the part source slots. The patch button opens the 64-slot
browser. The part menu opens the 128-slot browser in save or load mode. A save
into a used slot opens a confirmation dialog before overwriting. A multi save
uses the saved part source slots and puts a part with no source into a free slot
first. `preset_smoke` proves the device record round trip. `plugin_smoke` proves
the bank state round trip. `plugin_editor_snapshot` saves and loads a part and a
multi through the editor.

Milestone 5 is done. The temporary linear rate bridge is replaced by the 32-tap
polyphase resampler. The 44.1 kHz path is still bypassed and bit-exact, with zero
reported latency. At 48, 96 and 192 kHz the bridge reports 17, 34 and 67 host
samples. `rate_bridge_test` measures the passband, images, THD, latency and block
sizes from 32 to 1024. The 20 kHz image rejection is -110 dB at 48 kHz and
-25.4 dB at 96 and 192 kHz. That is the limit of the 32-tap kernel. A longer
kernel is the next quality step if a stricter budget is set.

Milestone 6 is done for the Linux and Windows builds. The JUCE project creates a
CLAP target next to VST3 and standalone. `P1_BUILD_CLAP` defaults to ON inside
the `P1_BUILD_JUCE` path and fetches `clap-juce-extensions` at the pinned MIT
commit. The CLAP plugin ID is `com.p1onken.typepfm1`. `clap-validator` reports 33
passed, 0 failed, 1 warning and 10 skipped on Linux. On Windows it reports 32
passed, 0 failed, 1 warning and 11 skipped. The warning is the wrapper returning
success for random state bytes even though the processor rejects them. It does
not crash and the wrapper gives the plugin no way to report the rejection.
`pluginval` passes strictness level 5 both with the editor open and with GUI
tests skipped on both platforms. The VST3 checks cover 44.1, 48, 96 and 192 kHz
and blocks from 32 to 1024.

REAPER 7.84 loads the Windows VST3 and CLAP builds. A one-note project renders
88200 frames at 44100 Hz from each format, and the two WAV files are byte
identical. Renoise 3.5.4 is installed but only scans VST3 from
`C:\Program Files\Common Files\VST3`, which this account cannot write. The macOS
build and the full two-DAW matrix remain open.

Host bridge build:

```sh
umetate build --synth examples/type-p-fm1   # regenerate firmware/gen first
cmake -S plugin -B build/plugin
cmake --build build/plugin
ctest --test-dir build/plugin --output-on-failure
```

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

`P1_BUILD_CLAP` defaults to ON when `P1_BUILD_JUCE` is ON. The CLAP wrapper is
fetched at the pinned commit. The artifacts are under
`build/plugin-juce/juce/type_p_fm1_artefacts/Release/VST3`,
`build/plugin-juce/juce/type_p_fm1_artefacts/Release/CLAP` and `Standalone`.
On Windows the same paths use backslashes and the VST3 bundle contains
`Contents\x86_64-win`. The editor snapshots are under
`build/plugin-juce/juce/snapshots`. The `plugin_editor_snapshot` CTest uses
`xvfb-run` when it is available.

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

Platform matrix:

| Platform | VST3 | CLAP | Standalone | Evidence |
| --- | --- | --- | --- | --- |
| Linux x86-64 | built, pluginval pass | built, clap-validator pass | built | Linux container, 2026-11-04 |
| Windows x86-64 | built, pluginval pass, REAPER render | built, clap-validator pass, REAPER render | built | Windows host, MSVC 19.51, 2026-11-04 |
| macOS arm64 and x86-64 | not built | not built | not built | no macOS runner |

The Windows VST3 and CLAP builds render equivalent one-note REAPER projects to
byte-identical WAV files. Renoise 3.5.4 is installed on the Windows host but
only scans VST3 from `C:\Program Files\Common Files\VST3`, which the current
account cannot write. That is a host path limit, not a plugin load failure. The
macOS rows are not claims of support. They need a native build, `pluginval` and
two DAWs per platform before they move to pass. AU remains a later macOS target.

The bridge build is host-native and optional. It is separate from the firmware
Docker gate. The generated `firmware/gen` must exist before CMake configures.

## 14. Risks

| Risk | Trigger | Response |
| --- | --- | --- |
| State refactor changes the sound | Any sample difference in the parity test | Stop, compare the generated state access, fix before plugin work |
| Two instances still share state | A second instance changes the first | Treat as a Milestone 0 failure |
| JUCE fetch is unavailable | No network in the build environment | Support `JUCE_DIR` and a pinned local archive |
| CLAP wrapper rots | The extension lags JUCE | Keep VST3 as the primary target, CLAP behind a flag |
| Firmware C stops compiling on MSVC | GCC attributes or volatile casts reach the plugin build | Keep `msvc_compat.h` and the Windows CTest target green |
| CLAP state load reports success on invalid bytes | `clap-validator` warning | Document it, keep the processor rejection, do not fake a valid state |
| Rate bridge colors the sound | THD or alias above the budget | Raise the tap count or change the filter, never change the core rate |
| Parameter map misses a control | Coverage test fails | Fix the map, not the test |
| Device preset round trip breaks | Byte mismatch | Use the C record functions, never a C++ copy |
| Name limit surprises users | More than 15 characters typed | Show the limit in the rename dialog, keep device compatibility |
| Font licence blocks release | Brand font unclear | Ship the Arial Black fallback until cleared |

## 15. Open questions

- CLAP is part of the first build on Linux. VST3 remains the primary target and
  CLAP stays behind `P1_BUILD_CLAP`.
- Is AU required on macOS in the first release?
- Does the first release need device preset import and export, or only the
  in-plugin banks?
- Block-accurate automation is accepted for v1. The processor reads the APVTS at
  the 32-sample control block. A sample-accurate claim is not part of v1.
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

Do not start with the editor. Start with Milestone 0. A plugin that cannot run
two instances is not a plugin yet.
