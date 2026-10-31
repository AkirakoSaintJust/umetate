/* DX-style rate/level envelope (control rate). Four rates + three levels, all
   0..99 (the Yamaha scale). Each stage advances `level` toward its target by the
   rate's one-pole coefficient (`fm1_rate_coeff[rate]`, Q16), scaled by
   `rate_scale` (velocity -> envelope rate, Q15 unity 32768, always >= 0). Levels
   are total-level 0..99 -> Q15 gain via `fm1_level_gain` (0.75 dB/step).
   `trigger` (default `voice_trig[v]`) resets to attack on a note-on edge, even
   mid-note (a voice steal). Stages: 0=attack (0->l1), 1=decay1 (l1->l2),
   2=decay2 (l2->l3), 3=sustain (hold l3), 4=release (->0). A gate edge starts
   release. No local declarations: the body is inlined once per operator, so
   every value is an inline expression. */
if (${in.trigger}) { ${state.stage} = 0u; ${state.level} = 0; }
if (${in.gate}) {
    if (${state.stage} == 4u) { ${state.stage} = 0u; ${state.level} = 0; }
} else if (${state.stage} != 4u) {
    ${state.stage} = 4u;
}

if (${state.stage} == 0u) {
    ${state.level} = fm1_madd_sat(${state.level},
        fm1_level_gain[${param.l1}] - ${state.level},
        fm1_q16_mul(fm1_rate_coeff[${param.r1}], ${in.rate_scale} << 1), 16);
    if (${state.level} >= fm1_level_gain[${param.l1}] - 8) { ${state.level} = fm1_level_gain[${param.l1}]; ${state.stage} = 1u; }
} else if (${state.stage} == 1u) {
    ${state.level} = fm1_madd_sat(${state.level},
        fm1_level_gain[${param.l2}] - ${state.level},
        fm1_q16_mul(fm1_rate_coeff[${param.r2}], ${in.rate_scale} << 1), 16);
    if (${state.level} <= fm1_level_gain[${param.l2}] + 8) { ${state.level} = fm1_level_gain[${param.l2}]; ${state.stage} = 2u; }
} else if (${state.stage} == 2u) {
    ${state.level} = fm1_madd_sat(${state.level},
        fm1_level_gain[${param.l3}] - ${state.level},
        fm1_q16_mul(fm1_rate_coeff[${param.r3}], ${in.rate_scale} << 1), 16);
    if (${state.level} <= fm1_level_gain[${param.l3}] + 8) { ${state.level} = fm1_level_gain[${param.l3}]; ${state.stage} = 3u; }
} else if (${state.stage} == 3u) {
    ${state.level} = fm1_level_gain[${param.l3}];
} else {
    ${state.level} = fm1_madd_sat(${state.level}, 0 - ${state.level},
        fm1_q16_mul(fm1_rate_coeff[${param.r4}], ${in.rate_scale} << 1), 16);
    if (${state.level} < 8) ${state.level} = 0;
}
${out.cv} = ${state.level};
