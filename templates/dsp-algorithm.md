# DSP algorithm spec

> One section per DSP component (oscillator, filter, envelope, LFO, mixer,
> delay, …). This is the *math* the `patch.json`/`node.c` translation follows:
> when it is complete, a fresh agent can write the code without re-deriving
> anything. Link this from `project-plan.md`; do not duplicate it there.

> **Research first.** When specifying or implementing an algorithm, research how
> it is best done — start from the default reference points below, honor any the
> user supplies, and let online search surface more. Record what you consulted and
> **give credit**: distinguish *consulting* (learn the technique) from
> *copying/deriving* (preserve the source's notice and record it in
> `LICENSING.md`). Check each source's licence before copying; incompatible
> licences are consulted, never copied.

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

In-repo study: [`docs/dsp-study.md`](../docs/dsp-study.md) (MI, SuperCollider,
Pure Data, Dexed/msfa, Nuked, ymfm, SAPF).

## Component: `___`

> Copy this block per component. Delete unused fields.

- **Purpose:**
- **Algorithm** (the fixed-point formula, exactly):
- **Inputs / outputs** (port, rate `event|control|audio`, format `q15|q16|q32|phase`):
- **Parameters** (name, Q-format, range, default, `sample`/`block` rate, modulatable):
- **Coefficients / precompute** (recomputed at block rate, not per sample — the formula):
- **State** (SoA fields, Q-format):
- **Edge cases** (div-by-zero guard, clamp/saturate, phase wrap, denormal):
- **Reference + credit** (source consulted, URL, licence, what was derived vs. merely learned):
- **Performance note** (per-sample vs per-block work; any cycle-breaker `delay1`/`delayN`):

## Component: `___`
