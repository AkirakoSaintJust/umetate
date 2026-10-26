/* sine via the pi32v2 ROM/hardware transcendental (fm1_sin). */
int32_t ${out.audio} = fm1_sin(${in.phase});
