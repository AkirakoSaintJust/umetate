# Evidence matrix

> Copy this into the project, attach the exact commands and artefacts, and
> validate it with `umetate evidence`. A lower layer never proves a higher one,
> and a `blocked` or `not-run` row counts as unfinished work rather than a pass.

| Layer | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Source/static (`source`) | `not-run` | | Compiler, warnings, static checks |
| Host behaviour (`host`) | `not-run` | | Command, vectors, artefacts |
| Browser/WASM (`browser`) | `not-run` | | Emscripten/browser versions, tolerance |
| Target package (`target`) | `not-run` | | Toolchain/SDK hashes, map/report |
| Emulator (`emulator`) | `not-run` | | fm1-emu run, model layer rather than the device |
| Physical timing (`timing`) | `not-run` | | Board/revision, callback time/headroom |
| Device acceptance (`device`) | `not-run` | | Controls, display, MIDI, persistence, power cycle |
| Release provenance (`release`) | `not-run` | | Source/package correspondence, notices |

## Status vocabulary

- `pass`: the named check ran and met its stated tolerance.
- `fail`: the named check ran and did not meet it.
- `blocked`: the check cannot run without a missing tool, device, or decision.
- `not-applicable`: the layer does not apply to this feature/project.
- `not-run`: no result yet. This is not a pass.
