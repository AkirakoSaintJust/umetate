# CPU optimisation loop (safe)

How to reduce the audio ISR cost without changing the sound, and without guessing.
Every rule below is a lesson from the type-p-fm1 render optimisation, where the ISR
dropped from 60% to 45% at 320 MHz with the output provably byte-identical.

## The metric

The target number is the ISR instruction share, printed by

```sh
umetate emu --check --mhz 320
# last 40 ms: NN% of instructions in ISRs = M.M M ISR instructions per second
```

ISR% is the metric. A full-scale audio peak plus "no halt" tells you the render
still works, not that it got cheaper. Watch the number.

The provisional device budget, until a hardware unit is available, is 45% ISR at
320 MHz, dual-core. The emulator is a model, about 1.92x optimistic, so 45 x 1.92
is roughly 86% of the real headroom. Do not claim a real-device fit from the
emulator number alone.

## The gate: bit-exactness

An optimisation that changes the audio is a bug, not an optimisation. Every change
must leave the output byte-identical. The tooling for that gate is already in the
framework.

- `umetate build --synth <project> --test-dump N` compiles with `-DUMETATE_TEST_DUMP=N`,
  which records the raw pre-master output of audio block N into a `volatile` array.
- `umetate emu --dump 0x1c19400 512 --keys '800:k21,...'` reads that array back.
- `umetate build --no-asm` forces the C fallback for any hand-asm, so you can diff
  asm against C.
- The host build writes `firmware/build/host/<project>.wav`. Build the before and
  the after, compare their SHA-256.

The cleanest gate is a before and after diff of the same firmware, same timing,
only your optimisation toggled. If the hashes differ, revert. There is no
"close enough".

## The loop

Run this for every optimisation increment. One change per pass.

1. **Baseline.** Record the ISR% and save a reference output hash (WAV SHA-256 or
   the test-dump block).
2. **Profile before you touch anything.** Disassemble the hot loop and classify the
   instruction mix: how many MACs, how many register moves, how many address
   computations, how many loads. The biggest category is the lever. In the type-p-fm1
   render the hot loop was 52% register-move and address arithmetic against roughly
   90 MACs, which told us the multiply was not the problem, the loop structure was.
3. **Check the compiler first.** Before writing hand-asm, confirm the compiler is
   not already emitting the optimal instruction. `fm1_q15_mul` already compiles to
   the native 64-bit MAC plus a shift. A manual MAC was a no-op for exactly this
   reason. Never hand-roll what the compiler already does well.
4. **Pick one lever and name the expected win.** Fewer multiplies, cheaper constant
   ops, or a loop reorder. State the hypothesis before the change so you can judge it.
5. **Implement, gated.** Smallest coherent change, `#ifdef UMETATE_TARGET` with a
   bit-identical C fallback and a `--no-asm` toggle. No change is so clever it may
   skip the gate.
6. **Measure and verify.** ISR% delta plus the byte-identical hash. Both, never one.
7. **Accept or revert.** No measured win, or a hash mismatch, means revert and move
   on. A rejected idea is a finding, not a failure.
8. **Record.** Write both the wins and the rejections into the roadmap so the next
   pass does not re-attempt a dead end.

## pi32v2 facts that shaped the findings

Do not re-learn these.

- The core has 16 general-purpose registers. The type-p-fm1 render loop touches roughly
  40 structure-of-arrays regions (voice state, block constants, delay and phase).
  They cannot all be live at once. Hand-asm hits this 16-register wall immediately,
  so the compiler is often the better register allocator here.
- The 64-bit MAC exists and the compiler uses it. `fm1_q15_mul` is four
  instructions: load the rounding constant, zero the high word, MAC, shift right 15.
  There is no 32-bit multiply-with-round-shift. The `*|* -#i (ssat)` family is
  16x16.
- `r1_r0 = #i` is a 7-bit immediate, so the rounding preload cannot fold into one
  64-bit load.
- clang 4.0.1 does not emit `rep` zero-overhead loops, VLIW `#` dual-issue, or
  `[rN++=4]` auto-increment. The stock firmware's compiler does. That is a real
  gap, but the register file is the hard ceiling above it.

## Effective changes, most useful first

1. **Loop structure.** The voice-outer swap: hoist `bus[]=0` out of the sample loop,
   put the voice loop outside the sample loop, so the per-voice block constants and
   the delay and phase state become loop-invariant over the samples and live in
   registers. This one C-only change took 51% to 45%.
2. **Fewer multiplies.** The route 0/1 specialisation folds constant 32767 and 0
   weights at compile time. The vca and tl nodes skip their two multiplies when the
   block-derived effective level is zero (the operator self-feedback with feedback 0).
3. **Cheaper constant ops.** The phasor `(int64_t)fm * 65536` became
   `(uint32_t)fm << 16`, a plain shift.

## Rejected changes (do not re-attempt)

- **Async ping-pong.** Measured, no ISR benefit. The split already runs both voice
  halves in parallel, so there was no wait to remove.
- **Manual MAC.** The compiler already emits the native MAC, so a hand MAC is a no-op.
- **Log-space math.** Only gains are exact in log space. Addition needs linear, and
  the carriers are summed linearly, so it cannot reach the final render.
- **Bit-shift for runtime values.** Only constant factors qualify, and those are done.
- **Hardware SIMD for the scalar FM.** The per-sample phase-indexed wavetable is
  scalar and data-dependent. SIMD fits the block work (bus sums, delay, post), which
  is about 2% of the cost.
- **Fused multiply-add.** The MAC accumulates then truncates. `fm1_q15_mul` plus
  `fm1_sat_add32` rounds then saturates. A raw MAC changes the result.
- **Hand-asm sample-outer rewrite.** Halted at the 16-register wall. The block
  constants re-load per sample exactly as the compiler already does.

## Safety rules

- Never weaken a test to make a build pass. The gate is the gate.
- Never accept a change that is not byte-identical, however small the difference.
- One decision-set per increment. Commit with the roadmap and the evidence in the
  same commit.
