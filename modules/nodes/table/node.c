/* Wavetable reader: nearest-neighbour read of the selected table (256 entries,
   the top 8 bits of phase). */
int32_t ${out.audio} = ${table.@}[${in.phase} >> 24];
