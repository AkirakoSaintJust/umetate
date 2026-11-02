# Custom code structure + interface — type-p-fm1

> Everything beyond the declarative `patch.json`/`panel.json`. The type-p-fm1
> dogfood is mostly *library*: it added a handful of nodes/macros + two HAL
> helpers, then declared the synth. No hand-written `dsp.c` — the generator emits
> it. The one hand-written piece is `app.c` (the app glue on the frozen `rib.c`
> framework, F7): `app_audio`/`app_main`/`app_idle`, the `ui_act_*` hooks, and
> the three service contexts (`synth_midi_ctx`/`synth_sysex_ctx`/
> `synth_runtime_ctx`).

## 1. Files

- **Created** (nodes/macros the dogfood shipped, in the library):
  - `modules/nodes/dx_env/` — the DX rate/level envelope (`node.json` + `node.c`).
  - `modules/nodes/mix4/` — 4-input summer.
  - `modules/nodes/route4/` — the general routing-matrix row mixer.
  - `modules/nodes/route/` — the audio-rate 4-op FM router (reads `alg` + 4 rows).
  - `modules/nodes/algo/` — the algorithm selector (control rate).
  - `modules/nodes/lfo/` — the control-rate low-frequency oscillator.
  - `modules/nodes/mute/` — the output gate (per-operator mute).
  - `modules/nodes/gain/` — pure audio×cv gain (no static `level`).
  - `modules/nodes/cmul/` — control×control multiplier (control-rate modulation).
  - `modules/nodes/csum/` — control summer (control-rate modulation).
  - `modules/nodes/pitch_env/` — the global pitch envelope (the "pitch blip").
  - `modules/macros/fm_op/` — the operator (`macro.json`).
  - `examples/type-p-fm1/{patch.json,panel.json,app.c,host-script.txt,synth-brief.md,dsp-algorithm.md,code-structure.md,control-map.md,README.md}`.
- **Modified**:
  - `modules/nodes/osc/` — added the `waveform` param (12 waveforms, the OPZ+OPL union).
  - `modules/nodes/vca/` — added the `level` param (Q15 gain).
  - `modules/nodes/phasor/` — the `fm` input now scales `<<16` (full-scale = ±π
    phase swing), and a `pitch` input scales the increment (`inc × (1 + pitch/32768)`,
    full-scale = ±1 octave) for relative-pitch vibrato.
  - `firmware/hal/fm1_math.h` — `fm1_sin_wave` (the 12-wave OPZ+OPL union),
    `fm1_route4` (the 4-weight Q15 dot product).
  - `umetate/_tables.py` — the `routing` table kind (the 8-algorithm matrix).
- **Forbidden to touch:** HAL registers, `platform.c` services, the loader,
  `uboot.boot`/`isd_config.ini` — none were touched.

## 2. The seam (library path)

No hand-written `dsp.c`: `generate(patch)` emits `<synth>_dsp_*` from the patch
(`docs/roadmap.md` §12.1). The new code is nodes/macros + the two HAL helpers.

### New nodes

- **`dx_env`** — `node.json`: `ins { gate(event, default voice_gate[v]),
  trigger(event, default voice_trig[v]), rate_scale(control, default 32768) }`,
  `outs { cv(control) }`, `params { r1 r2 r3 r4(rate 0..99), l1 l2 l3(level 0..99) }`,
  `state { stage(uint32), level(q15) }`. `node.c`: a 5-stage one-pole state
  machine (control rate) whose stage coefficient is `fm1_rate_coeff[rate]`
  (scaled by `rate_scale` — velocity → envelope rate) and whose level targets are
  `fm1_level_gain[level]` (0.25 dB/step); `trigger` retriggers on a note-on edge.
  Host test: `test_generate.py` `DX_ENV` + `RELEASE_PATCH`.
- **`tl`** — `node.json`: `ins { audio, cv(control, default 32768) }`,
  `outs { audio }`, `params { level(level 0..99) }`. `node.c`: the Yamaha
  total-level cell `audio × cv × (fm1_level_gain[level] >> 2)` — the `>> 2` is the
  −12 dB single-operator headroom. Host test: the type-p-fm1 render + clipping
  headroom assertions.
