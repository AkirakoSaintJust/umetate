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
- **Polyphony and voice stealing:** 20 voices; oldest-steal on overflow.
- **Pitch range and tuning:** 12-TET, full MIDI note range; per-op `ratio`
  (note-derived, non-integer ratios stay in tune).
- **Oscillators / operators / noise:** 4 operators, each `phasor → osc →
  dx_env → vca` with 1-sample self-feedback (`fm_op` macro).
- **Filter(s) and resonance:** one global `svf`, `type` selectable (LP/BP/HP),
  `q` = damping, with an **on/off bypass** and an **ADSR envelope routed to
  cutoff**.
- **Envelopes and velocity:** DX rate/level (`dx_env`, 4 rates + 3 levels);
  velocity → amplitude/FM/envelope-rate is wired (F2), but the dogfood defaults
  the depths to 0 (off) — settable via `set_param` (`opN.velamp.depth` etc.),
  not on the panel.
- **Modulation:** the routing matrix (8 algorithms) selects which operator
  phase-modulates which; feedback = self-modulation. One **per-part pitch LFO**
  (vibrato), one **per-note pitch envelope** (the "pitch blip": a `base` offset
  that decays back at note-on), and one **amplitude LFO per operator** (tremolo,
  per-voice).
- **Effects and output stage:** carrier sum → `svf` (type LP/BP/HP + bypass +
  a cutoff ADSR) → `wavefolder` (threshold + fold count + type) → `out` (the
  `MASTER` pot is the volume; no output VCA).

### 2.1a The output chain (filter + fold), specified

- **Filter (`svf` extension).** Params: `type` (0 = LP, 1 = BP, 2 = HP — the
  node already computes `low`/`band`/`high`, so `type` selects the output), `on`
  (0 = bypass = pass the input straight through), `f` (cutoff, Q16), `q`
  (damping, Q16). A **cutoff envelope** — a `dx_env` (rate/level, ADSR-shaped:
  attack → sustain → release) whose Q15 output scales a `fenv_depth` and is
  added to `f`. On a note-on it opens the filter; on note-off it closes.
- **Fold (`wavefolder` extension).** Params: `on` (0 = dry), `threshold` (the
  input level, Q15, above which folding engages), `folds` (the fold count —
  number of sine folds applied; 1 = the current single fold), `type` (0 = sine
  fold, others reserved). Folding applies to the signal above `threshold`; the
  dry signal below `threshold` passes unmodified.

### 2.1b Per-part voice modes (moved from global)

`mode` (0 = poly, 1 = unison, 2 = legato), `unison_count`, `unison_detune`,
`legato` (voice count), `portamento` (time), `note_priority` become **per-part**
params (each part its own poly/unison/legato + counts + times), exposed in `GLO`.
This is a breaking change to the voice-mode param layout: they move from the
global six to a per-part array.

### 2.1 Voice architecture (the node/macro graph)

- **Voice-zone graph** (20 voices): four `fm_op` instances `op1..op4`, four
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
- **Global-zone graph:** `algo` (the algorithm selector) → `alg` into the `route`
  node; `lp` (`svf`) → `wf` (`wavefolder`) → `out`: `voice → lp.audio`,
  `lp.low → wf.audio`, `wf.audio → out`.
- **Voice-zone additions:** `penv` (a per-note `pitch_env`, retriggered on every
  note-on) + `plfo` (the per-part vibrato LFO) + `psum` (a `csum`):
  `plfo.cv + penv.cv → op1..op4.pitch`.
- **Macros:** `fm_op` (shipped, `modules/macros/fm_op/`) — the operator, with
  params `ratio` (note-derived), `detune` (cents −50..50), `waveform`, `level`,
  `feedback` (per-op self-modulation), `trem_rate`, `trem_depth`, `r1..r4`,
  `l1..l3` mapped inward, and inputs `fm` (audio) + `pitch` (control).
- **Voice count / sample rate:** 20 voices / 44100 Hz (the default).
- **Feedback paths:** each operator's self-feedback is one `delay1` (the
  **oscillator** output × feedback → sum with external fm + pitch → `ph.fm`,
  tapped *pre*-envelope/pre-tremolo so the amplitude LFO never leaks into pitch).
  Feedback is **per-op only**: `opN_feedback` (its own self-modulation, on the op
  page) scales that operator's delayed oscillator output. (The earlier
  carrier-gated `feedback` master — the scrapped HOME knob that pushed a master
  amount onto whichever operator was the current carrier — is gone; it left a
  spurious feedback floor on every carrier even at zero.)

### 2.2 Parameter manifest

