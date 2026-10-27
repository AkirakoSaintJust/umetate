/* linear attack/release (Q15). Runs at control rate (once per sub-block). */
${out.cv} = ${state.level};
if (${in.gate}) {
    ${state.level} += ${param.attack};
    if (${state.level} > 32767) ${state.level} = 32767;
} else {
    ${state.level} -= ${param.release};
    if (${state.level} < 0) ${state.level} = 0;
}
