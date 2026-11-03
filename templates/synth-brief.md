# Synth brief

> Copy this file into your project and replace the prompts. Keep one brief as
> the source of truth. Delete options you reject instead of leaving them as
> maybe-decisions.

## 1. Instrument and player

- **Working name:**
- **Who plays it and in what setting:**
- **What should it feel like to play:**
- **Three reference sounds or pieces (and what you want from each):**
- **Explicit non-goals:**

## 2. Sound and voice architecture

- **Synthesis method(s):**
- **Polyphony and voice stealing:**
- **Pitch range and tuning:**
- **Oscillators / operators / noise:**
- **Filter(s) and resonance:**
- **Envelopes and velocity:**
- **Modulation (LFO, envelopes, macros):**
- **Effects and output stage:**
- **Multi-timbrality (`parts:`):** (number of parts. Each an independent timbre or
  shared. Per-part routing `channel` + keyzone `low`/`high`. Per-part gain/timing
  `level` + `delay`. Note→part routing rule. Layering allowed. Per-part voice pool)

### 2.1 Voice architecture (the node/macro graph)

> The graph that `patch.json` will express. A fresh reader must be able to draw
> it from this section alone. Feedback only via `delay1`/`delayN` (the graph is a
> DAG).

- **Voice-zone graph** (instance ids, node/macro types, wires, `voice_out`):
- **Global-zone graph** (single-instance: filter, effects, master):
- **Macros** (name, ins/outs, inner graph, params mapped inward):
- **Voice count / sample rate:**
- **Feedback paths** (only `delay1`/`delayN`):

### 2.2 Parameter manifest

> The source of the generated `params.json`. List **every** parameter. The GUI and
> MIDI map can only expose what is listed here (or marked internal).

| Param (name) | Target `<instance>.<param>` | Min | Max | Default | Curve | Unit | Rate | Modulatable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | | |

### 2.3 Tables

> Any wavetable / segments / spectrum / phase-map data (`tables:` → `const` XIP).

- **Table name → kind, shape/size/points:**


## 3. Controls and display

- **Keys, buttons, encoders, MASTER:**
- **Performance and navigation modes:**
- **Screen content and update rules:**
- **LED feedback:**
- **What must remain playable while the screen redraws:**

## 4. MIDI and connectivity

- **MIDI in / out / thru:**
- **Channels, velocity-zero note-off, sustain, panic:**
- **CC map** (fixed generator-assigned vs user-assignable. Which params. Sustain/panic/bend/program change):
- **Clock and transport:**
- **USB roles (MIDI, audio, update):**
- **Overflow and back-pressure behaviour:**

## 5. State and persistence

- **What survives reboot:**
- **Patch/sequence format and version:**
- **Storage budget and CRC/commit rule:**
- **Backup, import/export, migration, rollback:**

## 6. Browser prototype

- **What you want to hear or compare locally:**
- **Which parameters and MIDI controls the page needs:**
- **Supported browsers and offline expectation:**
- **What the browser must not be used to claim:**

## 7. Acceptance and evidence

- **Must-have features:**
- **Optional features:**
- **Supported-load profile (link):**
- **Host tests:**
- **Target package checks:**
- **Physical timing and device checks:**
- **Known unknowns and stop criteria:**

## 8. Confirmation

- **Brief owner:**
- **Date confirmed:**
- **Open questions that still change architecture:**
