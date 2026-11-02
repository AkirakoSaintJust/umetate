# DSP implementation study

This study looks at how Mutable Instruments, SuperCollider, Pure Data, Dexed
(msfa), Nuked, ymfm, and SAPF implement DSP. The goal is practical: identify
synthesis techniques and component interfaces that fit umetate's node library.
This is reference material, not a status tracker, `docs/roadmap.md` owns project
status. It supports §12.5 of that roadmap.

---

## 1. The component interface (three shapes)

Across these projects, the basic unit is a stateful DSP object with a process
function. Its interface usually takes one of three forms:

| Project             | Unit                        | Interface                                                 | Rate                           | Notes                                                                                         |
| ------------------- | --------------------------- | --------------------------------------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------- |
| Mutable Instruments | `Engine` / `Voice` subclass | `Process(const Block& in, const Block& out, size_t size)` | block                          | `Parameter` knobs (curve lookup), fixed-point `stmlib::`, per-voice classes, no heap in audio |
| SAPF                | `Sapf` subclass             | `virtual process(...)`                                    | block                          | inheritance, the only polymorphic-per-call one                                               |
| SuperCollider       | `UGen`                      | `next_a(n)` / `next_k(n)` / `next_i()`                    | per-sample (a) / per-block (k) | `.ar`/`.kr` rate polymorphism, graph + topological sort, `LocalIn`/`Out` feedback             |
| Pure Data           | tilde object                | `t_int *perform(t_int *w)`                                | block (64)                     | buffers in `w[2..]`, `dsp_add` registers the routine, message↔signal split                    |
| Dexed (msfa)        | `Dx7Note` + 6 operators     | `compute(int32_t *buf, …)`                                | per-sample → block             | 32 algorithms, rate/level envelopes, 1-sample operator feedback                               |
| Nuked               | `OPN2` core                 | `OPN2_Generate(OPN2*, int16_t *l, int16_t *r)`            | per-sample                     | bit-accurate integer, log/exp/sin tables, register writes                                     |
| ymfm                | `fm_operator` / `engine`    | `generate(int32_t *out, uint32_t n)`                      | per-sample → block             | templated operator/engine, shared core + per-chip tables                                      |

The trade-off is straightforward. Block processing (`process(in, out, size)`) is
easy to test and can support vectorization. Per-sample generation (`next` or
`generate`) makes one-sample feedback natural. SAPF's inheritance puts a virtual
dispatch in the hot loop. umetate combines the useful parts: nodes expose a block
`process(ctx, n)` for standalone tests, while the fused render inlines per-sample
work where FM feedback needs it (`docs/roadmap.md` §12.5).

---

## 2. Oscillators

### 2.1 Phase accumulator + table (the workhorse)

```c
uint32_t phase, inc;                    /* Q32; inc = f * 2^32 / FS, set at note-on */
phase += inc;
uint32_t idx  = phase >> (32 - LOG2_N); /* table of 2^LOG2_N samples */
uint32_t frac = (phase << LOG2_N) >> 16;/* fractional part, Q16 */
out = a + (((b - a) * (int32_t)frac) >> 16);   /* linear interpolation */
```

Compute **`inc` once per note**, or once per control tick when pitch is modulated.
do not recalculate it per sample. A 512–2048-sample table with linear interpolation
produces about 0.1% THD at 512, which is inaudible. A sine table needs no
anti-aliasing because it contains no harmonics to fold.

### 2.2 PolyBLEP (band-limited saw/square/pulse, cheap anti-aliasing)

MI's `PolyblepOscillator` uses the **polyBLEP** correction, a 2nd-order polynomial
applied around each discontinuity. It costs about four extra operations per sample
and needs no oversampling:

