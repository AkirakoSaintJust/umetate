<!-- GENERATED - do not edit. Source: firmware/README.md. Regenerate with `python -m umetate._skill generate`. -->

# RIB: the starter firmware contract

RIB is umetate's starter firmware for the M-VAVE FM-1 and SMK-37, derived from
Dinghy/Felucca and maintained here as source. This file defines the **code-level
contract**: the app API, numeric conventions, and rules for readable, fast code.
For a guided introduction, see `docs/tutorial.md`, and for project status, see
`docs/roadmap.md`.

Only `hal/` accesses raw registers, so app code uses the named helpers documented
below.

## 1. The app contract

`src/rib.c` is the **frozen framework**: the platform, the UI kit, and the synth
services (`presets.c`, `synth_sysex.c`, `synth_midi.c`, `synth_runtime.c`). The
**app half** is included at its bottom, the shipped demo (`src/rib_app.c`, a sine
wave on the keys) or a synth project's `app.c` (the `umetate build --synth <dir>`
composition, `-DUMETATE_SYNTH_APP=1`, resolved from `gen/`). An app provides two
functions (plus the UI hooks):

```c
static void app_audio(int32_t *out, uint32_t n);   /* audio ISR: fill n=256 stereo frames @ 44.1 kHz */
static void app_main(void);                        /* main loop; never returns */
static void app_idle(void);                        /* runs while the screen's DMA draws (MIDI in) */
```

- `app_audio` runs in the audio interrupt, once per 256-frame block (~5.8 ms).
  The interleaved stereo buffer (`L R L R …`) is already zeroed, **add** your
  samples to it. Full scale is ±32767 (Q15), the platform clips larger values.
  Keep the callback under 2.9 ms (50% of the block period).
- `app_main` reads the panel and MIDI and updates the display. It must call
  `platform_poll()` regularly to service USB and the watchdog, at least once every
  couple of seconds.

## 2. The platform API

The board-agnostic helpers use the `fm1_` prefix. SMK-37-specific helpers are
available when `BOARD_SMK37` is defined.

### Time

| Call | Meaning |
| --- | --- |
| `fm1_ms` | milliseconds since power-on (`volatile uint32_t`) |
| `fm1_ticks()` / `fm1_micros()` | free-running 24 MHz counter and microseconds (`FM1_TICKS_PER_US` = 24) |
| `fm1_delay_ms(ms)` / `fm1_delay_us(us)` | short busy waits, these calls do **not** poll |

To time the callback, take a counter reading before and after it, then divide
the difference by `FM1_TICKS_PER_US`: `t0 = fm1_ticks(); …; (fm1_ticks() - t0) / FM1_TICKS_PER_US`.

### Input

The input scanner samples controls at 10 kHz and debounces them.

| Call | Meaning |
| --- | --- |
| `fm1_in.notes` / `fm1_in.buttons` | held keys (bit 0 = F3 through bit 26 = G5) and held buttons (bit = `BTN_*`) |
| `fm1_input_edges(&released)` / `fm1_input_note_edges()` | input edges since the previous call |
| `fm1_enc_take(ENC_x)` | encoder detents since the previous call, positive means clockwise |
| `fm1_adc_read(FM1_ADC_MASTER)` / `…_BATT` | MASTER knob value (0–1023) and raw battery reading |

### LEDs / screen / MIDI / storage

| Area | Calls |
| --- | --- |
| LEDs | `fm1_led_key(id, on)`, `fm1_led_key_glow(id, on)`, and raw `fm1_led[]` layers |
| Screen | `lcd_fill(x,y,w,h,c)`, `draw_text_box(...)`, canvas calls `cv_begin/cv_rect/cv_line/cv_pset/cv_text/cv_blit`, and `FONT_S`/`FONT_L` |
| MIDI | `midi_get(&st,&d1,&d2)` (1 = USB, 2 = TRS), `midi_send(st,d1,d2)` (main loop only) |
| Storage | `settings_load/save`, `blob_load/save(i,..)`, `slot_load/save(i,..)`, each record has a magic value, length, and CRC |

### The SMK-37 (behind `BOARD_SMK37`)

The SMK-37 adds velocity in `fm1_in.key_vel[]`, 37-key state in `fm1_in.keys`,
and outer-key events from `smk_extkey_take()`. Use `padled_set()` and
`padled_flush()` for pad LEDs, `fm1_in.fader[0..3]` for faders, and
`fm1_in.wheel[0..1]` plus `smk_pw_bend()` for the wheels. Pad presses are in
`fm1_in.pad_press[]`. The store uses an owner tag, assign your fork its own
`DATA_FAMILY`.

## 3. Numeric conventions

- Represent **levels in Q15** (scale by 32768, clamp to ±32767) and gains or
  coefficients in **Q12/Q16**. Use a 32-bit phase accumulator:
  `inc = f * 2^32 / FS`, then `ph += inc` per sample.
- Keep the integer baseline free of `float` and `double`. The optional
  `--dsp float` path uses single precision and stays in `rib_dsp.c`. The target
  does not support `double`.
- Do not divide or take a modulo of 64-bit values. Multiplication such as
  `int64_t * x` is fine, but 64-bit division needs `__udivdi3` and will fail at
  link time. Shift or divide 32-bit values instead.
- Division by zero does not trap on this target, it returns a wrong result.
  Validate divisors before using them.
- Calculate constants on the host and put the resulting literals in the firmware,
  for example `INC_C9 = …`.
- Update envelopes, filter coefficients, and LFOs at **block rate** (every 16–32
  frames), not every sample, unless measurements justify the higher rate.

## 4. Naming

