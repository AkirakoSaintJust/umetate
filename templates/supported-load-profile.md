# Supported-load profile

> Record the simultaneous maxima you intend to support. A test outside this
> profile is informative, but it is not an acceptance failure unless the profile
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
| RAM | ≤ 96 KiB | build report | |
| Pool | ≤ 336 KiB | build report | |
| Code | ≤ 568 KiB | build report | |
| Stack | ≤ 24 KiB | build report | |
| Flash write pause | no audio during erase | design | |

## Worst-case test

- **Event script:**
- **Parameter extremes:**
- **Duration:**
- **Pass condition:**
- **Artifact:**

## Outside the profile

- **Behaviour when exceeded:**
- **User-visible diagnostic:**
- **Recovery:**

## Unknowns

- **What only a device can prove:**
- **What is blocked and why:**