```c
float poly_blep(float t, float dt) {          /* t = phase in [0,1), dt = inc */
    if (t < dt)      { t /= dt;       return t + t - t * t - 1.0f; }   /* = 2t - t² - 1 */
    if (t > 1 - dt)  { t = (t - 1)/dt; return t * t + t + t + 1.0f; } /* = t² + 2t + 1 */
    return 0.0f;
}
/* saw:    out = 2*t - 1 - poly_blep(t, dt);
   square: out = (t < 0.5f ? 1 : -1) + poly_blep(t, dt) - poly_blep(fract(t+0.5f), dt);
   triangle: the polyBLEP'd square through a leaky integrator, one extra state. */
```

The correction has the same shape at each discontinuity, only its phase changes.
For a **pulse (PWM)**, move the second correction to the pulse width `pw`:

```c
/* pulse: v = (ph < pw ? 1 : -1); p2 = (ph + 1 - pw) mod 1;
   out = v + poly_blep(ph, dt) - poly_blep(p2, dt); */
```

Keep `pw` away from 0 and 1 so the two BLEPs do not overlap and create a narrow-
pulse artifact. The 2nd-order form above suppresses aliasing up to roughly a 2 kHz
fundamental. Third- and fourth-order Lagrange or B-spline corrections extend that
range, a 2-tap EQ FIR (`b0 + b1·z⁻¹ + b0·z⁻²`) can flatten the passband (Välimäki
et al.). "Band-limited" therefore describes a family of approaches, not one fixed
algorithm.

The triangle's leaky integrator is `y = (1 − 1/1024)·y + slope·x` with `slope =
inc/2^16` (note-derived). It is not the single-coefficient `y += k·(x−y)` form,
because a single `k` must be both the integration gain and the leak: it either
droops low notes (k small) or goes unstable above ~7 kHz (k = 2π·dt, Finke's
original, which sndkit notes is unclear). Splitting the gain from a fixed 1/1024
leak keeps the output full-scale at any pitch, the price is a brief note-on
transient (the integrator starts from 0, decaying over ~2^10 samples) and a ~1 LSB
DC offset.

The same polynomial works in Q15/Q16. In fixed-point code, avoid the divide in
`poly_blep` (`t /= dt`): compute `1/dt` at **note-on**, while `dt` is constant.
The sample loop then multiplies instead of dividing. This is the default
"analog-ish" oscillator, the polynomial does the anti-aliasing.

### 2.3 Wavetable morphing (MI `VariableSawOscillator`)

Store one cycle in a wavetable and scan it with the phase accumulator. To change
the shape, cross-fade between precomputed tables. MI's variable saw, for example,
morphs between several saw shapes, it does not recompute the waveform.

### 2.4 Phase distortion (Casio CZ)

Phase distortion (PD) applies a **static** warp: the phase ramp passes through a
monotonic transfer function before the sine lookup. The CZ used a
cycle-synchronized modulator/carrier pair. Unlike FM's dynamic phase modulation,
this needs no delay. FM feedback does need a one-sample delay:

```c
uint32_t pd = transfer[phase >> (32 - LOG2_TF)];   /* warp the phase */
out = sin_table[pd >> (32 - LOG2_SIN)];
```

The CZ "resonance" waveforms are specific transfer functions (a cosine-shaped
bend). In umetate this is `osc` + a `phase_map` table, **data, not a new node**.

### 2.5 Vector phaseshaping (dynamic phase distortion)

Vector phaseshaping (VPS), described by Kleimola, Lazzarini, Timoney, and
Välimäki at DAFx-11, is the technique behind FAW's Circle². It extends classic PD
in three ways. First, the inflection point becomes a **2-D vector `p = (d, v)`**:
`d` sets the bend's x-position and `v` its y-position, classic PD fixes `v = 0.5`.
Second, the transfer can have **multiple, piecewise inflection points**. Third,
those points can be **modulated at audio rate**. VPS turns a static phase curve
into a dynamic shaper with multiple breakpoints:

```c
/* phase p in [0,1) -> a "bent" phase, then the sine. One inflection point (d,v):
   classic PD is the v = 0.5 fixed case; VPS frees both and adds breakpoints. */
