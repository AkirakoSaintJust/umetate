# JUCE mapping

How the p1onken interface language becomes a JUCE editor. The visual reference is
`mockups/type-p-fm1-plugin.html`, the source values are `tokens.json`, and the
product rules are in `README.md`.

Scope: a reusable plugin host inside umetate plus a generated `type-p-fm1`
project. The first targets are VST3 and CLAP on Windows, macOS and Linux. AU is a
later macOS addition.

Status: Milestone 3 implements this mapping. `plugin/tools/gen_tokens.py` emits
`UiTokens.h`, the editor is `plugin/juce/PluginEditor.*` and `plugin/ui/*`, and
`plugin_editor_snapshot` renders the pages and dialogs for review.

## One source of tokens

Do not retype colours, sizes or metrics in C++. Generate a `UiTokens.h` from
`tokens.json` at configure time, or commit the generated header and check it in a
test. Every value in the editor must come from that header.

Suggested shape:

```cpp
namespace p1::tokens {
inline constexpr auto bg = 0xff000000;
inline constexpr auto pink = 0xffff2e7e;
inline constexpr float baseText = 16.0f;
inline constexpr int windowWidth = 1240;
}
```

The generator is part of the plugin host, not the firmware. It keeps the web and
JUCE sides from drifting.

## Colour

Map each hex token to `juce::Colour` with an opaque alpha. Draw fills with
`fillRect` and `fillPath`. Do not use gradients, rounded rectangles, blurs or
glow.

- Window ground `bg`.
- Section fills `panel`.
- Dialogs `popup`.
- Structural lines `lineStrong`.
- Hairlines `line`.
- Primary values `pinkBright`.
- Carriers, active tab and unmuted tiles `pink`.
- Selection and modulation `purple`.
- Signal, enabled state and active part `green`.
- Body text `text`, labels `dim`, hints `faint`.

## Fonts

Bundle DotGothic16 and Zen Dots as binary resources. Both are SIL Open Font
License. Do not load them from the network in the plugin.

- Zen Dots: section titles, tabs, operator and part names, dialog titles, toolbar
  labels, status, algorithm number and the lowercase `fm1` wordmark suffix.
- DotGothic16: everything else, including values, labels, buttons and notes.
- Digital Desolation Plus: do not bundle until the licence is confirmed. Use the
  Arial Black fallback for the `TYPE P.` wordmark prefix in the first build. Draw
  `fm1` with Zen Dots in both cases.

JUCE takes a font height in logical pixels. Use the CSS pixel sizes from
`tokens.json` directly at 1x. Keep the whole editor on one uniform scale factor
instead of scaling individual fonts and strokes.

Check the Japanese glyph coverage for the brand line
`p1onken // パンク派第１音響合成研究班` and for the 猫 legend glyph. DotGothic16
covers both.

## Layout

- Design at 1240 logical pixels wide.
- Height is fixed at 985 logical pixels and shared by every page. Do not let page
  changes resize the editor.
- Apply one uniform scale to the whole 1240 wide layout when the host gives a
  different editor size. Do not reflow the design.
- Use integer rectangles and align 1px strokes to the pixel grid.
- Page padding is 14 top, 16 sides and 16 bottom.
- Grid gap is 10. Card padding is 9. Operator columns add 8 padding and a 6 gap.

Every page fills the same height:

- patch settings: two part cards, each with five knobs, a level slider and a
  scope and spectro that grow to fill the remaining card height, then the voice
  mode block.
- operators: four columns with oscillator, envelope and amplitude LFO. The
  envelope uses one row for R1 to R4 and a second row for L1 to L3.
- fx / mod: a four by two grid. Filters, filter envelope and wavefolder on the
  first row. Pitch LFO, pitch envelope, key follow and velocity follow on the
  second row. The two follow cards are separate and each has its own on switch
  and wipe button.

## Header

- Draw `TYPE P.` with the brand font and `fm1` with Zen Dots, both at the 30px
  wordmark size. Keep the solid `brandShadow` offset behind the whole wordmark.
