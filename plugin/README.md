# Type P.fm1 plugin plan

Status: Milestone 2 done, 2026-11-03. The JUCE VST3 and standalone host build,
render audio, accept MIDI and save state. The editor is still the generic JUCE
panel.

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
- CLAP through a pinned wrapper after VST3 is stable.
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
- At 44.1 kHz the bridge is bypassed and the output is bit-exact with the firmware
  host render.
- At other rates, a 32-tap Kaiser-windowed sinc polyphase resampler converts the
  output. It anti-aliases on downsampling and reports its group delay as plugin
  latency. The core is never resampled on input.
- The resampler ratio is rational. The bridge consumes 44.1 kHz frames and
  produces host frames. It handles any host block size.
- The editor and the visualisers always run on the 44.1 kHz timeline.
- Latency: report the resampler delay. The 32-sample control block is part of the
  instrument and is not compensated.
- Test at every supported rate: THD, alias rejection, passband ripple, latency,
  and no dropouts at 32, 64, 128, 256, 512 and 1024 frames.

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

- Fixed 1240 wide design grid, one uniform scale.
- Pages: patch settings, operators, fx / mod.
- The active part selector is UI state. The patch page shows both parts. The
  operators page binds to the active part. The fx / mod page is global.
- The header algorithm block shows the active part's algorithm. The picker writes
  the active part's `algorithm` parameter.
- The four operator scopes and spectros read the operator taps. The two part
  scopes and spectros read each part's carrier tap.
- The key and velocity card uses target selectors, exactly as the mockup does.
  The hidden parameters stay exposed to the host.
- Dialogs scroll. Patch browser uses 64 slots. Part slots use 128. The mockup's
  eight rows are illustrative.
- Names use the device record limit of 15 characters. A longer plugin-only name
  would break round-tripping with the device.
- Text entry, keyboard focus and the cut-polygon tabs follow the design language.
- No filler copy.

## 10. Presets and state

The plugin state is a versioned blob:

```text
version
APVTS state (313 parameters)
ui_active_part, ui_page
multi bank (64 records)
part bank (128 records)
current multi slot, part source slots
```

- Use `preset_multi_pack`, `preset_multi_unpack`, `preset_part_pack` and
  `preset_part_unpack` from `presets.c`. The byte layout stays device-compatible.
- The plugin state owns an in-memory bank. It does not write files on the audio
  thread.
- The patch browser edits the 64 multi slots. The part save and load dialogs edit
  the 128 single-part slots.
- DAW presets save the whole state. The bank size is small enough for one state
  blob.
- Import and export of a device preset bank through SysEx is a later milestone.
- The plugin must not silently rewrite a device bank. User confirmation is
  required before an overwrite, as in the mockup.

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
- CLAP through a pinned `clap-juce-extensions` wrapper. Confirm its licence in
  the build manifest.
- Windows: MSVC 2022 or clang-cl, VST3 SDK from JUCE.
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
| 3 | Editor | three pages, tokens, visualisers, dialogs, fixed scale |
| 4 | Presets and banks | 64 multi and 128 part slots, device record round trip |
| 5 | Rate bridge | bypass exact, 48/96/192 measured, latency reported |
| 6 | CLAP and platform matrix | clap-validator, pluginval, two DAWs per platform |
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
the parameter state. The generic JUCE editor is a placeholder for Milestone 3.
The 48 kHz path uses the temporary linear RateBridge, so it renders audio but is
not yet release quality. The `plugin_smoke` CTest checks the parameter count,
unique ids, contiguous engine ids, bit-exact 44.1 kHz output, an automation
write at the 32-sample control block, a MIDI offset at its control block and a
state round trip. `engine_parity` remains green.

Host bridge build:

```sh
umetate build --synth examples/type-p-fm1   # regenerate firmware/gen first
cmake -S plugin -B build/plugin
cmake --build build/plugin
ctest --test-dir build/plugin --output-on-failure
```

JUCE VST3 and standalone build:

```sh
cmake -S plugin -B build/plugin-juce -DP1_BUILD_JUCE=ON
cmake --build build/plugin-juce
ctest --test-dir build/plugin-juce --output-on-failure
```

The artifacts are under
`build/plugin-juce/juce/type_p_fm1_artefacts/Release/VST3` and `Standalone`.
On Linux, install `pkg-config`, `libasound2-dev`, the X11, Xrandr, Xcursor,
Xinerama, Xcomposite and Xrender headers, freetype and fontconfig, and the
OpenGL headers. JUCE 8.0.9 is fetched at configure time.

The bridge build is host-native and optional. It is separate from the firmware
Docker gate. The generated `firmware/gen` must exist before CMake configures.

## 14. Risks

| Risk | Trigger | Response |
| --- | --- | --- |
| State refactor changes the sound | Any sample difference in the parity test | Stop, compare the generated state access, fix before plugin work |
| Two instances still share state | A second instance changes the first | Treat as a Milestone 0 failure |
| JUCE fetch is unavailable | No network in the build environment | Support `JUCE_DIR` and a pinned local archive |
| CLAP wrapper rots | The extension lags JUCE | Keep VST3 as the primary target, CLAP behind a flag |
| Rate bridge colors the sound | THD or alias above the budget | Raise the tap count or change the filter, never change the core rate |
| Parameter map misses a control | Coverage test fails | Fix the map, not the test |
| Device preset round trip breaks | Byte mismatch | Use the C record functions, never a C++ copy |
| Name limit surprises users | More than 15 characters typed | Show the limit in the rename dialog, keep device compatibility |
| Font licence blocks release | Brand font unclear | Ship the Arial Black fallback until cleared |

## 15. Open questions

- Is CLAP a first-release target or a fast follow? The plan assumes VST3 first.
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
