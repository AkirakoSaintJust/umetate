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
- **Explicit non-goals:** no patch persistence/MIDI sysex, no effects beyond
  filter + wavefolder, no velocity scaling (deferred; see README).

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
- **Envelopes and velocity:** DX rate/level (`dx_env`, 4 rates + 3 levels); no
  velocity scaling (deferred).
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
- **Global-zone graph:** `lp` (`svf`) → `wf` (`wavefolder`) → `out`, plus the
  shared `plfo` (`lfo`) and `penv` (`pitch_env`) whose `cv`s are summed by
  `psum` (`csum`) into every operator's `pitch`:
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
  page) is summed with the carrier-gated `feedback` master (`route.feedback`, the
  HOME knob) — the `route` node gates the master by the carrier mask into
  `op1..op4.car_fb`, so only the carrier gets the master on top of its per-op
  amount.

### 2.2 Parameter manifest

> The 39 friendly names below are what the panel exposes; the generator also
> auto-exposes the remaining flattened operator-envelope params (per-op
> `r2/r3/l1/l2/l3` × 4, plus op2–4's `r1`/`r4`) by their
> `<instance>.<param>` target path (settable via `set_param`, not on the panel).

| Param (name) | Target | Min | Max | Curve | Unit |
| --- | --- | --- | --- | --- | --- |
| algorithm | route.algorithm | 0 | 6 | linear | |
| cutoff | lp.f | 0 | 65535 | log | Hz |
| res | lp.q | 0 | 65535 | linear | |
| fold | wf.amount | 0 | 32767 | linear | |
| feedback | route.feedback | 0 | 32767 | linear | |
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
feedback master (`route.feedback`, added to whichever operator is the current
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

- **MIDI in / out / thru:** MIDI in (notes); no out/thru.
- **Channels, velocity-zero note-off, sustain, panic:** omni; velocity-zero =
  note-off; `all_notes_off` panic.
- **Clock and transport:** none.
- **USB roles:** MIDI (update via the normal flash path).
- **Overflow and back-pressure:** voice stealing (oldest) on >8 voices.

## 5. State and persistence

- **What survives reboot:** nothing (the patch + panel are compile-time; params
  are RAM).
- **Patch/sequence format and version:** N/A.
- **Storage budget and CRC/commit rule:** N/A.
- **Backup, import/export, migration, rollback:** N/A.

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

- **Must-have features:** 7 runtime algorithms; 12 waveforms; carrier-only
  feedback; rate/level envelopes; a global pitch LFO + global pitch envelope +
  per-op amplitude LFO; the filter + wavefolder output chain; a panel.
- **Optional features:** velocity scaling, patch persistence.
- **Host tests:** `umetate.test_generate` renders the patch (non-silent → decays),
  proves the 7 algorithms, resolves the panel, and checks the LFO oscillates; the
  routing table is the 7-algorithm matrix.
- **Target package checks:** `lint.c_checks` clean; the emitted DSP compiles
  under the JieLi clang.
- **Physical timing and device checks:** device acceptance is `blocked`
  (hardware ~10 days out).
- **Known unknowns:** the `svf` sub-LSB limit cycle (recorded in the roadmap,
  benign).

## 8. Confirmation

- **Brief owner:** P1Onken.
- **Date confirmed:** 2026-10-27.
- **Open questions that still change architecture:** none — the 7-algorithm
  collapse (algorithm 2 ≡ 3) is locked in `dsp-algorithm.md`.