- The algorithm block is a button. Draw the 30px number, the caret and the 240 by
  128 graph. Centre the graph content in its viewBox so the header and the picker
  tiles share one optical centre.
- Clicking the algorithm block opens the picker. The mouse wheel over the block
  cycles the active part's algorithm and must not open the picker.
- In the picker, reserve the caption line below each graph. Centre the graph in the
  remaining figure area so it cannot clip or touch `alg n`.

## Shape and borders

- Radius is 0. Use `fillRect` and `drawRect`, not rounded helpers.
- Surfaces have no border. Only controls, selected states and the structural
  frame carry a 1px stroke.
- The plugin frame is 1px `lineStrong`. Add the 11 by 11 pink corner brackets at
  the top left and bottom right with a 2px stroke.
- The active tab is a `juce::Path` built from the token polygon. Fill it pink and
  draw the text in black. Inactive tabs have no dividers.
- Focus rings are 1px. Green for text entry, pink for selects.

## Controls

Knobs are custom painted. Each cell has a 270 degree track, a pink arc from the
start to the value, a white pointer, a name below and a value below that. Click
the value to type a number. Enter commits, Escape cancels, values are clamped and
stepped.

Context sizes:

- default 52 cell, 42 dial
- operator envelope 37 cell, 34 dial
- operator oscillator and amplitude LFO 56 cell, 34 dial
- part settings 62 cell, 38 dial
- pitch envelope 52 cell, 38 dial
- key follow and velocity follow 64 cell, 42 dial

Mute controls are tiles, not switches. Active is a solid pink tile with a black
label such as `op1` or `p1`. Muted is a black tile with a pink outline and a pink
label. The 猫 squares in the toolbar legend are illustrative only.

Part and operator mute switches use the inline form `active [track] mute`. The
word for the current state is pink and the other word is faint.

The level slider is a 14px track with a purple fill and a `level` caption.

List dialogs scroll. Patch browser rows are 260px maximum. Part slots are 240px
maximum. Use a thin scrollbar. Names use the device record limit of 15
characters, so the plugin banks round-trip with the device.

## Visualisers

- Scope: green trace on black, no frame.
- Spectro: pink bars with a purple band every fifth band.
- Amplitude and pitch envelopes: purple.
- Filter envelope and pitch LFO: green.
- Routing graph: white modulators, pink carriers, grey modulation lines, purple
  downward arrows under every carrier.

Use a `juce::Timer` at about 30 Hz for repaint. Feed it from a lock-free ring
buffer written by the audio thread. No allocation, locks or file access on the
audio thread. The visualisers are optional and must degrade to a flat line when
the host disables them.

## Parameters

`examples/type-p-fm1/patch.json` is the source of truth. The plugin exposes the
same parameter set and the same ranges. Group them to match the pages, not to
match the JSON order.

- patch settings: parts, keyzones, levels, delays, voice mode.
- operators: four sets of oscillator, envelope and amplitude LFO parameters.
- fx / mod: filters, envelopes, wavefolder, pitch LFO, pitch envelope, key and
  velocity follow.
- global: algorithm and patch name.

Use stable parameter IDs derived from the manifest. Host automation, state save
and restore, and the web lab must all agree.

## Audio

The engine is 44.1 kHz locked. The plugin runs the same core and resamples the
output to the host rate. Do not resample the input or change the core rate.

## Licensing

- Plugin code: GPL-3.0-only, matching umetate.
- Fonts: DotGothic16 and Zen Dots under the SIL Open Font License. Include the
  licence text with the binaries.
- Brand font: not bundled until the licence is verified.
- JUCE: use the GPLv3 path, and record the JUCE version in the build manifest.

## Open items

- Confirm the brand font licence. Until then the `TYPE P.` prefix uses Arial
  Black with a default bold sans fallback.
- Decide whether AU joins VST3 and CLAP in the first macOS build.
- Device preset bank import and export through SysEx is a later milestone. The
  in-plugin 64 multi and 128 part banks are in.