/* control rate: s0 = v/d, s1 = (1-v)/(1-d)  — the two segment slopes, Q16 */
uint32_t p = phase >> 16;                                   /* Q16, 0..1 */
uint32_t q = p < d ? (p * s0) >> 16 : v + (((p - d) * s1) >> 16);
out = fm1_sin(q << 16);                                     /* shaped phase -> sine */
```

`v` is not confined to `[0,1]`: the phaseshaping allows `v` outside one cycle
(e.g. `v = 1.5`), and the shaped phase then wraps past the wavecycle. A negative
`v` saturates to 0, which is outside the paper's intent and not a wrap-backward.
The Q32 phase accumulator's uint32 wrap does the forward wrap for free. umetate's
`phase_shape` node keeps this: the slopes are int64 (a *multiply* by 2^15 / 2^17,
not a `<<`, because left-shifting a negative int64 is UB), and the shaped phase is
cast to uint32. `phase_dist` is the `v = 0.5` classic-PD special case.

For umetate, VPS is a **parameterized phase shaper**, not a fixed `phase_map`
table. Its transfer depends on `(d, v)`, which can be modulated through
`<param>_mod` inputs. Static shapes still fit the "shape = data" rule and use
tables. A dynamic shape needs a parameterized transfer, such as a macro or an `osc`
with `d` and `v` parameters. The DAFx-11 paper by Kleimola, Lazzarini, Timoney,
and Välimäki gives the equations. FAW's write-up also notes that dynamic phase
shaping needs band-limiting, as in §2.2, the VPS oscillators therefore build on
§2.1 and §2.2.

### 2.6 The FM operator's sine (ymfm / Dexed)

An FM operator advances phase by `inc = f·2^32/FS` and reads the sine table:
`phase += inc; out = sin_table[phase] * level`. Here, `level` is the rate/level
amplitude envelope. ymfm computes sine and attenuation in the **log domain** with
phase-to-sine and level-to-gain tables, making the operator a sequence of integer
table lookups. umetate uses the same basic pieces in its `phasor` + `osc` + `env` +
`vca` decomposition.

umetate's `fm_op` macro adds two FM-specific controls to that arrangement. The
**`ratio`** parameter is `note_derived`: `inc = note_to_inc(note)·ratio`, so
non-integer ratios such as 2.5 stay in tune. Optional **one-sample feedback** uses
`delay1` for operator self-modulation (the DX/TX "feedback" control). `detune` is
a small fixed offset to `inc`. An N-operator voice can therefore use N `fm_op`
macros, wired according to its algorithm, without new C code.

### 2.7 OPL's waveform bit trick and the OPZ waveforms

The OPL2/OPL3 generate eight waveforms from **one quarter-sine table and a
3-bit selector**. The selector changes the phase index with a few bitwise
operations before lookup, so no extra tables are needed:

```c
uint32_t idx = phase >> (32 - LOG2_QUARTER);   /* quarter-sine index */
if (ws & 1) idx ^= SIGN;                        /* absolute (rectified) */
if (ws & 2) idx &= HALF;                        /* half (mute the negative half) */
if (ws & 4) idx ^= PERIOD;                      /* alternate periods */
out = quarter_sine[idx];
```

The three selector bits combine sign inversion, half-cycle muting, and period
selection to produce eight waveforms. This is a form of **phase distortion**: a
stepwise transfer function. In umetate, `osc` can use a `phase_map` implemented as
a small bitwise function or an eight-entry table of masks and XOR patterns.

The **OPZ (YM2414, TX81Z/DX11) waveforms use a different set**. They derive from
sine and its square (`sin·|sin|`, the "trianglish" wave), plus half-, double-
frequency, and rectified variants. They are not the OPL bit-mask combinations.
ymfm's `opz_registers` lists sine, triangle, half-sine, half-triangle,
double-sine, double-triangle, double-half-sine, and double-half-triangle. The OPZ
and OPL sets share four shapes (sine, half-sine, double-sine, double-half-sine).
That leaves four OPL-only shapes, so umetate's `fm1_sin_wave` in `hal/fm1_math.h`
provides a 12-wave union: OPZ at indices 0–7 and rectified `|sin|`, pulse, square,
and saw at 8–11. The type-p-fm1 `dsp-algorithm.md` §`osc.waveform` documents the
mapping. Both chips offer eight choices, but the actual shapes and selection logic
differ.

### 2.8 Wavetables and cache

A single-cycle wavetable (512–2048 samples, or 1–4 KB) fits in cache and is read
**sequentially** as phase advances. Cache thrashing is a concern when many large
tables exceed the cache and voices jump between them, evicting one table's lines
with another's.

To reduce cache misses:

1. **Share a table across voices.** In the common sine case, every voice reads the
   same table sequentially, keeping its cache lines hot.
2. **Keep single-cycle tables small** (512–2048 samples). Linear interpolation
   gives about 0.1% THD at 512 samples, so larger tables rarely help.
3. **For morph sets, process voices by table.** Use SoA to render all voices
   against one table before switching, rather than interleaving reads from
   different tables for each voice.
4. **On the pi32v2, put hot tables in SRAM (`.cpu1_rodata`), not XIP.** The flash
   SFC runs at about 80 MHz on a 320 MHz CPU. An uncached XIP read costs roughly
   four times a cache hit, and the D-cache is small. See `docs/roadmap.md`
   §12.2.3.

Morphing between two tables is the case that makes cache placement matter most.
Keep both tables small and place them in `.cpu1_rodata` so they fit in SRAM.

### 2.9 Wavefolding (nonlinear waveshaping)

A wavefolder applies a **memoryless nonlinear transfer function** to each input
sample. As the input amplitude crosses the fold points, the output bends back and
adds harmonics. Unlike a filter, a wavefolder has no state. Here are several
fixed-point transfer functions:

- **Sine fold:** `out = sin(π·gain·x)`. For Q15 `x`, scale `gain·x` to a Q32
  phase and call `fm1_sin` (one LUT read and one multiply). This is the cheapest
  option.
- **Triangle fold:** fold `x` back into [−1,1] after it passes the rails, using a
  transfer such as `out = 2·|2·(x·f + 0.25) − 1| − 1`. This is linear and needs no
  trigonometry.
- **Polynomial / Chebyshev:** since `T_n(cos θ) = cos(nθ)`, a weighted sum
  `Σ c_n·T_n(x)` adds exact harmonics. For example, `T₃ = 4x³−3x` and
  `T₅ = 16x⁵−20x³+5x`. Horner's method evaluates them with a few multiplies.
- **Buchla 259:** five parallel op-amp folding stages and a dry path are summed
  together. The "timbre" control sets the fold amount. Each stage contributes a
  progressively folded copy of the signal.

For umetate, keep one wavefolder node and treat the transfer function as data: a
shape enum or a set of Chebyshev coefficients. The node applies the selected
transfer function.

The proposed umetate `wavefolder` node has `ins {audio}`, `outs {audio}`, and no
state. Its params are modulatable `amount` and `shape` (`sine | triangle | cheby`).
Sine folding uses `fm1_sin`, polynomial folding uses `fm1_madd_sat` or
`fm1_sat_add32` because the result can exceed the input range.

---

## 3. Envelopes

### 3.1 Segment / breakpoint (MI `Envelope`)

```c
typedef struct {
    uint32_t start_value, end_value;
    uint16_t duration;      /* in control ticks */
    int16_t  increment;     /* (end - start) / duration, precomputed */
    uint8_t  curve;         /* LINEAR | EXPONENTIAL */
} EnvelopeSegment;
```

At each control tick, update the value linearly (`value += increment`) or
exponentially (`value = start + (end-start) * exp_curve[tick]`). Advance when
`tick == duration`. Compute the increment when the segment starts, keeping division
out of the hot path. This flexible form supports arbitrary breakpoints and curves.
umetate's `env` node reads the segment definitions from a `segments` table.

### 3.2 Rate / level (DX7 / ymfm / Dexed)

Each stage has a **rate**, looked up as an increment in an exponential table, and
a **level**, the target value:
`env += rate_table[rate]; if (env >= level) next_stage;`. The rate is exponential.
the level is linear in the log domain. Convert it to amplitude with a table lookup
for `10^(-env/…)`. This uses fewer controls than a segment envelope and matches
what FM chips do, at about two table lookups per tick.

### 3.3 Exponential one-pole

`env += (target - env) * coeff` moves the envelope toward its target with a
one-pole filter. The result is a true exponential curve and costs one multiply-add.
It works well for a simple ADSR decay or release, segment envelopes can express
more shapes.

### 3.4 Efficiency lesson

Run envelopes at **control rate**, once per block or sub-block rather than per
sample. Precompute the increment or rate, each tick then takes only one or two
operations.

---

## 4. Filters

### 4.1 SVF (Chamberlin / MI `Svf`, and Simper's TDF2)

The **Chamberlin** form (used by MI's `Svf`) is a classic two-integrator filter:

```c
f = 2 * sinf(pi * cutoff / FS);          /* recompute at control rate */
q = 1.0f / resonance;
low  += f * band;
high  = in - low - q * band;
band += f * high;
/* low / band / high are the LP/BP/HP outputs; notch = low + high */
```

The Chamberlin form is simple, but can become unstable at high resonance.
**Simper's TDF2 form** is more stable under modulation and at high resonance. It
produces the same LP/BP/HP outputs using mix coefficients (`m0,m1,m2`):

```c
g  = tanf(pi * cutoff / FS);            /* k = 1/Q */
a1 = 1.0f / (1.0f + g * (g + k));
a2 = g * a1;
a3 = g * a2;
/* per sample: */
v3 = in - ic2eq;
v1 = a1 * ic1eq + a2 * v3;
v2 = ic2eq + a2 * ic1eq + a3 * v3;
ic1eq = 2 * v1 - ic1eq;
ic2eq = 2 * v2 - ic2eq;
out   = m0 * in + m1 * v1 + m2 * v2;    /* low = v2, band = v1, high = in - k*v1 - v2 */
```

For fixed-point code, use `g = 2·sin(π·fc/fs)` instead of `tan`. Simper notes
that sine is more accurate at low bit depth, and `fm1_sin` is already available.
`tan` is not free on the pi32v2. The TDF2 topology with an `fm1_sin`-derived `g`
is therefore the better fit. Both forms use two state variables and recompute one
coefficient per control tick, matching umetate's `svf` node (`z1`/`z2` state).

### 4.2 One-pole

`out += (in - out) * coeff` takes one multiply-add and has no resonance. Use it
for smoothing or inexpensive low-pass filtering, umetate's `one_pole` node uses
this form.

### 4.3 Biquad (RBJ cookbook)

A biquad uses five coefficients to place two poles and two zeros. It supports
more responses (LP/HP/BP/notch/peak/shelf) than the SVF, but recomputing its
coefficients takes more work (sin/cos) each control tick. Use one when the SVF's
fixed topologies are not enough.

### 4.4 Ladder (Moog / MI `LadderFilter`)

A ladder filter puts four one-pole stages in series and feeds the last stage back
to the first: `stage1 += (in - stage4 * res) * g; stage2 += (stage1 - stage2) * g; …`.
This is the classic character-filter topology. `res` sets feedback, `g` sets the
tan-based cutoff.

### 4.5 Low-pass gate (vactrol)

The Buchla 292 low-pass gate (LPG) combines a one-pole low-pass filter and a VCA.
Both respond to the **same** vactrol control (an LED and an LDR). Its nonlinear
decay gives the circuit its character:

- **Fast attack:** nearly instant to about 3 ms.
- **Long decay:** a VTL5C4 takes about **1–1.5 s** to move from fully open to
  semi-closed, then takes longer to close fully. Its LDR responds faster in bright
  light and slower in dim light, producing a non-exponential, ringing pluck tail.
- **Memory:** the response depends on recent history. Slow vactrols "remember"
  being lit, so repeated notes can decay differently.
- **Coupled cutoff and gain:** as the gate closes, the sound gets quieter and
  darker together. That gives the LPG its woody pluck.

Model the vactrol response as a **sum of two exponentials** (fast LED, slow LDR)
or as a one-pole with a power-law tail. MI's _Streams_ models it digitally: SHAPE
sets the vactrol's on/off response times, and MOD controls damping. Consult its
MIT-licensed source for the curve, credit the work, but do not copy its code.

The proposed umetate `lpg` node has `ins {audio, gate}`, `params {response (on/off
time), damping}`, and `outs {audio}`. Its state combines a one-pole filter with the
vactrol envelope. This is more than a `one_pole` + `env` macro: the nonlinear
decay and coupled cutoff/gain define the algorithm.

### 4.6 Formant filter (vowel formants)

A formant filter uses band-pass filters at vowel formant frequencies to shape a
harmonically rich source, such as a saw or pulse, into a vowel. Store the F1 and F2
frequencies, and optionally F3 for a more natural sound, as **data**:

| Vowel      | F1      | F2        | F3   |
| ---------- | ------- | --------- | ---- |
| a (father) | 660–850 | 1610–1700 | 2400 |
| i (heed)   | 240–270 | 2300–2400 | 3000 |
| u (boot)   | 250–300 | 595–870   | 2250 |
| e (bet)    | 390–400 | 2000–2300 | 2550 |

A `formant` macro in umetate could combine three or four parallel `svf`
band-pass filters and a `vowel` parameter that selects F1/F2/F3 values from a
`tables:` table. The filters can all use fixed-point arithmetic. The Kawai K5000's
"formant filter" uses the same idea.

### 4.7 Comb filter

A delay line with feedback (`out = in + fb·delay`) creates peaks and notches at
multiples of `1/delay`. umetate's `delayN` already has `time` and `fb` parameters
(§6.9) and breaks graph cycles, so a comb needs no separate node. A short `delayN`
with feedback also covers flanging, chorus, resonators, and Karplus–Strong.

---

## 5. Spectral oscillators (IFFT additive)

In additive synthesis, the spectrum (magnitude and phase per bin) is the data.
Run an inverse FFT at build time to create a single-cycle wavetable, then read it
like any other table oscillator (§2.1). The IFFT is **offline and precomputed**.
it never belongs in the per-block audio loop. A fixed-spectrum "spectral
oscillator" is therefore a wavetable, not a separate algorithm. umetate keeps an
`ifft` node for live spectral work. This is how SC's `IFFT` and Csound's `adsyn`
can reduce to table reads when the spectrum is fixed.

**Fixed-point caution:** kiss_fft's fixed-point build scales by `1/N` in both
directions to prevent overflow. A forward and inverse transform therefore scale
the result by `1/N²`, multiply back by `N²` when reconstructing a Q15 table. The
pi32v2 hardware FFT is **float** (`libFFT_pi32v2_OnChip.a`,
`flfft_core_pi32v2.c`). A 64-harmonic `ifft` wavetable can use that hardware at
control rate, with float isolated there, or use kiss_fft with its scaling handled.

---

## 6. Cross-cutting efficiency lessons

1. **Keep algorithms separate from their data.** The oscillator, envelope, or
   filter reads a table, segment list, spectrum, or transfer function. Projects
   generally precompute that shape rather than make a new algorithm for each one.
2. **Precompute at note-on or control rate.** Calculate `inc`, envelope
   increments, and filter coefficients before the sample loop. Do not divide in
   that loop.
3. **Use tables for expensive functions.** ymfm, Dexed, and Nuked implement the
   operator with integer table lookups for sine, exponential, and logarithm. This
   fits umetate's `hal/fm1_math.h` and JieLi hardware math.
4. **Make fixed-point formats explicit.** MI uses `int16`/`int32`, ymfm, Nuked,
   and Dexed combine integers with lookup tables. The same integer-first approach
   underlies umetate's Q-format notation.
5. **Match the delay to the feedback.** ymfm and Dexed use one-sample operator
   feedback. SC and Pd's `LocalIn`/`send~` are block-delayed. umetate uses
   `delay1` for FM feedback and `delayN` for longer delays.
6. **Run control faster than the block rate, but slower than the audio sample rate.** MI uses
   24-sample control blocks (~1.8 kHz). Pd uses 64. Audio-rate work dominates, so
   sub-block control adds roughly 1–8%.
7. **Keep allocation and virtual dispatch out of the audio path.** MI allocates
   statically. SAPF is the outlier here: it uses inheritance and virtual calls.

Several backlog items can use existing nodes or macros:

- **Triangle wave:** store the shape in `tables:` and read it with `osc`.
- **Ring modulation:** use `vca` with an **audio-rate** CV input to multiply two
  signals.
- **High-pass filtering:** use the high-pass output of `svf`.
- **Comb filtering:** use `delayN` with feedback (§4.7).
- **Pitched noise:** build a macro from `noise` and a note-tracking `svf`
  band-pass. Derive its cutoff from `note_to_inc` at block rate.
- **`apc` and `dual_apc`:** combine a square `osc` with `env` for `apc`, for
  `dual_apc`, use two square oscillators that cross-modulate each other's `inc`.
  Both are straightforward once `fm_op` exists.

---

## 7. Sub-block control rate: the CPU question

Does updating control values (envelopes, LFOs, filter coefficients) every 16–32
frames instead of once per 256-frame block cost too much CPU?

No. **Control work is small beside audio processing:**

| Work                                        | Ops per voice per block (256 frames) |
| ------------------------------------------- | ------------------------------------ |
| audio: 256 × (osc ~6 + filter ~10 + vca ~2) | ~4600                                |
| control, once per block (172 Hz)            | ~30                                  |
| control, every 32 frames (1.4 kHz)          | ~240                                 |
| control, every 16 frames (2.8 kHz)          | ~480                                 |

At 2.8 kHz control (16-frame sub-blocks), this estimate puts control at about
**10% of one voice's audio work**. Each tick takes only one or two multiply-adds.
MI runs control at 1.8 kHz on a **168 MHz single-core Cortex-M4** and has CPU to
spare, umetate's DSP runs on a **320 MHz dual-core pi32v2**. The per-sample,
per-voice, per-node audio loop dominates the 2.9 ms budget, so this estimate does
not suggest that sub-block control is a threat.

The audible trade-off runs the other way. At 172 Hz (once per 256 frames), fast
filter sweeps and LFOs can zipper. Updating every 16–32 frames removes that
stepping at an estimated cost of about 5%. The generator chooses the sub-block
size at compile time based on the patch's modulation, static patches can use a
coarser rate. MI, Pd, and SC all update controls more often than once per audio
block for this reason.

---

## 8. Granulation (phase-granular, Xenakis-inspired)

Granulation reads slices of a **phase map** (a `const` XIP table) under
stochastic control. The map can be any table, including one generated by the §5
`ifft`. Because it reads a table rather than storing a separate audio buffer, it
uses no `.pool` memory.

### 8.1 The model

- A **grain** reads the phase interval `[p0, p0 + length)` at the rate set by
  `pitch`.
- `p0` (start), `length` (slice length, in **phase**), and `pitch` (read rate) are
  **parameters**, and each can be modulated.
- The grain's duration is `length / pitch`. Reading the same phase slice faster
  raises the pitch and shortens the grain, like playing a tape faster.
- Separate stochastic nodes generate the modulation signals and feed these
  parameters.

### 8.2 The pipeline order (the crux)

Apply pitch modulation **before** reading the map and the amplitude window
**afterward**:

```c
per sample, per grain:
    inc   = base_inc + pitch_mod(n);   /* (1) pitch mod — phase-domain, BEFORE the map */
    p    += inc;                        /* advance the phase pointer */
    w     = map[p];                     /* (2) sample the phase map (a table read) */
    out  += w * window(progress);       /* (3) amplitude window — signal-domain, AFTER */
