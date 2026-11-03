# Custom code structure + interface

> The exact granular structure of any code the project must write, beyond the
> declarative `patch.json`/`panel.json`. When complete, translation is mechanical:
> every file, signature, and data-layout decision is already made here. Link this
> from `project-plan.md`. Do not duplicate it there.

> The invariant seam is `<synth>_dsp_*` (`<synth>` from the project name). The
> generator emits it from a patch, and a hand-written `dsp.c` must match the same
> shape (`firmware/README.md` §1, `docs/roadmap.md` §12.1).

## 1. Files

- **Created** (exact path, what it holds):
- **Modified** (exact path, why):
- **Forbidden to touch** (HAL registers, `platform.c` services, the loader,
  `uboot.boot`/`isd_config.ini`):

## 2. The seam (hand-written path) or the node (library path)

> Pick one and delete the other.

### Hand-written `dsp.c`

```c
// the exact signatures, with the `<synth>` prefix:
void <synth>_dsp_init(uint32_t sample_rate);
void <synth>_dsp_note_on(uint32_t note, uint32_t velocity);
void <synth>_dsp_note_off(uint32_t note);
void <synth>_dsp_all_notes_off(void);
int  <synth>_dsp_set_param(uint32_t id, int32_t value);
int32_t <synth>_dsp_get_param(uint32_t id);
uint32_t <synth>_dsp_param_count(void);
void <synth>_dsp_render(uint32_t frames);
const int32_t *<synth>_dsp_output(void);
```

### New node (`modules/nodes/<name>/`)

- **`node.json`** (ports, params, state, conform to `node.schema.json`):
- **`node.c`** core: `static inline void <name>_process(ctx, n)`:
- **Host test + budget annotation** (add both):

## 3. Data layout

- **Per-voice state**, SoA or struct, and why (SoA is the default for the hot loop):
- **Single-instance control state**, struct:
- **Section placement** (`.dsp_text` = hot code, `.pool` = big buffers,
  `.cpu1_bss` = engine state, `const` = XIP):

## 4. State publication

- **One writer per shared value, or a snapshot protocol** (which, and the order):
- **What `volatile` alone is not enough for:**

## 5. Host-test hook

- **Which test file exercises it, and the vector** (silence → note-on → release.
  clamp at extremes. Out-of-range id rejected):

## 6. Forbidden dependencies (re-check)

- [ ] No allocation, `float`/`double`, or 64-bit division in the audio path.
- [ ] No display, flash, logging, blocking, or per-sample dispatch.
