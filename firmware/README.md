# RIB — the starter firmware contract

RIb is the umetate starter firmware: a Dinghy/Felucca-derived, source-owned base
for the M-VAVE FM-1 and SMK-37. This file is the **code-level contract**: the API
your app writes against, the numeric conventions, and the readability/perf rules.
It is not a tutorial (see `docs/tutorial.md`) and not a status file (see
`docs/roadmap.md`).

Raw registers live in `hal/` only. Everything your app touches is a named helper
below. Read this once; it is short and complete.

## 1. The app contract

Your app supplies two functions, nothing else is required:

```c
static void app_audio(int32_t *out, uint32_t n);   /* audio ISR: fill n=256 stereo frames @ 44.1 kHz */
static void app_main(void);                        /* main loop; never returns */
```

- `app_audio` runs in the audio interrupt, ~5.8 ms per block. `out` is
  `L R L R …`, already zeroed; **add** your sound to it. Full scale is ±32767
  (Q15); more is clipped by the platform. Callback budget target: ≤ 2.9 ms (50%).
- `app_main` must call `platform_poll()` often (USB + watchdog; never less than
  once every couple of seconds). It reads the panel and MIDI and draws.

## 2. The platform API

All helpers are `fm1_`-prefixed and board-agnostic; SMK-37 extras are behind
`BOARD_SMK37`.

### Time

| Call | Meaning |
| --- | --- |
| `fm1_ms` | milliseconds since power-on (`volatile uint32_t`) |
| `fm1_ticks()` / `fm1_micros()` | free-running 24 MHz counter / microseconds (`FM1_TICKS_PER_US` = 24) |
| `fm1_delay_ms(ms)` / `fm1_delay_us(us)` | short busy waits (they do **not** poll) |

Time the callback: `t0 = fm1_ticks(); …; (fm1_ticks() - t0) / FM1_TICKS_PER_US`.

### Input (scanned at 10 kHz, debounced)

| Call | Meaning |
| --- | --- |
| `fm1_in.notes` / `fm1_in.buttons` | held keys (bit 0 = F3 … 26 = G5) / buttons (bit = `BTN_*`) |
| `fm1_input_edges(&released)` / `fm1_input_note_edges()` | edges since the last call |
| `fm1_enc_take(ENC_x)` | detents since the last call (+ = clockwise) |
| `fm1_adc_read(FM1_ADC_MASTER)` / `…_BATT` | MASTER knob (0..1023) / battery raw |

### LEDs / screen / MIDI / storage

| Area | Calls |
| --- | --- |
| LEDs | `fm1_led_key(id, on)`, `fm1_led_key_glow(id, on)`, raw layers `fm1_led[]` |
| Screen | `lcd_fill(x,y,w,h,c)`, `draw_text_box(...)`, canvas `cv_begin/cv_rect/cv_line/cv_pset/cv_text/cv_blit`, `FONT_S`/`FONT_L` |
| MIDI | `midi_get(&st,&d1,&d2)` (1 = USB, 2 = TRS), `midi_send(st,d1,d2)` (main loop only) |
| Storage | `settings_load/save`, `blob_load/save(i,..)`, `slot_load/save(i,..)` — each with magic + length + CRC |

### The SMK-37 (behind `BOARD_SMK37`)

`fm1_in.key_vel[]` (velocity), `smk_extkey_take()` (outer keys), `fm1_in.keys`
(37 keys), `padled_set(pad,r,g,b)` / `padled_flush()`, `fm1_in.fader[0..3]`,
`fm1_in.wheel[0..1]` + `smk_pw_bend()`, `fm1_in.pad_press[]`. The store uses an
owner tag; give your fork its own `DATA_FAMILY`.

## 3. Numeric conventions

- **Q15 levels** (×32768, ±32767), **Q12/Q16 gains and coefficients**,
  **32-bit phase accumulator**: `inc = f * 2^32 / FS`, `ph += inc`.
- **No `float`/`double` in the integer baseline**; `--dsp float` is single-precision
  only and confined to `rib_dsp.c`. **No `double` anywhere on target.**
- **No 64-bit division/modulo** (`int64_t * x` is fine; `a / b` on 64-bit needs
  `__udivdi3` and the link fails). Shift, or divide 32-bit.
- **Division by zero does not trap** (the trap is off) — it gives a wrong value.
  Test your divisors.
- **Compute constants on the host; write them as literals** (`INC_C9 = …`).
- Envelopes, filter coefficients, and LFOs update at **block rate** (16–32
  frames), not per sample, unless measured.

## 4. Naming

| Kind | Case | Example |
| --- | --- | --- |
| functions | `snake_case`, layer prefix | `fm1_ticks()`, `rib_render()`, `synth_dsp_render()` |
| macros / constants / enum values | `UPPER_SNAKE`, shared prefix | `FM1_TICKS_PER_US`, `BTN_OCT_DOWN`, `ENC_KNOB1` |
| structs | `snake_case` (no `_t`: POSIX-reserved) | `fm1_input`, `voice_state` |
| file-local | `static` + `snake_case` | `static void ramp_coeff(void)` |

Prefixes: `fm1_` = board/HAL, `rib_` = reference app, `<synth>_` = user synth
(from the scaffold name). On-device identity strings are **frozen** (`_990`).

## 5. The ten rules (readable *and* fast)

