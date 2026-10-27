# DSP algorithm spec — fourop-fm

> One section per DSP component (oscillator, filter, envelope, …). This is the
> *math* the `patch.json`/`node.c` translation follows: when it is complete, a fresh
> agent can write the code without re-deriving anything.

> **Research first.** Record what was consulted and **give credit**: distinguish
> *consulting* (learn the technique) from *copying/deriving* (preserve the source's
> notice and record it in `LICENSING.md`). Check each source's licence before
> copying; incompatible licences are consulted, never copied.

> **Performance + memory safety are standing constraints:** bounded loops, no
> allocation, no 64-bit division, no `double`, no per-sample dispatch in the hot
> loop; one writer per shared value or a snapshot protocol.

## Default reference points

| Source | URL | Licence (verify at use) |
| --- | --- | --- |
| ymfm (MAME 3rdparty) | https://github.com/mamedev/mame/tree/master/3rdparty/ymfm | BSD-3-Clause |
| SuperCollider DSP (UGens) | https://github.com/supercollider/supercollider | GPL-3.0-or-later |
| Mutable Instruments (eurorack) | https://github.com/pichenettes/eurorack | MIT |
| Synthesis Toolkit (STK) | https://github.com/thestk/stk | permissive (see LICENSE) |
| maximilian | https://github.com/micknoise/Maximilian | see LICENSE |
| music dsp archives | https://www.musicdsp.org/en/latest/ | per-snippet (see each) |

In-repo study: [`docs/dsp-study.md`](../docs/dsp-study.md).

---

## Component: `dx_env` (rate/level envelope)

- **Purpose:** the FM operator envelope — the DX/TX rate/level shape that gives
  4-op FM its attack/decay/sustain/release character. Replaces the shipped `env`
  node's linear attack/release.

- **Algorithm** (fixed-point, exactly):
  `level` is a Q15 gain (0…32767). Four stages, each an exponential one-pole toward
  a target (`level += (target − level)·rate / 2¹⁶`, via `fm1_madd_sat`):

  | stage | target | advance when | on advance |
  | --- | --- | --- | --- |
  | 0 attack | `l1` (peak) | `level ≥ l1−8` | level := l1; stage := 1 |
  | 1 decay1 | `l2` | `level ≤ l2+8` | level := l2; stage := 2 |
  | 2 decay2 | `l3` (sustain) | `level ≤ l3+8` | level := l3; stage := 3 |
  | 3 sustain | — | hold | level := l3 |
  | 4 release | `0` | `level < 8` | level := 0 |

  Gate edges drive the stage: gate↑ from release → stage 0 (level := 0); gate↓ from
  any non-release stage → stage 4.

- **Inputs / outputs:** `gate` (event, default `voice_gate[v]`), `cv` (control, Q15).

- **Parameters** (Q-format, range, default, rate, modulatable):

  | param | Q | range | meaning |
  | --- | --- | --- | --- |
  | `r1 r2 r3 r4` | q16 | 0…65535 | one-pole coefficient (0 = ∞, 65536 = instant) |
  | `l1` | q15 | 0…32767 | attack peak |
  | `l2` | q15 | 0…32767 | decay1 target |
  | `l3` | q15 | 0…32767 | sustain level |

  All block rate, modulatable. The rate→time relationship is `t ≈ 1/rate` (one-pole),
  so a UI "rate" knob should use a log curve.

- **Coefficients / precompute:** none — the rates are used directly as one-pole
  coefficients; the per-tick work is one `fm1_madd_sat` (a Q15×Q16 multiply-add).

- **State:** `stage` (uint32, 0…4), `level` (q15).

- **Edge cases:** `level` is clamped to [0, 32767] by the stage thresholds; release
  from a held level; a gate↑ during release restarts attack from 0. The +8/−8
  hysteresis prevents asymptotic creep.

- **Reference + credit:** stage structure and rate/level semantics from **ymfm**
  (`fm_operator::clock_envelope`, BSD-3-Clause — consulted for the
  attack/decay/sustain/release decomposition and the "attack is the only stage that
  raises the level" rule). Cross-checked against **Dexed/msfa** (GPL-3.0 — consulted
  only). **Deviation:** ymfm/Dexed advance a log-domain *attenuation* by a table
  increment and convert via a power table; here the rate is a Q16 one-pole
  coefficient (the §3.3 exponential form) — the same exponential character, one
  multiply-add, no log/power tables. Recorded as *learned, re-implemented*.

- **Performance note:** control rate (no audio ports), one `fm1_madd_sat` + one
  compare per tick; runs in the control prologue, not the sample loop.