> The friendly names below are what the panel exposes. The engine is
> **two-timbre** (`parts: 2`, channels 0 and 1): every voice-zone param is a
> per-part array, so the full id space is **82 voice params per part** (the
> `fm_op` macro's 17 × 4 operators + the per-note pitch envelope's 8 + the six
> voice-mode params) × 2 parts + 20 global (the filter + fold output chain) +
> 10 routing = **194 `set_param` ids**, part-major (`part × param`). The patch's
> `cc:` list exposes 56 of them (part 0's timbre + the global FX + both parts'
> mode params) as the fixed CC surface; part 1's timbre comes from the
> multi-patch / SysEx. The six voice-mode params (`mode`, `unison_count`,
> `unison_detune`, `legato`, `portamento`, `note_priority`) are **per-part**
> (each part its own poly/unison/legato + counts + times).

| Param (name) | Target | Min | Max | Curve | Unit | Display |
| --- | --- | --- | --- | --- | --- | --- |
| algorithm | algo.algorithm | 0 | 7 | linear | | raw (0–7) |
| cutoff | lp.f | 0 | 65535 | log | | off_pct ("off" at 0) |
| res | lp.q | 0 | 65535 | linear | | pct_inv (100% = least damping) |
| filter_type | lp.type | 0 | 2 | linear | | raw (0=LP 1=BP 2=HP) |
| filter_on | lp.on | 0 | 1 | linear | | onoff (off/on) |
| fenv_a | fenv.a | 0 | 65535 | log | | raw |
| fenv_d | fenv.d | 0 | 65535 | log | | raw |
| fenv_s | fenv.s | 0 | 32767 | linear | | pct |
| fenv_r | fenv.r | 0 | 65535 | log | | raw |
| fenv_depth | lp.fenv_depth | 0 | 65535 | linear | | raw |
| fold | wf.amount | 0 | 32767 | linear | | pct |
| fold_on | wf.on | 0 | 1 | linear | | onoff (off/on) |
| fold_threshold | wf.threshold | 0 | 32767 | linear | | pct |
| fold_folds | wf.folds | 1 | 8 | linear | | raw |
| fold_type | wf.type | 0 | 0 | linear | | raw |
| attack | op1.eg.r1 | 0 | 99 | linear | | raw (0–99 rate) |
| release | op1.eg.r4 | 0 | 99 | linear | | raw (0–99 rate) |
| pitch_rate | plfo.rate | 0 | 20000000 | log | | hz |
| pitch_depth | plfo.depth | 0 | 3277 | linear | | pct |
| penv_on | penv.on | 0 | 1 | linear | | onoff (off/on) |
| penv_r1 … penv_r4 | penv.rN | 0 | 99 | linear | | raw (0–99 rate) |
| penv_l1 … penv_l3 | penv.lN | -32768 | 32767 | linear | | semi (±st) |
| op1_level … op4_level | opN.tl.level | 0 | 99 | linear | | raw (0–99) |
| op1_waveform … op4_waveform | opN.osc.waveform | 0 | 11 | linear | | raw (0–11) |
| op1_ratio … op4_ratio | opN.ph.inc_ratio | 32768 | 1048576 | linear | | ratio (1.00 = base) |
| op1_detune … op4_detune | opN.ph.detune | -50 | 50 | linear | | cent (±c) |
| op1_mute … op4_mute | opN.mute.mute | 0 | 1 | linear | | onoff (off/on) |
| op1_feedback … op4_feedback | opN.fb.level | 0 | 32767 | linear | | pct |
| op1_trem_rate … op4_trem_rate | opN.lfo.rate | 0 | 20000000 | log | | hz |
| op1_trem_depth … op4_trem_depth | opN.lfo.depth | 0 | 32767 | linear | | pct |

The `display` column is the per-param on-screen form (the `params:` `display`
field → a `ui_param_disp` entry in the generated panel). A relative encoder steps
per the curve (linear = a fraction of the range, log = multiplicative), so each
knob reaches its whole range in a sane number of turns and clamps at the ends.

