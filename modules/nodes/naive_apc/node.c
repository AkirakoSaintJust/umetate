/* Atari Punk Console, naive (aliasing) variant. A 555 astable (the Q32 phase
   accumulator) triggers a 555 monostable whose pulse width is an absolute time
   (`width`, Q16 samples), so the duty is width/period and changes with pitch (the
   authentic cross-coupling). `fm` (audio) scales the frequency by 1 + fm/32768;
   `width_mod` (control) scales the width by 1 + width_mod/32768 (the cross-mod
   inputs). The duty is clamped to [inc, 2^32-inc] so the two edges never collide;
   a width past the period clamps to a near-full pulse. Raw edges: this is the
   aggressive, aliased APC. Locals are scoped so two instances can coexist. */
int32_t ${out.audio} = 0;
{
    uint32_t inc_eff = (uint32_t)(((int64_t)${state.inc} * (32768 + ${in.fm})) >> 15);
    int64_t w = ((int64_t)${param.width} * (32768 + ${in.width_mod})) >> 15;
    uint64_t raw = (uint64_t)(w < 0 ? 0 : w) * (uint64_t)inc_eff;
    uint32_t pw = 0;
    if (inc_eff) {
        uint64_t p = raw >> 16;                 /* width_samples * inc / 2^16 (Q32) */
        uint32_t hi = 0u - inc_eff;             /* 2^32 - inc: one low sample left */
        pw = (uint32_t)(p < inc_eff ? inc_eff : (p > hi ? hi : p));
    }
    uint32_t ph = ${state.phase} + inc_eff;
    ${state.phase} = ph;
    if (inc_eff)
        ${out.audio} = (ph < pw) ? 32767 : -32767;
}
