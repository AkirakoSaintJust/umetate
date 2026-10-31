/* Q32 phase accumulator. `inc` (note-derived) is the pitch; `pitch` (control, Q15)
   scales it — full-scale = ±1 octave, i.e. `inc * (1 + pitch/32768)` (the vibrato
   input). The pitch-scaled increment is block-constant (`inc` is note-derived,
   `pitch` is control-rate), so it is recomputed once per block into `${state.step}`
   (the node's `block_derived`) — the per-sample body is just the add.

   `fm` (audio, Q15) is a *phase offset* scaled by 2^16 (full-scale = ±π, the FM
   index) and `mod` (control) is a small additive offset — both apply to the readout
   phase only. The accumulator advances by `step` alone: accumulating `fm` would
   integrate the modulator into the frequency (FM), which detunes the carrier with
   any modulator DC and lets a feedback loop settle on a DC fixed point. This is the
   Yamaha model: `out = wave(acc + modulator)`, `acc += step`. Multiplication (not
   `<< 16`) so a negative (bipolar) modulator is well-defined. */
uint32_t ${out.phase} = (uint32_t)(
    (int64_t)${state.phase}
    + ((int64_t)${in.fm} * 65536)
    + (int64_t)${in.mod}
);
${state.phase} = (uint32_t)((int64_t)${state.phase} + (int64_t)${state.step});