Adapted from the NASA/JPL "Power of 10" (Holzmann, 2006). Each is enforced by
`umetate lint --c`, `.clang-tidy`, or review:

1. **Simple control flow.** No `goto`, no `setjmp`/`longjmp`, no recursion.
2. **Bounded loops.** Every loop has a named upper bound; no `while (1)` inside
   the audio callback.
3. **No heap after init.** `static`/`.pool` buffers only; nothing allocates in
   the audio path.
4. **Small functions** (≤ ~60 lines). Factor; `static` + `inline` let the
   compiler remove the call under `-O3`/LTO.
5. **Assert invariants.** Ranges, divisors, buffer bounds. Side-effect-free;
   compiled out of the release profile.
6. **Smallest scope.** Declare at point of use; `static` for file-locals.
7. **Check returns and parameters.** Non-void callers check; functions validate
   their inputs.
8. **Limited preprocessor.** Header guards + complete-unit macros only. No token
   pasting, no variadic/recursive macros. Conditional compilation only for
   `BOARD_SMK37` and `--dsp`/`--clock` seams.
9. **Restricted pointers and dispatch.** One dereference level; no
   pointer-in-typedef/macro; **no indirect dispatch per sample** in the hot loop.
   Runtime-selectable models dispatch at **block rate** (a `switch`, or a
   `static const` table indexed once per block), never per sample; prefer
   **model-as-data** (one monomorphic loop reading a chosen table). The only
   per-call function pointers are the fixed platform seams
   `app_audio`/`app_main`/`LCD_IDLE`.
10. **Warnings-as-errors from day one**, plus the static analyzers, daily.

**Data-layout rule (perf + readability):** per-voice parallel state is
**SoA** — e.g. `int16_t phase[NVOICE]`, `int16_t env[NVOICE]` as separate arrays
iterated together — because the hot loop walks one field across all voices.
Single-instance control state may be a plain struct. Say which, in a comment,
next to the declaration. `const` tables (`wavetables`, fonts) are XIP and cost no
RAM.

### 5.1 Runtime-selectable models (dispatch)

The hot inner loop must stay **monomorphic** (one model's code, inlined, no
per-sample branch). Three tiers, in order of preference:

1. **Model as data.** When models differ only by waveform, they are tables, not
   code — one oscillator loop reads whichever table a voice points at; selecting
   a model is `wave[v] = MODEL_SAW` at note-on:

   ```c
   static int32_t phase[NVOICE];   /* 32-bit phase */
   static uint8_t  wave[NVOICE];   /* table index, set at note-on */

   static inline void osc_render(int32_t *out, uint32_t n)
   {
       for (uint32_t v = 0; v < NVOICE; v++) {
           const int16_t *w = WAVES[wave[v]];   /* data read, not an indirect call */
           int32_t ph = phase[v];
           for (uint32_t f = 0; f < n; f++) { out[f*2] += w[ph >> 22]; ph += inc[v]; }
           phase[v] = ph;
       }
   }
   ```

2. **Block-rate switch.** When models differ in algorithm, dispatch once per
   block — one branch per ~256 samples, not the hot path:

   ```c
   switch (model) {                 /* one branch per BLOCK */
   case MODEL_BLIT:  blit_render(out, n);  break;
   case MODEL_FM:    fm_render(out, n);    break;
   case MODEL_TABLE: osc_render(out, n);   break;
   }
   ```

   A dense `switch` compiles to a jump table; each `*_render` is `static inline`.

3. **Per-model buckets.** A polyphonic mix of different models loops models
   outer / voices inner; the indirect call is per model per block:

   ```c
   for (int m = 0; m < N_MODELS; m++)
       if (model_count[m]) render_fn[m](out, voices[m], n);  /* once per block */
   ```

   `render_fn` is a `static const` table indexed once per block — allowed because
   it is per-block, never per-sample.

These three tiers are the **primitive-level** techniques. At the framework level
(see `../docs/roadmap.md` §3.1), runtime model selection is a *graph* concern — a
`select` node, or separate patches — and the generator emits the block-rate
`switch`/buckets from that switchable topology, so the user never hand-writes the
dispatch. On the pi32v2 (I-cache, weak branch prediction) monomorphic loops matter
more than on a desktop: an indirect call per sample thrashes I-cache and mispredicts.

## 6. The audio callback "never" list

Inside `app_audio` (and anything it calls): **no** display, **no** flash, **no**
logging/`printf`, **no** blocking/waiting, **no** allocation, **no** division by a
runtime value without a guard. One writer per shared value, or a snapshot
protocol; `volatile` alone is not atomicity.

## 7. Tooling

- `.clang-format` (repo root) — formatting, applied by `umetate fmt`.
- `.clang-tidy` (repo root) — UB/style/bug checks, run by `umetate lint --c`
  against the portable C.
- `umetate lint --c` also runs the target-specific checks: MAXP/buffer/descriptor
  bounds, UAC out-of-object access, ROM-address constants, HAL-only MMIO,
  flash-busy call graph, no `double`/64-bit-div/allocation in the DSP TU, and the
  image/RAM/pool budget.

## 8. The SMK-37

Same chip, 37-key velocity keybed, 16 RGB pads, 4 faders (+ bank), 8 encoders
(+ bank), pitch/mod wheels, outer keys. `--board smk37` builds the same app
unchanged. The store uses an owner tag; the board layer (`board/`) is gated by
`BOARD_SMK37`; the FM-1 build stays byte-identical.
