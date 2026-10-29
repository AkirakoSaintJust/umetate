# Synth brief — fourop-fm

> One brief as the source of truth. `patch.json` + `panel.json` are the
> translation of this brief; `dsp-algorithm.md` holds the math.

## 1. Instrument and player

- **Working name:** fourop-fm (a 4-operator Yamaha FM synth).
- **Who plays it and in what setting:** a desktop/tabletop FM voice in the
  OPZ/DX21 lineage — pads, bells, EPs, basses. Played from the keys or MIDI.
- **What should it feel like to play:** immediate, bright-but-tameable; the
  algorithm knob should be the headline gesture, the filter + wavefolder the
  softening stage.
- **Three reference sounds:** (1) a DX7-style E-piano (algorithm 4, two
  2-operator stacks); (2) a clangorous bell (algorithm 0, deep stack + feedback);
  (3) an additive organ pad (algorithm 7, all four carriers).
- **Explicit non-goals:** no effects beyond filter + wavefolder (patch
  persistence, SysEx, and velocity scaling are now shipped — see §4/§5).

## 2. Sound and voice architecture

- **Synthesis method(s):** 4-operator phase-modulation FM, per-operator
  self-feedback, 12 waveforms per operator (the OPZ + OPL union), rate/level
  envelopes.
- **Polyphony and voice stealing:** 8 voices; oldest-steal on overflow.
- **Pitch range and tuning:** 12-TET, full MIDI note range; per-op `ratio`
  (note-derived, non-integer ratios stay in tune).
- **Oscillators / operators / noise:** 4 operators, each `phasor → osc →
  dx_env → vca` with 1-sample self-feedback (`fm_op` macro).
- **Filter(s) and resonance:** one global `svf` low-pass, `q` = damping.
- **Envelopes and velocity:** DX rate/level (`dx_env`, 4 rates + 3 levels);
  velocity → amplitude/FM/envelope-rate is wired (F2), but the dogfood defaults
  the depths to 0 (off) — settable via `set_param` (`opN.velamp.depth` etc.),
  not on the panel.
- **Modulation:** the routing matrix (7 algorithms) selects which operator
  phase-modulates which; feedback = self-modulation. One **global pitch LFO**
  (vibrato, shared across voices), one **global pitch envelope** (the "pitch
  blip": a `base` offset that decays back at note-on), and one **amplitude LFO
  per operator** (tremolo, per-voice).
- **Effects and output stage:** carrier sum → `svf` LP → `wavefolder` → `out`
  (the `MASTER` pot is the volume; no output VCA).

### 2.1 Voice architecture (the node/macro graph)

- **Voice-zone graph** (8 voices): four `fm_op` instances `op1..op4`, four
  `delay1` instances `d1..d4`, one `route` instance:
  ```
  op1.audio → d1.in      op2.audio → d2.in
  op3.audio → d3.in      op4.audio → d4.in
  d1.out → route.a   d2.out → route.b   d3.out → route.c   d4.out → route.d
  route.mod2 → op2.fm   route.mod3 → op3.fm   route.mod4 → op4.fm
  voice_out = route.car
  ```
  The four `delay1` make the graph acyclic for *every* algorithm (all modulation
  reads the 1-sample-delayed output of its sources).
- **Global-zone graph:** `algo` (the algorithm selector + carrier-feedback master)
  → `alg` into the `route` node + `fb1..fb4` into `op1..op4.car_fb`; `lp` (`svf`)
  → `wf` (`wavefolder`) → `out`, plus the shared `plfo` (`lfo`) and `penv`
  (`pitch_env`) whose `cv`s are summed by `psum` (`csum`) into every operator's
  `pitch`:
  `voice → lp.audio`, `lp.low → wf.audio`, `wf.audio → out`,
  `plfo.cv + penv.cv → op1..op4.pitch`.
- **Macros:** `fm_op` (shipped, `modules/macros/fm_op/`) — the operator, with
  params `ratio` (note-derived), `waveform`, `level`, `feedback` (per-op
  self-modulation), `trem_rate`, `trem_depth`, `r1..r4`, `l1..l3` mapped inward,
  and inputs `fm` (audio) + `pitch` (control) + `car_fb` (control, the carrier
  feedback master).
- **Voice count / sample rate:** 8 voices / 44100 Hz (the default).
- **Feedback paths:** each operator's self-feedback is one `delay1` (out ×
  feedback → sum with external fm + pitch → `ph.fm`). Feedback is **per-op +
  carrier**: each operator's `opN_feedback` (its own self-modulation, on the op
  page) is summed with the carrier-gated `feedback` master (`algo.car_fb`, the
  HOME knob) — the `algo` node gates the master by the carrier mask into
  `op1..op4.car_fb`, so only the carrier gets the master on top of its per-op
  amount.

