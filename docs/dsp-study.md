# DSP implementation study

Reference material: how Mutable Instruments, SuperCollider, Pure Data, Dexed
(msfa), Nuked, ymfm, and SAPF implement their DSP — to learn efficient
synthesis-algorithm implementation and the shape of synthesis components. This is
a **reference**, not a governance/status doc (`docs/roadmap.md` is the status
authority). It backs `docs/roadmap.md` §12.5 (the node library).

---

## 1. The component interface (three shapes)

Every project converges on the same *unit* — a stateful DSP object with a process
function — but with three interface shapes:

| Project | Unit | Interface | Rate | Notes |
| --- | --- | --- | --- | --- |
| Mutable Instruments | `Engine` / `Voice` subclass | `Process(const Block& in, const Block& out, size_t size)` | block | `Parameter` knobs (curve lookup); fixed-point `stmlib::`; per-voice classes; no heap in audio |
| SAPF | `Sapf` subclass | `virtual process(...)` | block | inheritance — the only polymorphic-per-call one |
| SuperCollider | `UGen` | `next_a(n)` / `next_k(n)` / `next_i()` | per-sample (a) / per-block (k) | `.ar`/`.kr` rate polymorphism; graph + topological sort; `LocalIn`/`Out` feedback |
| Pure Data | tilde object | `t_int *perform(t_int *w)` | block (64) | buffers in `w[2..]`, `dsp_add` registers the routine; message↔signal split |
| Dexed (msfa) | `Dx7Note` + 6 operators | `compute(int32_t *buf, …)` | per-sample → block | 32 algorithms; rate/level envelopes; 1-sample operator feedback |
| Nuked | `OPN2` core | `OPN2_Generate(OPN2*, int16_t *l, int16_t *r)` | per-sample | bit-accurate integer; log/exp/sin tables; register writes |
| ymfm | `fm_operator` / `engine` | `generate(int32_t *out, uint32_t n)` | per-sample → block | templated operator/engine; shared core + per-chip tables |

**The three shapes, and the lesson:** block-process (`process(in, out, size)`) is
good for testability and vectorization; per-sample generate (`next`/`generate`)
is good for feedback (1-sample) and cache; inheritance (SAPF) puts a virtual
dispatch in the hot loop. umetate's node contract is the synthesis: a block
`process(ctx, n)` for standalone testing **plus** per-sample inlining in the fused
render for 1-sample FM feedback (`docs/roadmap.md` §12.5).

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

The one rule that makes it cheap and glitch-free: **`inc` is computed once per
note (or per control tick for pitch mod), never per sample.** Table size 512–2048
(linear interpolation ≈ 0.1% THD at 512 — inaudible). This is the *only* oscillator
form that needs no anti-aliasing (a sine table has no harmonics to fold).

### 2.2 PolyBLEP (band-limited saw/square/pulse, cheap anti-aliasing)

MI's `PolyblepOscillator` and every modern synth use the **polyBLEP** correction —
a 2nd-order polynomial patched around each discontinuity, ~4 extra ops/sample, no
oversampling:

```c
float poly_blep(float t, float dt) {          /* t = phase in [0,1), dt = inc */
    if (t < dt)      { t /= dt;       return t + t - t * t - 1.0f; }   /* = 2t - t² - 1 */
    if (t > 1 - dt)  { t = (t - 1)/dt; return t * t + t + t + 1.0f; } /* = t² + 2t + 1 */
    return 0.0f;
}
/* saw:    out = 2*t - 1 - poly_blep(t, dt);
   square: out = (t < 0.5f ? 1 : -1) + poly_blep(t, dt) - poly_blep(fract(t+0.5f), dt);
   triangle: a polyBLEP'd square through a leaky integrator (y += k·(x−y)), one extra state. */
```

The residual is the **same function regardless of where the discontinuity sits**;
only its position moves. So a **pulse (PWM)** is the square with the second
correction moved to the width `pw`:

```c
/* pulse: v = (ph < pw ? 1 : -1); p2 = (ph + 1 - pw) mod 1;
   out = v + poly_blep(ph, dt) - poly_blep(p2, dt); */
```

