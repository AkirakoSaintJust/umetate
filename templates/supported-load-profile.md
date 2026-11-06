# Supported-load profile

> Record the simultaneous maxima you intend to support. A test outside this
> profile is informative, though it isn't an acceptance failure unless the profile
> says so.

## Profile

- **Name/version:**
- **Board(s):** FM-1 / SMK-37 Pro / Elite / MKE-P37
- **Sample rate and callback:** 44.1 kHz, 256 frames (5.8 ms nominal)
- **Voices:**
- **Oscillators/operators per voice:**
- **Noise sources:**
- **Filters:**
- **Envelopes/LFOs:**
- **Effects:**
- **Sequencer/event rate:**
- **Panel/USB/display activity during the test:**
- **MIDI burst (events per ms):**
- **Persistence/flash activity:**

## Resource targets

| Resource | Target | Evidence class | Measured |
| --- | --- | --- | --- |
| Audio callback | ≤ 2.9 ms (50% of 5.8 ms) | estimated / host / target | |
| CPU0 `.data`/`.bss` | ≤ 96 KiB | build report | |
| CPU1 `.cpu1_bss` | ≤ 16 KiB | build report | |
| `.dsp_text` (hot DSP code) | ≤ 32 KiB | build report | |
| `.pool` (delay lines) | ≤ 336 KiB | build report | |
| XIP code + const | ≤ 568 KiB | build report | |
| Stack | 24 KiB CPU0 + 8 KiB CPU1 | build report | |
| Flash write pause | no audio during erase | design | |

## Worst-case test

- **Event script:**
- **Parameter extremes:**
- **Duration:**
- **Pass condition:**
- **Artefact:**

## Outside the profile

- **Behaviour when exceeded:**
- **User-visible diagnostic:**
- **Recovery:**

## Unknowns

- **What only a device can prove:**
- **What is blocked and why:**
