/* wavetable reader: nearest-neighbor read of the selected table (256 entries). */
int32_t ${out.audio} = ${table.@}[${in.phase} >> 22];