(`level` is the Yamaha total-level (0–99, 0.25 dB/step: 99 = max, 50 ≈ −12 dB,
0 = silence) that gates the operator's
output with −12 dB single-operator headroom (`fm1_level_gain[level] >> 2`), so a
solo carrier never clips and a four-carrier additive algorithm sums to ~0 dBFS;
`opN_feedback` is each operator's own self-modulation depth. The DX rates
(`r1..r4`, `penv_r1..r4`) are 0–99 → a one-pole coefficient via
`fm1_rate_coeff` (a non-uniform Yamaha-style curve: 99 = instant ≈ 0.73 ms, 0 ≈ 7 s); the DX levels (`l1..l3`) are
0–99 → Q15 gain via `fm1_level_gain` (0.25 dB/step). `rate` is a Q32 phase
increment per sample — `f · 2³² / 44100`, so ~97392 = 1 Hz. `depth` is `depth/32768` in the
use's units: octaves of vibrato for `pitch_depth` (273 ≈ ±10 cents), fraction of
full amplitude for `trem_depth` (~16000 ≈ ±50%). `ratio` is the q16 frequency
multiplier — `ratio/65536` = the multiplier (65536 = 1.0, 32768 = 0.5). The
per-note pitch envelope (`penv`) retriggers on every note-on, releases on
note-off, and is off by default; its levels `l1..l3` are q15 pitch offsets
(32768 = +1 octave, 2731 ≈ +1 semitone). All block rate.)

### 2.3 Tables

- **`routing` → kind `routing`** — the 8-algorithm 4-op FM matrix (8 rows × 5
  sub-rows × 4 Q15 0/1 weights = 160 entries), ymfm's `s_algorithm_ops`
  {0,1,2,3,4,5,6,7} (the full standard TX81Z/DX100/DX21 4-op set).

### 2.4 Scope taps

