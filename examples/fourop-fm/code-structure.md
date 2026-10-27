# Custom code structure + interface — fourop-fm

> Everything beyond the declarative `patch.json`/`panel.json`. The fourop-fm
> dogfood is mostly *library*: it added a handful of nodes/macros + two HAL
> helpers, then declared the synth. No hand-written `dsp.c` — the generator emits
> it.

## 1. Files

- **Created** (nodes/macros the dogfood shipped, in the library):
  - `modules/nodes/dx_env/` — the DX rate/level envelope (`node.json` + `node.c`).
  - `modules/nodes/mix4/` — 4-input summer.
  - `modules/nodes/route4/` — the general routing-matrix row mixer.
  - `modules/nodes/route/` — the 4-op FM router (one `algorithm` param, 4 rows).
  - `modules/macros/fm_op/` — the operator (`macro.json`).
  - `examples/fourop-fm/{patch.json,panel.json,synth-brief.md,dsp-algorithm.md,code-structure.md,control-map.md,README.md}`.
- **Modified**:
  - `modules/nodes/osc/` — added the `waveform` param (8 waveforms).
  - `modules/nodes/vca/` — added the `level` param (Q15 gain).
  - `modules/nodes/phasor/` — the `fm` input now scales `<<16` (full-scale = ±π
    phase swing).
  - `firmware/hal/fm1_math.h` — `fm1_sin_ws` (the 8-waveform bit trick),
    `fm1_route4` (the 4-weight Q15 dot product).
  - `umetate/_tables.py` — the `routing` table kind (the 7-algorithm matrix).
- **Forbidden to touch:** HAL registers, `platform.c` services, the loader,
  `uboot.boot`/`isd_config.ini` — none were touched.

## 2. The seam (library path)

No hand-written `dsp.c`: `generate(patch)` emits `<synth>_dsp_*` from the patch
(`docs/roadmap.md` §12.1). The new code is nodes/macros + the two HAL helpers.

### New nodes

- **`dx_env`** — `node.json`: `ins { gate(event, default voice_gate[v]) }`,
  `outs { cv(control) }`, `params { r1 r2 r3 r4(q16), l1 l2 l3(q15) }`,
  `state { stage(uint32), level(q15) }`. `node.c`: a 5-stage one-pole state
  machine (control rate). Host test: `test_generate.py` `DX_ENV`.
- **`route`** — `node.json`: `ins { a b c d(audio) }`,
  `outs { mod2 mod3 mod4 car(audio) }`, `params { which(table), algorithm(uint32) }`.
  `node.c`: four `fm1_route4` calls reading rows 1–4 of the routing table.
  Host test: the fourop-fm render + routing-table assertions in
  `test_generate.py`.
- **`route4`** / **`mix4`** — the general primitive (row mixer) + 4-sum. Host
  test: `test_generate.py` `ROUTE4_TEST`.

### HAL helpers (`firmware/hal/fm1_math.h`)

- `FM1_MATH_INLINE int32_t fm1_sin_ws(uint32_t phase, uint32_t ws)` — the
  quarter-sine bit trick. `FM1_MATH_INLINE`, so a `.dsp_text` call never goes
  XIP.
- `FM1_MATH_INLINE int32_t fm1_route4(const int16_t *w, int32_t a, int32_t b,
  int32_t c, int32_t d)` — `Σ a·w0 + b·w1 + c·w2 + d·w3` via `fm1_q15_mul`.

## 3. Data layout

- **Per-voice state:** SoA (the generator default) — `opN_ph_phase[NVOICE]`,
  `opN_eg_level[NVOICE]`, `dN_prev[NVOICE]`, etc.
- **Single-instance control state:** the global `svf`/`wavefolder`/`vca` scalars.
- **Section placement:** per-sample bodies in `.dsp_text`; `routing` + the
  quarter-sine tables `const` (XIP); engine state `.cpu1_bss`.

## 4. State publication

- **One writer per shared value:** params are single-writer (`set_param` writes
  the shared slot; the render reads it). The voice allocator owns `gate`/`inc`;
  the envelope owns its `stage`/`level`.

## 5. Host-test hook

- **`umetate/test_generate.py`** — `DX_ENV` (envelope), `ROUTE4_TEST`
  (route4+mix4), the routing-table assertions, and the fourop-fm patch render
  (non-silent → decays) + panel resolve. Run:
  `python3 -m umetate.test_generate`.

## 6. Forbidden dependencies (re-check)

- [x] No allocation, `float`/`double`, or 64-bit division in the audio path
      (all integer Q15/Q16/Q32; `fm1_*` helpers).
- [x] No display, flash, logging, blocking, or per-sample dispatch (the
      generator inlines one fused monomorphic render).