```

Modulating pitch before the map changes phase/frequency directly: one multiply-add,
with no resampling or extra aliasing. Apply the window after the map to shape each
grain's amplitude. The window must stay **aligned to the grain**, so it needs the
grain's progress value from the phase generator.

### 8.3 The shape: three nodes, not a loop

The window needs the grain's progress. Putting the phase generator and window in
one node that loops through an external oscillator would create a graph cycle, which
the DAG generator rejects. Use a linear chain instead:

```text
gran_phase.phase    ->  osc.phase             (any oscillator reads the map at the stochastic phase)
gran_phase.progress ->  gran_window.progress  (the window is aligned to the grain)
osc.audio           ->  gran_window.audio
```

- **`gran_phase` node:** generates the stochastic slice and outputs `phase` (Q32)
  and `progress` (Q16, from 0 to 1 within each grain). Its modulatable parameters
  are `p0`, `length`, `pitch`, and `density`. Calculate progress from phase as
  `(phase − p0) / length`, it remains correct under per-sample pitch modulation.
  Each grain ends at `p0 + length`, regardless of rate changes. Wrap `p0` and
  `p0 + length` modulo the map length to avoid overflow.
- **Existing `osc` node:** it already accepts a `phase` input, so it can read the
  map at the stochastic phase. Choose a saw, `fm_op`, or an IFFT-generated table to
  set the grain's timbre.
- **`gran_window` node:** multiplies `audio` by a window of `progress`. Supported
  shapes are trapezoid, Hann, and rectangular. The trapezoid is cheapest because
  its ramps are linear and need no cosine. The rectangular window has no taper, it
  matches Xenakis's abrupt grains.

### 8.4 The stochastic component (its own nodes)

The Xenakis-inspired core is GENDYN, described in _Formalized Music_. Its
waveform is a polygon: both breakpoint amplitudes and distances between
breakpoints take bounded random walks, with samples linearly interpolated between
points. At the ±32768 limits, the walk **reflects** rather than clamps. This
"elastic barrier" is part of Xenakis's method, clamping would change the sound.
The values are already integer (Q15 ±32767), so the method fits umetate's
fixed-point baseline. Implement the random process as control-rate nodes connected
to `gran_phase`'s modulation inputs:

- **`rand_walk`**, `x += step·(u − ½)`, then **reflect** off `[lo, hi]` (mirror,
  not clamp). Xenakis's barrier model.
- **`distribution`**, a random draw per control tick (uniform / Gaussian /
  Cauchy, Xenakis's ST/Free-Stochastic vocabulary. Gaussian via sum-of-uniforms
  or a Box–Muller-lite table, Cauchy via `tan(π·(u − ½))`).
- **`drift`**, a one-pole-lowpassed `rand_walk` (slow wander).

`rand_walk` and `drift` use inexpensive integer operations. Cauchy sampling needs a
`tan` table or an identity derived from `fm1_atan2`, so keep that calculation at
control rate.

### 8.5 Fixed-point and cost

Use Q32 for `p0`, `length`, and `pitch`, store the map as a Q15 `const` XIP table,
`progress` as Q16, and the window as Q15. Per sample, each active grain needs one
addition, one map lookup, one window multiply, and one saturating accumulate. The
stochastic nodes run at block rate. In total, a grain costs about four integer
operations and two table reads. The map lives in XIP and the window is either a
table or a simple ramp, so neither uses the `.pool` budget.
