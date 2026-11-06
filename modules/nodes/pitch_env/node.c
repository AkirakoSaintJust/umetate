/* Per-note pitch envelope (control rate). on/off + 4 rates (0..99) + 3 levels
   (Q15 pitch offset, bipolar). Retriggers to attack on every note-on
   (`trigger` = voice_trig[v]), and a gate edge starts release. A key-follow factor
   `k` (Q15) pushes each rate toward 0 (slower) or 99 (faster), so the effective
   rates are block-derived. The stages run 0=attack (0->l1), 1=decay1 (l1->l2),
   2=decay2 (l2->l3), 3=sustain (hold l3), 4=release (->0), and the levels are
   signed, so the stage transitions use an absolute distance. No local declarations
   (inlined once per operator). */
if (${in.trigger}) { ${state.stage} = 0u; ${state.level} = 0; }
if (${in.gate}) {
    if (${state.stage} == 4u) { ${state.stage} = 0u; ${state.level} = 0; }
} else if (${state.stage} != 4u) {
    ${state.stage} = 4u;
}

if (${state.stage} == 0u) {
    ${state.level} = fm1_onepole(${state.level}, ${param.l1}, fm1_rate_coeff[${state.r1_eff}]);
    if ((${state.level} >= ${param.l1} ? ${state.level} - ${param.l1} : ${param.l1} - ${state.level}) <= 8) { ${state.level} = ${param.l1}; ${state.stage} = 1u; }
} else if (${state.stage} == 1u) {
    ${state.level} = fm1_onepole(${state.level}, ${param.l2}, fm1_rate_coeff[${state.r2_eff}]);
    if ((${state.level} >= ${param.l2} ? ${state.level} - ${param.l2} : ${param.l2} - ${state.level}) <= 8) { ${state.level} = ${param.l2}; ${state.stage} = 2u; }
} else if (${state.stage} == 2u) {
    ${state.level} = fm1_onepole(${state.level}, ${param.l3}, fm1_rate_coeff[${state.r3_eff}]);
    if ((${state.level} >= ${param.l3} ? ${state.level} - ${param.l3} : ${param.l3} - ${state.level}) <= 8) { ${state.level} = ${param.l3}; ${state.stage} = 3u; }
} else if (${state.stage} == 3u) {
    ${state.level} = ${param.l3};
} else {
    ${state.level} = fm1_onepole(${state.level}, 0, fm1_rate_coeff[${state.r4_eff}]);
    if (${state.level} < 8 && ${state.level} > -8) ${state.level} = 0;
}
${out.cv} = ${param.on} ? ${state.level} : 0;
