/* DX-style rate/level envelope (control rate). Exponential one-pole per stage —
   the rate/level character of ymfm/Dexed (§3.2), with the rate as a Q16 one-pole
   coefficient. Stages: 0=attack (0→l1), 1=decay1 (l1→l2), 2=decay2 (l2→l3),
   3=sustain (hold l3), 4=release (→0). `level` is Q15 gain; a gate edge resets
   attack (on) or starts release (off). */
if (${in.gate}) {
    if (${state.stage} == 4u) { ${state.stage} = 0u; ${state.level} = 0; }
} else if (${state.stage} != 4u) {
    ${state.stage} = 4u;
}

if (${state.stage} == 0u) {
    ${state.level} = fm1_madd_sat(${state.level}, ${param.l1} - ${state.level}, ${param.r1}, 16);
    if (${state.level} >= ${param.l1} - 8) { ${state.level} = ${param.l1}; ${state.stage} = 1u; }
} else if (${state.stage} == 1u) {
    ${state.level} = fm1_madd_sat(${state.level}, ${param.l2} - ${state.level}, ${param.r2}, 16);
    if (${state.level} <= ${param.l2} + 8) { ${state.level} = ${param.l2}; ${state.stage} = 2u; }
} else if (${state.stage} == 2u) {
    ${state.level} = fm1_madd_sat(${state.level}, ${param.l3} - ${state.level}, ${param.r3}, 16);
    if (${state.level} <= ${param.l3} + 8) { ${state.level} = ${param.l3}; ${state.stage} = 3u; }
} else if (${state.stage} == 3u) {
    ${state.level} = ${param.l3};
} else {
    ${state.level} = fm1_madd_sat(${state.level}, 0 - ${state.level}, ${param.r4}, 16);
    if (${state.level} < 8) ${state.level} = 0;
}
${out.cv} = ${state.level};
