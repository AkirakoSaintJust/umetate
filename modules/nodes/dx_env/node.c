/* DX-style rate/level envelope (control rate). It has four rates and three levels,
   all 0..99 on the Yamaha scale. Each stage advances `level` toward its target by
   the rate's one-pole coefficient (`fm1_rate_coeff[r_eff]`, Q16), scaled by
   `rate_scale`, which is velocity -> envelope rate (Q15 unity 32768, always
   >= 0), whilst a key-follow factor `k` (Q15) pushes each rate toward 0 (slower)
   or 99 (faster) and the effective rates are block-derived. The decay 2 stage
   uses `fm1_rate_coeff_r3`, a separate curve whose rate 1 is the OPM's slowest
   D2R time and whose 99 steps cover the OPM's 31 with more resolution. Levels are total-level
   0..99 -> Q15 gain via `fm1_level_gain`. A stage ends when it is within 8 units
   of its target on the side it is moving toward, so a target above the current
   level runs up instead of snapping. A level of 99 is max and 0 is silence.
   `trigger` (default `voice_trig[v]`) resets to attack on a note-on edge, even
   mid-note (a voice steal). Stages: 0=attack (0->l1), 1=decay1 (l1->l2),
   2=decay2 (l2->l3), 3=sustain (hold l3), 4=release (->0). A gate edge starts
   release. There are no local declarations, because the body is inlined once per
   operator, so every value is an inline expression. */
if (${in.trigger}) { ${state.stage} = 0u; ${state.level} = 0; }
if (${in.gate}) {
    if (${state.stage} == 4u) { ${state.stage} = 0u; ${state.level} = 0; }
} else if (${state.stage} != 4u) {
    ${state.stage} = 4u;
}

if (${state.stage} == 0u) {
    ${state.level} = fm1_onepole(${state.level},
        fm1_level_gain[${param.l1}],
        fm1_q16_mul(fm1_rate_coeff[${state.r1_eff}], ${in.rate_scale} << 1));
    if (fm1_level_gain[${param.l1}] >= ${state.level}
            ? ${state.level} >= fm1_level_gain[${param.l1}] - 8
            : ${state.level} <= fm1_level_gain[${param.l1}] + 8) {
        ${state.level} = fm1_level_gain[${param.l1}]; ${state.stage} = 1u;
    }
} else if (${state.stage} == 1u) {
    ${state.level} = fm1_onepole(${state.level},
        fm1_level_gain[${param.l2}],
        fm1_q16_mul(fm1_rate_coeff[${state.r2_eff}], ${in.rate_scale} << 1));
    if (fm1_level_gain[${param.l2}] >= ${state.level}
            ? ${state.level} >= fm1_level_gain[${param.l2}] - 8
            : ${state.level} <= fm1_level_gain[${param.l2}] + 8) {
        ${state.level} = fm1_level_gain[${param.l2}]; ${state.stage} = 2u;
    }
} else if (${state.stage} == 2u) {
    ${state.level} = fm1_onepole(${state.level},
        fm1_level_gain[${param.l3}],
        fm1_q16_mul(fm1_rate_coeff_r3[${state.r3_eff}], ${in.rate_scale} << 1));
    if (fm1_level_gain[${param.l3}] >= ${state.level}
            ? ${state.level} >= fm1_level_gain[${param.l3}] - 8
            : ${state.level} <= fm1_level_gain[${param.l3}] + 8) {
        ${state.level} = fm1_level_gain[${param.l3}]; ${state.stage} = 3u;
    }
} else if (${state.stage} == 3u) {
    ${state.level} = fm1_level_gain[${param.l3}];
} else {
    ${state.level} = fm1_onepole(${state.level}, 0,
        fm1_q16_mul(fm1_rate_coeff[${state.r4_eff}], ${in.rate_scale} << 1));
    if (${state.level} < 8) ${state.level} = 0;
}
${out.cv} = ${state.level};