`taps: ["op1.audio", "op2.audio", "op3.audio", "op4.audio"]` — four per-operator
audio tap points (resolved to each operator's post-mute output), exposed per part
as `N_TAP × N_PART` = 8 channels via `fourop_fm_dsp_tap(ch)` (`ch = tap × 2 +
part`, the last block's Q15 samples). These feed the HOME 4-op scope/spectro
pages (§3.3): the active part's four operators are its four channels, so the
"active part" label stays true when both parts layer.

## 3. Controls and display

### 3.1 The control surface (fixed)

`MASTER` = volume (platform). `ALGORITHM` = always-on algorithm encoder. `KNOB1–4`
= the current page's params. `SELECT` = page up/down (wrapping). The buttons:
`EDIT` (operator pitch), `ENV` (envelopes), `LFO` (modulation), `FX` (filter +
fold), `GLO` (parts + patch), `HOME` (the visual pages), `ARP`/`SEQ`/`PLAY`/`REC`
(operator mutes 1–4), `SCL` (operator select + part switch + part mute combos),
`PRESETS` (the patch-browser popup), `OCT−`/`OCT+` (shift the keybed a whole
octave, ±2, firmware-level). The keybed plays notes; `SCL`+key is the mute chord.

### 3.2 Always visible (every page, a fixed header)

The header is two lines. Line 1 shows, at all times: every **part** (`P1 P2`) and
**operator** (`op 1 2 3 4`), each with its **ON/OFF** (muted, an `x`) state and the
active one highlighted; the **current algorithm** (`ALG n`); and the **current menu
name + page number/total** (`EDIT 1/2`). Line 2 is the **page description** (the
page's first widget, e.g. `OSCILLATOR`, `OP DETUNES`). Colours: parts + operators
white, active pink, `ALG` yellow, menu/page purple, the description green. No page
may hide any of it.

### 3.3 Contexts (menus) and their pages

- **HOME** (visual, column layout — each widget a row, part 1 / op 1 on top):
  1. envelope graphs of all 4 operators of the active part;
  2. oscilloscope of all 4 operators of the active part;
  3. spectrogram of all 4 operators of the active part;
  4. oscilloscope of both parts;
  5. spectrogram of both parts.
- **EDIT** (the active operator): ratio · level · feedback · waveform + a live
  scope/spectro (one page); then **PART n OP DETUNES** — all four operators'
  detunes (±50 cents) of the active part.
- **ENV**: the active operator's **amplitude envelope** in two pages — rates
  (r1/r2/r3/r4) then levels (l1/l2/l3); then the **per-part pitch envelope**
  (base + rate). The envelope graph is drawn on both amplitude-envelope pages.
- **LFO**: the active operator's **amplitude LFO** (rate + depth); then the
  **per-part pitch LFO** (vibrato rate + depth).
- **FX** (the output chain): **filter** — on/off, cutoff, rez, type, and an ADSR
  envelope routed to cutoff; **fold** — on/off, threshold, folds (count), type.
- **GLO** (parts + patch): per-part **level** (scales the part's maximum
  amplitude) and **delay**; per-part **voice mode** (poly / unison / legato,
  with unison voice count + detune, legato voice count, portamento time); part
  **name**, MIDI **channel**, **keyboard split**, **INIT PART**; **save/load a
  single part into either part** from the preset store; multi-patch settings —
  **multi-patch name**, **INIT PATCH** (additive algorithm, gate-type envelopes,
  waveform 0, no feedback, ratio 1, all ops ON, part 2 OFF, part 1 active,
  level 75).

### 3.4 The shortcuts and modifiers

`SCL` **taps** the next active operator; a **double-tap** switches the active
part. **Holding `SCL` + a key** mutes that operator (chord, not a note). **Holding
`SCL` + `ARP` or `PLAY`** toggles part 1 mute; **`SCL` + `SEQ` or `REC`** toggles
part 2 mute. `ARP`/`SEQ`/`PLAY`/`REC` (plain) toggle operator mutes 1–4 — the
old mute sub-page is gone. The `PRESETS` encoder opens the **multi-patch (2-part)
preset browser** as a popup; after 2 s with no preset-encoder input, the selected
patch loads and the popup clears (unless it is already loaded — then it just
clears). Single-part presets load from the `GLO` menu. `SAVE` opens the **save
chooser** — a two-row `single part` / `multi-patch` dialog (`KNOB1` = row,
`KNOB2` = slot, `SAVE` = commit, `HOME` = cancel; no idle timeout). Saving a
multi-patch then asks what to do with the active part's live edits — **discard
edits**, **save as a new part**, or **mutate in place** (`KNOB1` picks, `SAVE`
commits, `HOME` goes back).

### 3.5 Screen rules

Retained-mode, ~30 Hz redraw, no display in the audio callback, full clear on
page/context change, held notes stay playable. Per-param display scale (ratio
`1.00`, on/off, `%`, Hz, semitones) as §2.2.

## 4. MIDI and connectivity

- **MIDI in / out:** in — notes, CC (the `cc:` list, sustain CC64, panic CC123),
  pitch bend (±2 semitones); out — the local keys echo on part 0's channel.
- **Channels:** two parts — part 0 = channel 0, part 1 = channel 1 (a note
  routes to every part whose channel + keyzone match; layering allowed).
- **Velocity-zero note-off, sustain, panic:** velocity-zero = note-off; sustain
  defers note-offs until the pedal lifts; `all_notes_off` (CC123) = panic.
- **Clock and transport:** none (ignored).
- **USB roles:** MIDI in/out; firmware update via the normal flash path.
- **Overflow and back-pressure:** voice stealing (oldest) on >20 voices.

## 5. State and persistence

- **What survives reboot:** 128 single parts + 64 multi patches + the settings
  record (base channel, master tune), saved to flash **only when silent** and
  only on an explicit save; the multi-patch in slot 0 applies at boot.
- **Patch/sequence format and version:** the preset records (`docs/roadmap.md`
  §6.11.4): `u8 version | name[16] | params | crc32`, 128 single-part slots +
  64 multi-patch slots (chunked across the slot area's measured 16 372 B
  ceiling).
- **Storage budget and CRC/commit rule:** per-record CRC-32 + the area CRC;
  a corrupt record is skipped, never the bank.
- **Backup, import/export, migration, rollback:** `umetate preset export/import`
  (the bank ↔ `.syx`), and the five SysEx commands (identity / param dump /
  single-part / multi-patch / settings).

## 6. Browser prototype

- **What you want to hear or compare locally:** the 8 algorithms side-by-side;
  confirm the routing matrix sounds like the DX algorithm family.
- **Which parameters and MIDI controls the page needs:** algorithm + the 5
  output-chain params; keys via mouse/MIDI.
- **Supported browsers and offline expectation:** any WebAudio browser; offline
  once built.
- **What the browser must not be used to claim:** device performance — the WASM
  build is the parity lab, not the device.

## 7. Acceptance and evidence

- **Must-have features:** 8 runtime algorithms; 12 waveforms; per-op + carrier
  feedback; rate/level envelopes; a per-part pitch LFO + per-note pitch envelope +
  per-op amplitude LFO; the filter + wavefolder output chain; a panel; **two
  timbres** (parts), **presets** (128+64 + settings), **SysEx**, **MIDI CC /
  sustain / panic / bend**.
- **Optional features (shipped, defaulted off):** velocity scaling (the depths
  default to 0).
- **Host tests:** `umetate deep-check --all` — mypy + ruff + pyright, the four
  test modules (`test_generate` renders the patch + proves the 8 algorithms +
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
- **Open questions that still change architecture:** none — the 8-algorithm set
  (ymfm `s_algorithm_ops` 0..7) is locked in `dsp-algorithm.md`; the F7 additions
  (two timbres, presets, SysEx, the `cc:` surface, the app glue) are locked in
  the roadmap §6.11.
