# Worked example: Pocket Drone (two-op FM)

Pocket Drone is a worked design for the blueprint in `docs/roadmap.md` §12. It
shows where the declarative patch meets implementation details, and records gaps
to resolve. The generator is not implemented yet, so the `dsp.c` below is a sketch
of the code it is expected to emit.

## 1. The synth

A two-operator FM pad: 8 voices, each voice two operators (carrier + modulator).
Each operator = `phasor` + `osc` + `env` + `vca`. The modulator phase-modulates the
carrier (audio-rate `fm`), with 1-sample feedback on the modulator. Global chain:
a lowpass `svf` + a `delayN`. Seven params (carrier ratio, mod ratio, filter
cutoff/res, delay time/feedback, master).

## 2. patch.json

```jsonc
{
  "name": "pocket-drone",
  "voices": 8,
  "sample_rate": 44100,
  "tables": {
    "sine":     { "kind": "wavetable", "size": 1024 },
    "env_adsr": { "kind": "segments",  "source": "adsr" }
  },
  "macros": {
    "op": {
      "ins":  { "gate": "event", "freq": "control", "fm": "audio" },
      "outs": { "audio": "audio" },
      "params": { "ratio": "ph.ratio", "level": "vca.level" },   // NOTE: ph.ratio is state, not a port
      "nodes": [
        { "id": "ph",  "type": "phasor" },
        { "id": "osc", "type": "osc" },
        { "id": "env", "type": "env" },
        { "id": "vca", "type": "vca" }
      ],
      "wires": [
        { "from": "freq", "to": "ph.inc" },                       // NOTE: inc is state
        { "from": "fm",   "to": "ph.fm" },
        { "from": "ph.phase", "to": "osc.phase" },
        { "from": "osc.audio", "to": "vca.audio" },
        { "from": "gate", "to": "env.gate" },
        { "from": "env.cv", "to": "vca.cv" },
        { "from": "vca.audio", "to": "audio" }
      ]
    }
  },
  "voice": {
    "nodes": [
      { "id": "carrier", "type": "op", "params": { "ratio": 1 } },
      { "id": "mod",     "type": "op", "params": { "ratio": 2 } },
      { "id": "d1",      "type": "delay1" }
    ],
    "wires": [
      { "from": "note", "to": "carrier.freq" },
      { "from": "note", "to": "mod.freq" },
      { "from": "gate", "to": "carrier.gate" },
      { "from": "gate", "to": "mod.gate" },
      { "from": "mod.audio", "to": "carrier.fm" },               // FM: mod → carrier phase
      { "from": "mod.audio", "to": "d1.in" },
      { "from": "d1.out",    "to": "mod.fm" }                    // 1-sample feedback
    ]
  },
  "global": {
    "nodes": [ { "id": "lp", "type": "svf" }, { "id": "delay", "type": "delayN" } ],
    "wires": [
      { "from": "voice", "to": "lp.audio" },                     // NOTE: "voice" is implicit
      { "from": "lp.audio", "to": "delay.in" },
      { "from": "delay.out", "to": "out" }
    ]
  }
}
```

## 3. panel.json

```jsonc
{
  "name": "pocket-drone",
  "home": "home",
  "global": [
    { "source": "FM1_ADC_MASTER", "target": "master", "behavior": "absolute" },
    { "source": "KEY",            "action": "note_on" },
    { "source": "cc:123",         "action": "panic" }
  ],
  "contexts": {
    "home": {
      "pages": [
        { "id": "home", "widgets": [
          { "type": "label",     "row": 0, "text": "DRONE" },
          { "type": "param_row", "row": 1, "param": "carrier_ratio", "unit": "" },
          { "type": "param_row", "row": 2, "param": "mod_ratio",     "unit": "" },
          { "type": "param_row", "row": 3, "param": "filter_cutoff", "unit": "Hz" } ] }
      ],
      "bindings": [
        { "source": "ENC_KNOB1", "target": "filter_cutoff", "behavior": "absolute", "curve": "log" },
        { "source": "ENC_KNOB2", "target": "mod_ratio",     "behavior": "absolute" },
        { "source": "BTN_EDIT",  "action": "push", "arg": "edit" }
      ]
    },
    "edit": {
      "pages": [
        { "id": "op",   "widgets": [ { "type": "param_row", "row": 1, "param": "carrier_ratio" } ] },
        { "id": "fx",   "widgets": [ { "type": "param_row", "row": 1, "param": "delay_time" } ] }
      ],
      "bindings": [
        { "source": "ENC_SELECT", "action": "next_page" },
        { "source": "BTN_HOME",   "action": "pop_home" },
        { "source": "ENC_KNOB1",  "target": "carrier_ratio", "behavior": "absolute" }
      ]
    }
  }
}
```

