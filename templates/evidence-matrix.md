# Evidence matrix

> Copy this into the project and attach exact commands/artifacts. A lower layer
> never proves a higher one. `blocked` and `not-run` are not passes. Validate
> with `umetate evidence`.

| Layer | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Source/static (`source`) | `not-run` | | Compiler, warnings, static checks |
| Host behavior (`host`) | `not-run` | | Command, vectors, artifacts |
| Browser/WASM (`browser`) | `not-run` | | Emscripten/browser versions, tolerance |
| Target package (`target`) | `not-run` | | Toolchain/SDK hashes, map/report |
| Emulator (`emulator`) | `not-run` | | fm1-emu run, model layer, not device |
| Physical timing (`timing`) | `not-run` | | Board/revision, callback time/headroom |
| Device acceptance (`device`) | `not-run` | | Controls, display, MIDI, persistence, power cycle |
| Release provenance (`release`) | `not-run` | | Source/package correspondence, notices |

## Status vocabulary

- `pass`: the named check ran and met its stated tolerance.
- `fail`: the named check ran and did not meet it.
- `blocked`: the check cannot run without a missing tool, device, or decision.
- `not-applicable`: the layer does not apply to this feature/project.
- `not-run`: no result yet. This is not a pass.