### 2.2 Parameter manifest

> The 39 friendly names below are what the panel exposes. The engine is
> **two-timbre** (`parts: 2`, channels 0 and 1): every voice-zone param is a
> per-part array, so the full id space is 68 voice params (the `fm_op` macro's
> 17 × 4 operators) × 2 parts + 9 global + 10 routing + 6 voice-mode = **161
> `set_param` ids**, part-major (`part × param`). The patch's `cc:` list exposes
> 45 of them (part 0's timbre + the global FX + the mode params) as the fixed CC
> surface; part 1's timbre comes from the multi patch / SysEx. The 6 voice-mode
> params (`mode`, `unison_count`, `unison_detune`, `legato`, `portamento`,
> `note_priority`) are per-preset.

| Param (name) | Target | Min | Max | Curve | Unit |
| --- | --- | --- | --- | --- | --- |
| algorithm | algo.algorithm | 0 | 6 | linear | |
| cutoff | lp.f | 0 | 65535 | log | Hz |
| res | lp.q | 0 | 65535 | linear | |
| fold | wf.amount | 0 | 32767 | linear | |
| feedback | algo.car_fb | 0 | 32767 | linear | |
| attack | op1.eg.r1 | 0 | 65535 | log | |
| release | op1.eg.r4 | 0 | 65535 | log | |
| pitch_rate | plfo.rate | 0 | 20000000 | log | |
| pitch_depth | plfo.depth | 0 | 32767 | linear | |
| penv_base | penv.base | -32768 | 32767 | linear | |
| penv_rate | penv.rate | 0 | 65535 | log | |
| op1_level … op4_level | opN.vca.level | 0 | 32767 | linear | |
| op1_waveform … op4_waveform | opN.osc.waveform | 0 | 11 | linear | |
| op1_ratio … op4_ratio | opN.ph.inc_ratio | 32768 | 1048576 | linear | × |
| op1_mute … op4_mute | opN.mute.mute | 0 | 1 | linear | |
| op1_feedback … op4_feedback | opN.fb.level | 0 | 32767 | linear | |
| op1_trem_rate … op4_trem_rate | opN.lfo.rate | 0 | 20000000 | log | |
| op1_trem_depth … op4_trem_depth | opN.lfo.depth | 0 | 32767 | linear | |

(`level` is both the output amplitude and the FM index; `feedback` is the carrier
feedback master (`algo.car_fb`, added to whichever operator is the current
algorithm's carrier), and `opN_feedback` is each operator's own self-modulation
depth (added on top). `rate` is a Q32 phase increment per
sample — `f · 2³² / 44100`, so ~97392 = 1 Hz. `depth` is `depth/32768` in the
use's units: octaves of vibrato for `pitch_depth` (273 ≈ ±10 cents), fraction of
full amplitude for `trem_depth` (~16000 ≈ ±50%). `ratio` is the q16 frequency
multiplier — `ratio/65536` = the multiplier (65536 = 1.0, 32768 = 0.5). `penv_base`
is the q15 starting pitch offset of the global pitch envelope (the `phasor.pitch`
octave scale: 32767 = +1 octave, 2731 ≈ +1 semitone); `penv_rate` is its q16
one-pole decay rate toward the specified pitch. All block rate.)

### 2.3 Tables

- **`routing` → kind `routing`** — the 7-algorithm 4-op FM matrix (7 rows × 5
  sub-rows × 4 Q15 0/1 weights = 140 entries), ymfm's `s_algorithm_ops`
  {0,1,2,4,5,6,7} (algorithm 3 dropped as algorithm 2's mirror).

## 3. Controls and display

- **Keys, buttons, encoders, MASTER:** keys = notes; `ALGORITHM` = always-on
  algorithm; `KNOB1–4` = the current page's four params; `SELECT` cycles pages;
  `SEL` selects the operator; `EDIT`/`FX`/`GLO` push their contexts; `HOME` pops
  home; `MASTER` is the volume pot (platform, not a patch param).
- **Performance and navigation modes:** `home` (the four perform knobs cutoff ·
  res · fold · feedback), `op` (per-operator pitch/env/tremolo/mute sub-pages,
  operator-relative), `fx` (the output chain), `glo` (vibrato + the pitch
  envelope). Each op page opens with a `status` readout (`ALG n · OP n/4 · MUTE`).
- **Screen content and update rules:** retained-mode, ~30 Hz redraw; no display
  in the audio callback.
- **LED feedback:** none specific.
- **What must remain playable while the screen redraws:** held notes (redraw is
  rate-bounded and DMA-integrated).

## 4. MIDI and connectivity

- **MIDI in / out:** in — notes, CC (the `cc:` list, sustain CC64, panic CC123),
  pitch bend (±2 semitones); out — the local keys echo on part 0's channel.
- **Channels:** two parts — part 0 = channel 0, part 1 = channel 1 (a note
  routes to every part whose channel + keyzone match; layering allowed).
- **Velocity-zero note-off, sustain, panic:** velocity-zero = note-off; sustain
  defers note-offs until the pedal lifts; `all_notes_off` (CC123) = panic.
- **Clock and transport:** none (ignored).
- **USB roles:** MIDI in/out; firmware update via the normal flash path.
- **Overflow and back-pressure:** voice stealing (oldest) on >8 voices.

## 5. State and persistence

- **What survives reboot:** 32 part patches + 32 multi patches + the settings
  record (base channel, master tune), saved to flash **only when silent** and
  only on an explicit save; the multi patch in slot 0 applies at boot.
- **Patch/sequence format and version:** the preset records (`docs/roadmap.md`
  §6.11.4): `u8 version | name[16] | params | crc32`, 32 slots each (the slot
  area's measured 16 372 B ceiling).
- **Storage budget and CRC/commit rule:** per-record CRC-32 + the area CRC;
  a corrupt record is skipped, never the bank.
- **Backup, import/export, migration, rollback:** `umetate preset export/import`
  (the bank ↔ `.syx`), and the five SysEx commands (identity / param dump /
  part-patch / multi-patch / settings).

## 6. Browser prototype

- **What you want to hear or compare locally:** the 7 algorithms side-by-side;
  confirm the routing matrix sounds like the DX algorithm family.
- **Which parameters and MIDI controls the page needs:** algorithm + the 5
  output-chain params; keys via mouse/MIDI.
- **Supported browsers and offline expectation:** any WebAudio browser; offline
  once built.
- **What the browser must not be used to claim:** device performance — the WASM
  build is the parity lab, not the device.

## 7. Acceptance and evidence

- **Must-have features:** 7 runtime algorithms; 12 waveforms; per-op + carrier
  feedback; rate/level envelopes; a global pitch LFO + global pitch envelope +
  per-op amplitude LFO; the filter + wavefolder output chain; a panel; **two
  timbres** (parts), **presets** (32+32 + settings), **SysEx**, **MIDI CC /
  sustain / panic / bend**.
- **Optional features (shipped, defaulted off):** velocity scaling (the depths
  default to 0).
- **Host tests:** `umetate deep-check --all` — mypy + ruff + pyright, the four
  test modules (`test_generate` renders the patch + proves the 7 algorithms +
  resolves the panel; `test_cli` runs the `build --synth` composition), plus
  `umetate budget` (the measured polyphony claim).
- **Target package checks:** `umetate build --synth examples/fourop-fm` →
  `umetate-fm1-pro-fourop_fm.fwsc` (82 060 B image, `.dsp_text` in SRAM); the
  JieLi build's own checks green.
- **Emulator:** `umetate emu --check --mhz 240` boots the package and holds a
  chord — no halt, full-scale audio peak.
- **Physical timing and device checks:** device acceptance is `blocked`
  (hardware ~10 days out).
- **Known unknowns:** the `svf` sub-LSB limit cycle (recorded in the roadmap,
  benign).

## 8. Confirmation

- **Brief owner:** P1Onken.
- **Date confirmed:** 2026-10-27.
- **Open questions that still change architecture:** none — the 7-algorithm
  collapse (algorithm 2 ≡ 3) is locked in `dsp-algorithm.md`; the F7 additions
  (two timbres, presets, SysEx, the `cc:` surface, the app glue) are locked in
  the roadmap §6.11.