## 4. Generated `dsp.c` (sketch)

```c
/* GENERATED — do not edit */
#define NVOICE 8

static uint32_t UMETATE_CPU1 carrier_ph_phase[NVOICE], carrier_ph_inc[NVOICE];
static uint32_t UMETATE_CPU1 mod_ph_phase[NVOICE],     mod_ph_inc[NVOICE];
static int32_t  UMETATE_CPU1 carrier_env_level[NVOICE], mod_env_level[NVOICE];
static uint8_t  UMETATE_CPU1 carrier_env_stage[NVOICE], mod_env_stage[NVOICE];
static int32_t  UMETATE_CPU1 d1_prev[NVOICE];          /* delay1 feedback, per voice */
static int32_t  UMETATE_CPU1 lp_z1, lp_z2;
static int16_t  UMETATE_POOL delay_buf[DELAY_SAMPLES]; static uint32_t UMETATE_CPU1 delay_idx;

void pocket_drone_render(int32_t *out, uint32_t frames) {
    for (uint32_t b = 0; b < frames; b += CONTROL_BLOCK) {
        /* control prologue: advance envelopes, recompute filter coeffs */
        for (uint32_t f = b; f < b + CONTROL_BLOCK; f++) {
            int32_t bus = 0;
            for (uint32_t v = 0; v < NVOICE; v++) {
                /* modulator (with 1-sample feedback) */
                uint32_t m = mod_ph_phase[v] + mod_ph_inc[v] + d1_prev[v];
                int32_t ms = sine[m >> 22];
                int32_t mo = (ms * mod_env_level[v]) >> 16;
                mod_ph_phase[v] = m; d1_prev[v] = mo;
                /* carrier (fm = modulator out) */
                uint32_t c = carrier_ph_phase[v] + carrier_ph_inc[v] + mo;
                int32_t cs = sine[c >> 22];
                int32_t co = (cs * carrier_env_level[v]) >> 16;
                carrier_ph_phase[v] = c;
                bus += co;                              /* mix voice into bus */
            }
            int32_t lp = svf_step(&lp_z1, &lp_z2, bus);
            int32_t dl = delay_step(&delay_buf, &delay_idx, lp);
            out[f*2] = dl; out[f*2+1] = dl;
        }
    }
}
```

The sketch makes the intended render structure concrete: SoA voice state,
one-sample `d1_prev` feedback, a per-voice loop, the voice-to-bus mix, and the
global effects chain.

## 5. Lessons (what the example exposed)

1. **`inc` is state, so the note→increment path is the allocator's, not a wire.**
   The `op` macro wired `freq → ph.inc` and `ratio → ph.ratio`, but `inc` is a state
   field (set at note-on from `note × ratio`), not a port. → The patch needs a
   **note-derived input**: the allocator computes `inc = note_to_inc(note) × ratio`
   and stores it, so a macro's `freq`/`ratio` inputs are *allocator bindings*, not
   graph edges. Add an explicit "note inputs" concept to the voice zone.

2. **The voice→global mix boundary is implicit.** `{"from": "voice"}` is
   ambiguous — the generator needs to know *which* voice-zone signal is summed into
   the bus. → Declare a named `voice_out` (the voice-zone signal to mix), and the
   generator emits the NVOICE→1 sum there.

3. **Velocity was un-wired.** Velocity should scale the VCA (envelope × velocity).
   → The voice zone's `velocity` input is a reserved allocator input wired to the
   vca's level, like `gate`.

4. **Mod depth = modulator level.** The FM index is just the modulator's VCA output
   (envelope × level) — no separate "depth" param needed. Confirmed by the example,
   matches Dexed/ymfm.

5. **Macro params map inward to *state or ports*, not just ports.** `ratio` targets
   the phasor's `inc` (state), `level` targets the vca's param. → The macro param
   mapping must allow a `state` target (handled at note-on), not only `port` targets.

The roadmap records these gaps in §12.4 (pass 5), and `patch.schema.json` will
need to reflect the decisions before the generator is implemented.