- **`pitch_env`** — `node.json`: `ins { gate(event, default voice_gate[v]),
  trigger(event, default voice_trig[v]) }`, `outs { cv(control) }`,
  `params { on(uint32), r1..r4(rate), l1..l3(q15) }`, `state { stage(uint32),
  level(q15) }`. `node.c`: a per-note rate/level envelope with *signed* Q15
  level targets (a pitch offset), retriggered on every note-on and gated by `on`.
  Host test: `test_generate.py` `_release_tail`.
- **`route`** — `node.json`: `ins { alg(control), a b c d(audio) }`,
  `outs { mod2 mod3 mod4 car(audio) }`, `params {}`. `node.c`: an 8-algorithm
  `switch` over the routing matrix (weights 0/1, Q15 `0`/`32767`) — a 1-weight is
  `fm1_q15_mul(x, 32767)` (folded by the compiler to a 32-bit shift/sub/add), a
  0-weight is dropped — instead of four `fm1_route4` calls (16 multiplies + 16
  table loads). Host test: the type-p-fm1 render + routing-table assertions in
  `test_generate.py`.
- **`algo`** — `node.json`: `ins {}`, `outs { alg(control) }`,
  `params { algorithm(uint32) }`. `node.c`: echoes `algorithm` (clamped to the 8
  routings) as `alg` (control rate). Host test: `test_generate.py` algorithm +
  separation assertions.
- **`route4`** / **`mix4`** — the general primitive (row mixer) + 4-sum. Host
  test: `test_generate.py` `ROUTE4_TEST`.
- **`lfo`** — `node.json`: `ins {}`, `outs { cv(control) }`,
  `params { rate(q32), depth(q15) }`, `state { phase(phase) }`. `node.c`:
  `phase += rate * CONTROL_BLOCK` (the emitted macro) then `cv = fm1_sin(phase) ×
  depth`. Host test: `test_generate.py` `LFO_TEST` (oscillates, non-constant).
- **`mute`** — `node.json`: `ins { audio }`, `outs { audio }`,
  `params { mute(uint32) }`. `node.c`: `mute ? 0 : in`. Host test:
  `test_generate.py` `MUTE_TEST` (`_mute_gates`: unmuted non-silent, muted silent).

### HAL helpers (`firmware/hal/fm1_math.h`)

- `FM1_MATH_INLINE int32_t fm1_sin_wave(uint32_t phase, uint32_t ws)` — the
  12-waveform OPZ + OPL union (0–7 OPZ, 8–11 OPL-only).
  `FM1_MATH_INLINE`, so a `.dsp_text` call never goes XIP.
- `FM1_MATH_INLINE int32_t fm1_route4(const int16_t *w, int32_t a, int32_t b,
  int32_t c, int32_t d)` — `Σ a·w0 + b·w1 + c·w2 + d·w3` via `fm1_q15_mul`.

## 3. Data layout

- **Per-voice state:** SoA (the generator default) — `opN_ph_phase[NVOICE]`,
  `opN_eg_level[NVOICE]`, `opN_lfo_phase[NVOICE]` (the per-op tremolo LFO),
  `dN_prev[NVOICE]`, etc.
- **Single-instance control state:** the global `svf`/`wavefolder` scalars.
- **Per-voice control state:** `penv`/`plfo`/`psum` (the per-note pitch envelope,
  the per-part vibrato LFO, and their sum), run per voice in the control prologue.
- **Section placement:** per-sample bodies in `.dsp_text`; `routing` + the
  quarter-sine tables `const` (XIP); engine state `.cpu1_bss`.

## 4. State publication

- **One writer per shared value:** params are single-writer (`set_param` writes
  the shared slot; the render reads it). The voice allocator owns `gate`/`inc`;
  the envelope owns its `stage`/`level`.

## 5. Host-test hook

- **`umetate/test_generate.py`** — `DX_ENV` (envelope), `ROUTE4_TEST`
  (route4+mix4), the routing-table assertions, and the type-p-fm1 patch render
  (non-silent → decays) + panel resolve. Run:
  `python3 -m umetate.test_generate` (or the whole gate: `umetate deep-check
  --all`).

## 6. Forbidden dependencies (re-check)

- [x] No allocation, `float`/`double`, or 64-bit division in the audio path
      (all integer Q15/Q16/Q32; `fm1_*` helpers).
- [x] No display, flash, logging, blocking, or per-sample dispatch (the
      generator inlines one fused monomorphic render).
