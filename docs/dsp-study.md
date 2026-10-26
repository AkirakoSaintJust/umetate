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

### 2.2 PolyBLEP (band-limited saw/square, cheap anti-aliasing)

MI's `PolyblepOscillator` and every modern synth use the **polyBLEP** correction —
a 4th-order polynomial patched around the discontinuity, ~4 extra ops/sample, no
oversampling:

```c
float poly_blep(float t, float dt) {          /* t = phase in [0,1), dt = inc */
    if (t < dt)      { t /= dt;       return t + t - t * t - 1.0f; }
    if (t > 1 - dt)  { t = (t - 1)/dt; return t * t + t + t + 1.0f; }
    return 0.0f;
}
/* saw:    out = 2*t - 1 - poly_blep(t, dt);
   square: out = (t < 0.5f ? 1 : -1) + poly_blep(t, dt) - poly_blep(fract(t+0.5f), dt); */
```

The fixed-point equivalent keeps the same polynomial in Q15/Q16. This is the
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

VPS (Lazzarini & Timoney, DAFx-11 — the technique behind FAW's Circle²) extends
classic PD by making **both** the distortion depth `d` and the bending point `v`
modulatable. Classic PD only bends the transfer along the x-axis; VPS opens the
y-axis too. Concretely, the transfer function is **two sine segments "glued"
together at the bending point `v`**, with `d` controlling how far the segments
differ — so the waveform morphs in a 2D `(d, v)` space, both ordinary (modulatable)
params:

```c
/* phase 0..1 → a "bent" sine: segments glued at v, depth d */
uint32_t ph = phase >> (32 - LOG2_TF);        /* 0..1 index */
uint32_t bend = glue(ph, v);                   /* the bend point, shaped by v */
out = sin_table[(ph + d * shape(bend)) & MASK];/* d = distortion depth */
```

The essential point for umetate: VPS turns the *static* `phase_map` table into a
**parameterized phase shaper** — the transfer depends on `d` and `v`, which are
ordinary params (modulatable through a `<param>_mod` input). This is the one place
the "shape = data" rule needs a nuance: a *static* shape is a table, a *dynamic*
shape is a parameterized transfer (a node with `d`/`v` params, not a fixed table).
The exact equations are in the paper (Lazzarini & Timoney, DAFx-11); the FAW
write-up also stresses that dynamic phase shaping needs band-limiting (the §2.2
polyBLEP care), which is why the VPS oscillators are built on §2.1/§2.2.

### 2.6 The FM operator's sine (ymfm / Dexed)

The operator is: `inc = f·2^32/FS`, `phase += inc`, `out = sin_table[phase] *
level`, where `level` is the *amplitude envelope* (rate/level). ymfm computes the
sine and the attenuation in the **log domain** (a phase→sine table and a
level→gain table), so the whole operator is integer table lookups. This is exactly
umetate's `phasor` + `osc` + `env` + `vca` decomposition, and it is why the FM-chip
authors and umetate independently chose the same primitives.

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

### 4.1 SVF (Chamberlin / MI `Svf`)

```c
f = 2 * sinf(pi * cutoff / FS);          /* or tan approx; recompute at control rate */
q = 1.0f / resonance;
low  += f * band;
high  = in - low - q * band;
band += f * high;
/* low / band / high are the LP/BP/HP outputs; notch = low + high */
```

Two state variables (`band`, `low`), one coefficient recompute per control tick.
MI's `Svf` is exactly this. It is the best "one filter for all modes" primitive,
and matches umetate's `svf` node (`z1`/`z2` state).

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

---

## 5. Spectral oscillators (IFFT additive)

Additive synthesis via IFFT: the spectrum (magnitude+phase per bin) is the *data*;
an inverse FFT turns it into a single-cycle wavetable at build time, which is then
read like any other table oscillator (§2.1). The IFFT is **offline/precomputed**,
never per-block in the hot loop. So a "spectral oscillator" is just a wavetable
whose source was an IFFT — **data, not a distinct algorithm** (though umetate keeps
an `ifft` node for live spectral work). This is how SC's `IFFT` and Csound's
`adsyn` conceptually collapse to table reads for a fixed spectrum.

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