| Kind | Convention | Example |
| --- | --- | --- |
| functions | `snake_case` with a layer prefix | `fm1_ticks()`, `rib_render()`, `synth_dsp_render()` |
| macros, constants, enum values | `UPPER_SNAKE` with a shared prefix | `FM1_TICKS_PER_US`, `BTN_OCT_DOWN`, `ENC_KNOB1` |
| structs | `snake_case`, avoid `_t`, which POSIX reserves | `fm1_input`, `voice_state` |
| file-local names | `static` and `snake_case` | `static void ramp_coeff(void)` |

Use `fm1_` for board/HAL functions, `rib_` for the reference app, and
`<synth>_` for synth code (using the scaffold name). On-device identity strings
are **frozen** at `_990`.

## 5. The ten rules (readable *and* fast)

These rules are adapted from NASA/JPL's "Power of 10" (Holzmann, 2006), and
`umetate lint --c`, `.clang-tidy`, and code review check them:

1. **Keep control flow simple.** Do not use `goto`, `setjmp`/`longjmp`, or
   recursion.
2. **Bound every loop.** Give each loop a named upper limit. Never use an unbounded
   `while (1)` in the audio callback.
3. **Do not allocate after initialisation.** Use `static` or `.pool` buffers, the
   audio path must not allocate.
4. **Keep functions small** (about 60 lines or fewer). Factor longer functions.
   `static inline` lets `-O3`/LTO remove the call where appropriate.
5. **Assert invariants.** Check ranges, divisors, and buffer bounds. Assertions
   must have no side effects and are compiled out of the release profile.
6. **Limit scope.** Declare variables where they are used and mark file-local
   names `static`.
7. **Check inputs and return values.** Validate function parameters, and make
   callers check every non-void result.
8. **Keep preprocessor use limited.** Use header guards and complete-unit macros.
   avoid token pasting and variadic or recursive macros. Conditional compilation
   is reserved for `BOARD_SMK37` and the `--dsp`/`--clock` seams.
9. **Limit pointers and dispatch.** Use at most one level of indirection, do not
   hide pointers in typedefs or macros. The hot loop must not use **indirect
   dispatch per sample**. Select models at **block rate**, with a `switch` or a
   `static const` table indexed once per block. Prefer **model-as-data**: one
   monomorphic loop reads the selected table. The only per-call function pointers
   are the fixed platform seams `app_audio`, `app_main`, and `LCD_IDLE`, and the
   synth services' contexts (`synth_midi_ctx`, `synth_sysex_ctx`,
   `synth_runtime_ctx`, set up once at boot, never in the hot loop).
10. **Treat warnings as errors from the start.** Run the static analysers daily.

**Data layout:** Store parallel per-voice state as **SoA**: separate arrays such
as `int16_t phase[NVOICE]` and `int16_t env[NVOICE]`, iterated together. The hot
loop then walks one field across all voices. A single-instance control state can
use a plain struct. Add a comment by each declaration to explain the choice.
`const` tables such as wavetables and fonts are XIP and use no RAM.

### 5.1 Runtime-selectable models (dispatch)

Keep the hot inner loop **monomorphic**: inline one model's code, with no
per-sample branch. Prefer these approaches in order:

1. **Model as data.** When models differ only by waveform, they are tables, not
   code, one oscillator loop reads whichever table a voice points at, selecting
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
   block, one branch per ~256 samples, not the hot path:

   ```c
   switch (model) {                 /* one branch per BLOCK */
   case MODEL_BLIT:  blit_render(out, n);  break;
   case MODEL_FM:    fm_render(out, n);    break;
   case MODEL_TABLE: osc_render(out, n);   break;
   }
   ```

   A dense `switch` compiles to a jump table, each `*_render` is `static inline`.

3. **Per-model buckets.** A polyphonic mix of different models loops models
   outer / voices inner, the indirect call is per model per block:

   ```c
   for (int m = 0; m < N_MODELS; m++)
       if (model_count[m]) render_fn[m](out, voices[m], n);  /* once per block */
   ```

   `render_fn` is a `static const` table indexed once per block, allowed because
   it is per-block, never per-sample.

These techniques apply to individual DSP primitives, whilst at the framework level
runtime model selection belongs in the graph (see `../docs/roadmap.md` §3.1): use
a `select` node or separate patches. The generator emits the block-rate switch or
buckets, so users do not write dispatch code themselves. On the pi32v2, with its
small instruction cache and weak branch prediction, monomorphic loops matter more
than on a desktop. An indirect call per sample can thrash the cache and mispredict.

## 6. The audio callback "never" list

Inside `app_audio` and every function it calls, do not access the display or flash,
log or print, block or wait, allocate memory, or divide by a runtime value without
a guard, and give each shared value one writer or use a snapshot protocol.
`volatile` alone does not make an access atomic.

## 7. Tooling

- `.clang-format` (repo root), formatting, applied by `umetate fmt`.
- `.clang-tidy` (repo root), UB/style/bug checks, run by `umetate lint --c`
  against the portable C.
- `umetate lint --c` also checks target-specific constraints: MAXP, buffer and
  descriptor bounds. UAC object access. ROM-address constants. HAL-only MMIO, the
  flash-busy call graph, no `double`, 64-bit division, or allocation in the DSP
  translation unit, and image, RAM, and pool budgets.

## 8. The SMK-37

The SMK-37 uses the same chip and adds a 37-key velocity keybed, 16 RGB pads,
four faders and eight encoders (both banked), pitch and modulation wheels, and
outer keys. Build with `--board smk37`, and the app source stays the same. The board
layer (`board/`) is guarded by `BOARD_SMK37`, and the store uses an owner tag. The
FM-1 build remains byte-identical.
