# Build your own M-VAVE FM-1 / SMK-37 synthesizer

A workshop for programmers who know the sound they want but are new to the FM-1,
embedded audio, and the umetate workflow. You start from the source-built RIB
firmware, design an instrument, prototype its sound, then develop and verify
firmware in small, measured increments.

> **Safety and evidence.** Never flash as a side effect of editing code. Identify a
> real recovery route before installing. Source, host, browser, target package,
> emulator, timing, and device acceptance are separate evidence layers — a lower
> layer never proves a higher one. Use `pass` / `fail` / `blocked` / `not-run`.

## The 13 stages

| § | Stage | Outcome | Evidence layer | Hardware |
| --- | --- | --- | --- | --- |
| 1 | What umetate is; RIB as the runtime; the framework on top | correct mental model | docs | no |
| 2 | Safety before hardware (hard-brick risk, backup limits, recovery) | informed consent + a backup plan | docs | no |
| 3 | Verify the environment (`umetate quick-check`) | a green/blocked report | host | no |
| 4 | Build untouched RIB; host tests; browser lab | first sound in the browser | host/browser | no |
| 5 | The firmware contract (`app_audio`, `app_main`, `platform_poll`, HAL) | a correct app skeleton | source | no |
| 6 | Design the instrument (brief, feature contracts, load profile) | a bounded design | docs | no |
| 7 | Author the synth (nodes/macros/patches; or hand-written `dsp.c`) | a working voice | host | no |
| 8 | Controls, MIDI, screen, storage | a playable instrument | host/browser | no |
| 9 | Test (host, browser parity, target package, fm1-emu, evidence) | a recorded evidence set | host/target | no |
| 10 | Install (identity, backup, installer, verify) | a safe install plan | docs | yes |
| 11 | Validate on device (audio, MIDI, USB, stress, recovery) | a device record | device | yes |
| 12 | Troubleshoot and recover (route taxonomy) | a known recovery path | docs/device | maybe |
| 13 | Record evidence and release provenance | a traceable release | release | no |

## Core commands

```sh
umetate quick-check         # verify the environment (read-only)
umetate scaffold patch --name "My Synth" --out examples/my-synth   # author a synth
umetate deep-check --host   # run the host-side checks
umetate build --board fm1 --model pro                              # a target package (no flash)
```

Every stage states its evidence layer and a no-hardware path. Target timing and
device acceptance require the actual FM-1/SMK-37; installation requires the
separate approval, backup, power, identity, and recovery gates.