Clamp `pw` away from 0/1 so the two BLEPs don't overlap (the narrow-pulse
artifact). **Order matters:** the 2nd-order form above is aliasing-free only up to
~2 kHz fundamental (it covers the musical range); 3rd/4th-order (Lagrange /
B-spline) extend that, with a 2-tap EQ FIR `b0 + b1·z⁻¹ + b0·z⁻²` to flatten the
passband (Välimäki et al.). So "band-limited" is a 2nd-order default plus an
optional higher-order tier, not one fixed thing.

The fixed-point equivalent keeps the same polynomial in Q15/Q16. One subtlety for
fixed point: `poly_blep` divides by `dt` (`t /= dt`), which is a 32/32 divide —
hoist `1/dt` to **note-on** (it's constant per note), so the per-sample cost is a
multiply, not a divide. This is the
default "analog-ish" oscillator; the polynomial is the only magic.

### 2.3 Wavetable morphing (MI `VariableSawOscillator`)

A single cycle stored as a wavetable, phase-scanned; the *shape* is one or more
tables cross-faded. MI's variable saw morphs between a few precomputed saw shapes.
Lesson: **morphing = cross-fade between tables, not recomputing the waveform.**

### 2.4 Phase distortion (Casio CZ)

PD is **static** phase warping: the phase ramp goes through a monotonic *transfer
function* before the sine lookup (confirmed: the CZ used a per-cycle-synced
modulator/carrier pair). No delay — unlike FM, which is *dynamic* phase
modulation and needs a 1-sample delay for feedback:

```c
uint32_t pd = transfer[phase >> (32 - LOG2_TF)];   /* warp the phase */
out = sin_table[pd >> (32 - LOG2_SIN)];
```

The CZ "resonance" waveforms are specific transfer functions (a cosine-shaped
bend). In umetate this is `osc` + a `phase_map` table — **data, not a new node**.

### 2.5 Vector Phaseshaping (dynamic phase distortion)

VPS (Kleimola, Lazzarini, Timoney & Välimäki, DAFx-11 — the technique behind FAW's
Circle²) extends classic PD with three changes: (1) the inflection point is a
**2-D vector `p = (d, v)`** — `d` is the x-position of the bend and `v` its
y-position, where classic PD *fixes* `v = 0.5`; (2) the transfer has **multiple
inflection points** (piecewise); (3) the inflection points can be **modulated at
audio rate**. So VPS turns the *static* phase-distortion curve into a *dynamic,
multi-breakpoint* phase shaper:

```c
/* phase p in [0,1) -> a "bent" phase, then the sine. One inflection point (d,v):
   classic PD is the v = 0.5 fixed case; VPS frees both and adds breakpoints. */
/* control rate: s0 = v/d, s1 = (1-v)/(1-d)  — the two segment slopes, Q16 */
uint32_t p = phase >> 16;                                   /* Q16, 0..1 */
uint32_t q = p < d ? (p * s0) >> 16 : v + (((p - d) * s1) >> 16);
out = fm1_sin(q << 16);                                     /* shaped phase -> sine */
```

The essential point for umetate: VPS turns the *static* `phase_map` table into a
**parameterized phase shaper** — the transfer depends on `(d, v)`, which are
ordinary params (modulatable through a `<param>_mod` input). This is the one place
the "shape = data" rule needs a nuance: a *static* shape is a table, a *dynamic*
shape is a parameterized transfer (a macro/`osc` with `d`/`v` params, not a fixed
table). The exact equations are in the paper (Kleimola, Lazzarini, Timoney &
Välimäki, DAFx-11); the FAW
write-up also stresses that dynamic phase shaping needs band-limiting (the §2.2
polyBLEP care), which is why the VPS oscillators are built on §2.1/§2.2.

### 2.6 The FM operator's sine (ymfm / Dexed)

The operator is: `inc = f·2^32/FS`, `phase += inc`, `out = sin_table[phase] *
level`, where `level` is the *amplitude envelope* (rate/level). ymfm computes the
sine and the attenuation in the **log domain** (a phase→sine table and a
level→gain table), so the whole operator is integer table lookups. This is exactly
umetate's `phasor` + `osc` + `env` + `vca` decomposition, and it is why the FM-chip
authors and umetate independently chose the same primitives.

umetate's `fm_op` macro is that decomposition plus the two FM-specific knobs: a
**`ratio`** param that is `note_derived` (`inc = note_to_inc(note)·ratio`, so
non-integer ratios like 2.5 stay in tune), and optional **1-sample feedback** via
`delay1` (operator self-modulation — the DX/TX "feedback" knob). `detune` is a
small fixed offset added to `inc`. So an N-operator FM voice is N `fm_op` macros
wired by the algorithm, not new C.

### 2.7 The 8-waveform bit trick (OPZ / OPL)

The TX81Z/DX11 (YM2414 "OPZ") and the OPL2/OPL3 get their 8 selectable waveforms
from **one quarter-sine table + a 3-bit "waveform select" that bitwise-manipulates
the phase index** before the lookup — no extra tables, a few bit ops per sample:

```c
uint32_t idx = phase >> (32 - LOG2_QUARTER);   /* quarter-sine index */
if (ws & 1) idx ^= SIGN;                        /* absolute (rectified) */
if (ws & 2) idx &= HALF;                        /* half (mute the negative half) */
if (ws & 4) idx ^= PERIOD;                      /* alternate periods */
out = quarter_sine[idx];
```

So 8 waveforms = all combinations of {sign-invert, half-mute, period-mute}. The
"waveform" is a 3-bit value, and the mechanism is **phase distortion in disguise**
(a stepwise transfer function). (The OPZ's 8 differ from the OPL's 8, but both are
the same bitwise scheme.) In umetate this is `osc` with a `phase_map` that is a tiny
bitwise function (or an 8-entry table of mask/XOR patterns) — the same
`osc` + `phase_map` concept, with the map being bits rather than a full table.

### 2.8 Wavetables and cache

The cache-thrashing worry is real but has a simple fix. A single-cycle wavetable
(512–2048 samples = 1–4 KB) fits comfortably in an L1/D-cache and is read
**sequentially** (the phase advances), so it's inherently cache-friendly. Thrashing
happens only when (1) you keep *many* large tables whose total exceeds the cache,
and (2) reads scatter across them — voice 0 reads table 0, voice 1 reads table 1,
so each table's lines evict the others.

The fixes, in order:

1. **Share one table across all voices** (the common sine-based case): every voice
   reads the *same* table, so its lines stay hot and access is sequential. Free.
2. **Keep tables one cycle and small** (512–2048): linear interpolation is ~0.1%
   THD at 512, so a bigger table buys nothing.
3. **SoA over per-voice tables**: with a morph set, process *all voices against one
   table* before switching (structure-of-arrays), not interleaved per-voice reads.
4. **On the pi32v2**: hot per-sample tables belong in **SRAM (`.cpu1_rodata`)**, not
   XIP — the flash SFC runs ~80 MHz against a 320 MHz CPU, so an uncached XIP read
   is ~4× a cache hit, and the D-cache is small. This is `docs/roadmap.md`
   §12.2.3's `.cpu1_rodata` note, now with the reason.

The one case where cache genuinely matters is a *morphing wavetable* (two tables
cross-faded per sample): keep both tables small and in `.cpu1_rodata` and they both
fit.

### 2.9 Wavefolding (nonlinear waveshaping)

A wavefolder is a **memoryless** non-linear transfer function — the input
amplitude drives the fold, adding harmonics. Unlike a filter (stateful) or an
oscillator (self-contained), it is a per-sample function of the input. Transfer
functions (all fixed-point, no state):

- **Sine fold** — `out = sin(π·gain·x)`: for Q15 `x`, scale `gain·x` to a Q32
  phase and use `fm1_sin` (one LUT read + one multiply). The cheapest fold.
- **Triangle fold** — fold `x` back into [−1,1] past the rails
  (`out = 2·|2·(x·f + 0.25) − 1| − 1`-style); linear, no trig.
- **Polynomial / Chebyshev** — `T_n(cos θ) = cos(nθ)`, so a weighted sum
  `Σ c_n·T_n(x)` adds exact harmonics (T₃ = 4x³−3x, T₅ = 16x⁵−20x³+5x); a few
  multiplies via Horner.
- **Buchla 259** — five parallel op-amp folding stages + a dry path, summed; the
  "timbre" knob controls the fold amount. Parallel stages = a weighted sum of
  progressively-folded copies.

The lesson: a wavefolder is **one node = one algorithm; the transfer function =
data** (a shape enum or a Chebyshev-coefficient set). The node is the "apply the
transfer" reader; the shape is a param.

In umetate: a `wavefolder` node — `ins {audio}`, `params {amount (modulatable),
shape (sine | triangle | cheby)}`, `outs {audio}`, no state. Sine-fold uses
`fm1_sin`; polynomial folds use `fm1_madd_sat`/`fm1_sat_add32` (a fold can
overrange).

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

At each control tick: `value += increment` (linear) or `value = start + (end-start)
* exp_curve[tick]` (exponential); advance to the next segment at `tick == duration`.
The increment is precomputed at segment start — no division in the hot path. This
is the most flexible form (arbitrary breakpoints + curves) and maps to umetate's
`env` node reading a `segments` table (data).

### 3.2 Rate / level (DX7 / ymfm / Dexed)

Each stage has a **rate** (an increment, looked up from an exponential table) and a
**level** (the target): `env += rate_table[rate]; if (env >= level) next_stage;`.
The rate is exponential, the level linear-in-log-domain — so the amplitude is
`10^(-env/…)` via a table. Fewer knobs than segment envelopes, but exactly what the
FM chips do and cheap (two table lookups per tick).

### 3.3 Exponential one-pole

`env += (target - env) * coeff` — a one-pole lowpass toward a target, giving a true
exponential curve with one multiply-add. Good for simple ADSR decay/release; the
segment form generalizes it.

### 3.4 Efficiency lesson

Envelopes run at **control rate** (block or sub-block), never per sample. The
increment (or rate) is precomputed; the per-tick work is one or two ops.

---

## 4. Filters

### 4.1 SVF (Chamberlin / MI `Svf`, and Simper's TDF2)

The **Chamberlin** form (MI's `Svf`) is the classic two-integrator topology:

```c
f = 2 * sinf(pi * cutoff / FS);          /* recompute at control rate */
q = 1.0f / resonance;
low  += f * band;
high  = in - low - q * band;
band += f * high;
/* low / band / high are the LP/BP/HP outputs; notch = low + high */
```

It is simple but loses stability at high resonance. **Simper's TDF2 form** is the
production one — stable under modulation and at high resonance, same LP/BP/HP via
mix coefficients (`m0,m1,m2`):

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

For fixed point, use `g = 2·sin(π·fc/fs)` instead of `tan`: **sin is more accurate
at low bit depth** (Simper's own note), and we already have `fm1_sin` — `tan` is
*not* free on the pi32v2. So the TDF2 topology with a `fm1_sin`-derived `g` is the
right fixed-point choice. Both forms are two state variables + one coefficient
recompute per control tick; matches umetate's `svf` node (`z1`/`z2` state).

### 4.2 One-pole

`out += (in - out) * coeff` — one multiply-add, no resonance. The workhorse for
smoothing and cheap lowpass (umetate `one_pole`).

### 4.3 Biquad (RBJ cookbook)

The standard two-pole/two-zero with five coefficients. More shape (LP/HP/BP/notch/
peak/shelf) but more coefficient recomputation per control tick (sin/cos). Use when
the SVF's fixed topologies are insufficient.

### 4.4 Ladder (Moog / MI `LadderFilter`)

Four one-pole stages in series + negative feedback from the last stage to the first
(the "ladder"): `stage1 += (in - stage4 * res) * g; stage2 += (stage1 - stage2) * g; …`.
The classic character filter; `res` is the feedback, `g` the tan-based cutoff.

### 4.5 Low-pass gate (vactrol)

The Buchla 292 LPG couples a one-pole low-pass and a VCA, both driven by the
**same** control — a vactrol (LED + LDR), whose non-linear decay is the character:

- fast attack (~instant–3 ms);
- a slow decay: ~**1–1.5 s** from fully open to semi-closed (VTL5C4), then *slower
  still* to fully closed — and the LDR responds **faster at high light, slower at
  low light**, which is precisely what makes the decay non-exponential (the "ring"/
  "pluck" tail);
- a **memory effect**: the response depends on recent history (the slowest
  vactrols "remember" being lit), so repeated hits land differently;
- because cutoff and gain are coupled, the sound gets *quieter and darker
  together* — the "woody" pluck.

The vactrol response is modeled as a **sum of two exponentials** (fast LED + slow
LDR) or a one-pole with a power-law tail; MI *Streams* models it digitally (SHAPE =
the vactrol on/off response times, MOD = damping — study its source for the exact
curve, MIT-licensed; credit, don't copy).

In umetate: an `lpg` **node** — `ins {audio, gate}`, `params {response (on/off
time), damping}`, `outs {audio}`; state = one-pole + the vactrol envelope. It is
*not* just `one_pole` + `env` as a macro: the vactrol envelope's non-linear decay
plus the cutoff/gain coupling are the algorithm.

### 4.6 Formant filter (vowel formants)

A bank of band-pass filters at the vowel formant frequencies shapes a
harmonically-rich source (saw/pulse) into a vowel. F1/F2 (and F3 for naturalness)
are **data**:

| Vowel | F1 | F2 | F3 |
| --- | --- | --- | --- |
| a (father) | 660–850 | 1610–1700 | 2400 |
| i (heed) | 240–270 | 2300–2400 | 3000 |
| u (boot) | 250–300 | 595–870 | 2250 |
| e (bet) | 390–400 | 2000–2300 | 2550 |

In umetate: a `formant` **macro** — 3–4 `svf` band-passes in parallel, a `vowel`
param indexing an F1/F2/F3 `tables:` table. All fixed-point (N × `svf`). The Kawai
K5000's "formant filter" is this idea.

### 4.7 Comb filter

A delay line with feedback (`out = in + fb·delay`) gives the comb response
(peaks/notches at multiples of 1/delay). umetate's `delayN` node *is* the comb —
it already has `time` and `fb` params (§6.9) and is the DAG cycle-breaker — so no
new node: a "comb" is a short `delayN` with feedback, and flanger / chorus /
resonator / Karplus–Strong are all `delayN` uses.

---

## 5. Spectral oscillators (IFFT additive)

Additive synthesis via IFFT: the spectrum (magnitude+phase per bin) is the *data*;
an inverse FFT turns it into a single-cycle wavetable at build time, which is then
read like any other table oscillator (§2.1). The IFFT is **offline/precomputed**,
never per-block in the hot loop. So a "spectral oscillator" is just a wavetable
whose source was an IFFT — **data, not a distinct algorithm** (though umetate keeps
an `ifft` node for live spectral work). This is how SC's `IFFT` and Csound's
`adsyn` conceptually collapse to table reads for a fixed spectrum.

Fixed-point caution: kiss_fft's **fixed-point** build scales by `1/N` in *both*
directions (overflow prevention), so a forward+inverse round-trip is `1/N²` — you
must multiply back to reconstruct a Q15 table. The pi32v2 **hardware FFT is
float** (`libFFT_pi32v2_OnChip.a`, `flfft_core_pi32v2.c`), so the `ifft` node's
"wavetable-from-64-harmonics" is either float (hw, at control rate — the honest
float isolation) or fixed-point (kiss_fft) with the scaling handled.

---

## 6. Cross-cutting efficiency lessons

1. **One node = one algorithm; shape/spectrum/envelope/transfer-function = data.**
   Every project keeps the *reader* (oscillator, envelope, filter) separate from
   the *shape* (table, segments, spectrum) — the shape is data, precomputed.
2. **Precompute everything at note-on / control rate** — `inc`, envelope
   increments, filter coefficients. Never divide in the per-sample loop.
3. **Tables over transcendentals** — sin/exp/log are tables (ymfm/Dexed/Nuked do
   the whole operator in integer table lookups). Maps to umetate's `hal/fm1_math.h`
   and the JieLi hardware math.
4. **Integer fixed-point, Q in the name** — MI (`int16`/`int32`), ymfm/Nuked/Dexed
   (integer + tables). Confirms umetate's integer-first + Q-notation.
5. **1-sample feedback for FM, block-delay for echo** — ymfm/Dexed (operator
   feedback is 1-sample), SC/Pd (`LocalIn`/`send~` are block-delayed). Confirms
   umetate's `delay1` vs `delayN`.
6. **Control at sub-block rate, audio at sample rate** — MI (24-sample blocks,
   ~1.8 kHz control), Pd (64). The per-sample loop is the cost; control is ~1–8%.
7. **No heap, no virtual dispatch in the audio path** — MI allocates statically;
   only SAPF uses inheritance, and it's the educational outlier.

**The backlog items that are already covered** (pinned so nothing is hand-wavy):

- `triangle` — a `tables:` shape, read by `osc`. Data, no node.
- `ring mod` — `vca` with an **audio-rate** CV input (multiply two signals). No new
  node.
- `high-pass` — the `svf` high-pass output. No new node.
- `comb` — `delayN` with feedback (§4.7). No new node.
- `pitched_noise` — a macro: `noise` → a note-tracking `svf` band-pass (cutoff =
  `note_to_inc`-derived frequency at block rate). No new node.
- `apc` / `dual_apc` — a macro: a square `osc` + `env` (`apc`), or two squares
  cross-modulating each other's `inc` (`dual_apc`). Trivial once `fm_op` exists.

---

## 7. Sub-block control rate — the CPU question

Anxiety: does running control (envelopes, LFOs, filter coefficients) every 16–32
frames instead of once per 256-frame block cost too much CPU?

No — for a concrete reason. **Control is a rounding error next to audio:**

| Work | Ops per voice per block (256 frames) |
| --- | --- |
| audio: 256 × (osc ~6 + filter ~10 + vca ~2) | ~4600 |
| control, once per block (172 Hz) | ~30 |
| control, every 32 frames (1.4 kHz) | ~240 |
| control, every 16 frames (2.8 kHz) | ~480 |

Even at 2.8 kHz control (16-frame sub-blocks), control is **~10% of one voice's
audio**, and it's the *cheap* kind of work (one or two multiply-adds per tick).
MI runs 1.8 kHz control on a **168 MHz single-core Cortex-M4** and has CPU to
spare; umetate runs a **320 MHz dual-core pi32v2 with the DSP on a dedicated core**.
The audio loop (per-sample × per-voice × per-node) is what the 2.9 ms budget is
spent on — sub-block control does not threaten it.

The real tradeoff is the opposite direction: control at 172 Hz (once per 256
frames) causes audible **zipper/stepping** on fast filter sweeps and LFOs, while
16–32-frame sub-blocks eliminate it at ~5% cost. The sub-block size is a
**compile-time generator choice** (from the patch's modulation), and it can be
coarser for a static patch. Sub-block control is the correct, cheap default —
MI, Pd, and SC all do finer-than-audio-block control for exactly this reason.

---

## 8. Granulation (phase-granular, Xenakis-inspired)

The one genuinely novel piece of the backlog. It is a **wavetable granulator**: a
"phase map" (a `const` XIP table — any table, including one generated by the
§5 `ifft`) is read in *slices* under stochastic control. No audio buffer, no `.pool`
cost.

### 8.1 The model

- a **grain** = a phase interval `[p0, p0+length)` read at a rate (`pitch`);
- `p0` (start), `length` (slice length, in **phase**), and `pitch` (read rate) are
  all **params**, all **modulatable**;
- the grain's *time* duration = `length / pitch` — a fixed phase-slice read faster
  is higher *and* shorter (the "reading a tape faster" behavior), which is what
  makes granulation feel organic;
- the stochastic part is **separate nodes** (below), patched into those mod inputs.

### 8.2 The pipeline order (the crux)

Pitch modulation happens **before** the map; windowing **after**:

```c
per sample, per grain:
    inc   = base_inc + pitch_mod(n);   /* (1) pitch mod — phase-domain, BEFORE the map */
    p    += inc;                        /* advance the phase pointer */
    w     = map[p];                     /* (2) sample the phase map (a table read) */
    out  += w * window(progress);       /* (3) amplitude window — signal-domain, AFTER */
```

Pitch modulation *before* the map is pure phase/frequency modulation (one
multiply-add, no resampling, no extra aliasing). Windowing *after* is the grain
envelope — it must be **aligned to the grain**, so it needs the grain *progress*,
which only the phase generator owns.

### 8.3 The shape: three nodes, not a loop

The window needs the grain progress, so the phase generator and the window cannot
be one node that *loops* through an external oscillator (that would be a graph
cycle, which the DAG generator rejects). Instead it is a linear chain:

```text
gran_phase.phase    ->  osc.phase             (any oscillator reads the map at the stochastic phase)
gran_phase.progress ->  gran_window.progress  (the window is aligned to the grain)
osc.audio           ->  gran_window.audio
```

- **`gran_phase`** (node): the stochastic slicer. Outs `phase` (Q32) and `progress`
  (Q16, 0…1 within each grain). Params `p0`, `length`, `pitch`, `density`; all
  modulatable. `progress = (phase − p0) / length` is **phase-based**, so it stays
  correct even under per-sample pitch modulation (a grain ends exactly at
  `p0 + length`, however the rate jitters). `p0` and `p0+length` wrap modulo the
  map length (no overflow).
- **`osc`** (existing): already has a `phase` input — this is exactly what it's for;
  swap in `saw`, `fm_op`, or an `ifft`-generated table to change the grain timbre.
- **`gran_window`** (node): `audio × window(progress)`, `window` ∈ {trapezoid,
  Hann, rect}. A trapezoid is the cheapest (linear ramps, no `cos`); "genuinely
  Xenakis" is the degenerate `rect` case (no windowing at all — he used abrupt
  grains).

### 8.4 The stochastic component (its own nodes)

The "genuinely Xenakis" core is GENDYN (*Formalized Music*): a waveform is a
polygon whose **breakpoints** — both their **amplitudes** *and* the **distances
between them** — do bounded random walks between ±32768 barriers, with samples by
**linear interpolation** between breakpoints. The bounds are **mirrors, not
clamps**: the walk *reflects* off the barrier (an "elastic barrier"), which is the
specific Xenakis mechanism — a clamp would sound different. This is *already
integer* (Q15 ±32767), so it fits the fixed-point baseline exactly. The stochastic
engine is therefore control-rate nodes, patched into `gran_phase`'s mod inputs:

- **`rand_walk`** — `x += step·(u − ½)`, then **reflect** off `[lo, hi]` (mirror,
  not clamp); Xenakis's barrier model.
- **`distribution`** — a random draw per control tick (uniform / Gaussian /
  Cauchy — Xenakis's ST/Free-Stochastic vocabulary; Gaussian via sum-of-uniforms
  or a Box–Muller-lite table, Cauchy via `tan(π·(u − ½))`).
- **`drift`** — a one-pole-lowpassed `rand_walk` (slow wander).

(`rand_walk` and `drift` are cheap and integer; the Cauchy `tan` needs a `tan`
table or a `fm1_atan2`-derived identity, so it is the one to keep control-rate.)

### 8.5 Fixed-point and cost

`p0`/`length`/`pitch` Q32, map `const` XIP Q15, `progress` Q16, window Q15.
Per-sample cost = active grains × (one add + one table read + one window multiply
+ one saturating accumulate); everything stochastic is block-rate. So a grain is
~4 integer ops + 2 table reads, and the `.pool` budget is untouched (the map is
XIP, the window is a table or a cheap ramp).
