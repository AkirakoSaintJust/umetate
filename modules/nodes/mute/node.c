/* Output gate: 0 when `mute` is set, else the input passes through. */
int32_t ${out.audio} = ${param.mute} ? 0 : ${in.audio};
