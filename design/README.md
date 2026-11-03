# p1onken interface language

The shared visual language for the Type P.fm1 web interface and the JUCE plugin.
The reference implementation is the clickable mockup at
`mockups/type-p-fm1-plugin.html`. The machine-readable source is `tokens.json`,
with a CSS projection in `tokens.css` and platform notes in `juce.md`.

Status: v1.1, 2026-11-03. Signed off on the mockup. Revised for the split
follow cards, part tune, filter env symmetry, centred algorithm graphs and the
two-row operator envelopes.

## Principles

1. Black is the room. Surfaces do not need outlines to exist.
2. Pink is identity and the primary value. Green is live signal and active state.
   Purple is selection and modulation. No other hues.
3. Controls are outlined. Content surfaces are not. If it cannot be clicked or
   typed into, it probably should not have a border.
4. Square corners, flat fills, no gradients, no blur, no glow. The only shadow is
   the solid offset behind the wordmark.
5. Type is lowercase and pixel-sharp. Headers use Zen Dots, everything else uses
   DotGothic16. The wordmark and user-entered names keep their case. The `fm1`
   suffix is lowercase Zen Dots.
6. Every label earns its place. No filler text such as voice counts, operator
   counts, or descriptions of what the product already is.
7. One algorithm per node, one meaning per colour, one home for every token.

## Colour

| Token | Hex | Role |
| --- | --- | --- |
| bg | `#000000` | window and page ground |
| panel | `#070707` | section and operator fill |
| popup | `#1b1b1b` | dialogs, popovers |
| line | `#1c1c1c` | hairlines inside dark surfaces |
| lineStrong | `#2e2e2e` | structural dividers, control borders |
| text | `#d2d2d2` | body text |
| dim | `#7d7d7d` | labels, secondary text |
| faint | `#4a4a4a` | hints, captions, inactive edges |
| white | `#ffffff` | dialog text, modulator blocks, high-contrast marks |
| pink | `#ff2e7e` | brand dot, carriers, primary values, active tab, unmuted tile |
| pinkBright | `#ff4d94` | knob values, hover on pink |
| purple | `#c780ff` | selection, modulation, pitch envelope, level fill, active scope mode |
| green | `#3dff9e` | live signal, enabled state, active part, output label |
| brandInk | `#d6d6d6` | wordmark |
| brandShadow | `#c2ad00` | solid wordmark shadow |

Rules:

- Pink is not a success colour. It is identity and primary emphasis.
- Green is not decoration. It means signal or an active path.
- Purple marks the selected or the modulating thing. Filter envelope and pitch
  LFO curves are green. Amplitude and pitch envelope curves are purple.
- Retire `panel2`, `green2`, `select` and `yellow` from new code. They were
  exploratory values and are not part of v1.

## Type

Families:

| Family | Use | Licence |
| --- | --- | --- |
| Zen Dots | section titles, tabs, operator and part names, dialog titles, toolbar labels, status, wordmark suffix | SIL Open Font License |
| DotGothic16 | all other interface text, values, labels, buttons, notes | SIL Open Font License |
| Digital Desolation Plus | `TYPE P.` wordmark prefix | unverified, do not bundle until cleared |

The mockup loads both OFL families from Google Fonts after first paint. A
production web build should self-host them. The JUCE build must bundle the OFL
files as binary resources. The current mockup uses `Arial Black` as the `TYPE P.`
prefix fallback because the brand font licence is not confirmed. The `fm1`
suffix always uses Zen Dots.

Scale:

| Role | Family | Size | Case |
| --- | --- | --- | --- |
| base | DotGothic16 | 16 | lower |
| knob name | DotGothic16 | 13 | lower |
| knob value | DotGothic16 | 16 | lower |
| inline label | DotGothic16 | 13 | lower |
| button | DotGothic16 | 12 | lower |
| button key hint | DotGothic16 | 11 | lower |
| mini button | DotGothic16 | 12 | lower |
| legend word | DotGothic16 | 11 | lower |
| legend glyph | DotGothic16 | 12 | lower |
| mute tile label | DotGothic16 | 13 | lower |
| note | DotGothic16 | 13 | lower |
| dialog body | DotGothic16 | 14 | lower |
| slot row | DotGothic16 | 15 | lower |
| select text | DotGothic16 | 9 | lower |
| brand line | DotGothic16 | 12 | lower |
| section title | Zen Dots | 11 | lower |
| tab | Zen Dots | 12 | lower |
| operator name | Zen Dots | 14 | lower |
| part name | Zen Dots | 12 | lower |
| dialog title | Zen Dots | 11 | lower |
| toolbar label | Zen Dots | 9 | lower |
| status | Zen Dots | 11 | lower |
| algorithm label | Zen Dots | 10 | lower |
| algorithm number | Zen Dots | 30 | lower |
| wordmark prefix | Digital Desolation Plus | 30 | as drawn |
| wordmark suffix | Zen Dots | 30 | lower |

Tracking is tight, between 0.01em and 0.06em. Section titles carry a `//` prefix
in `faint`. The wordmark is `TYPE P.` in the brand font and `fm1` in lowercase
Zen Dots. It keeps the solid shadow. Zen Dots has one weight, so the suffix uses
400 at the same 30px em size. The select text at 9px is the one survivor from the
old scale and should be reviewed when the real control is rebuilt.

## Metrics

| Item | Value |
| --- | --- |
| window width | 1240 |
| window height | 985 |
| window height note | fixed across pages, set by the operator page |
| page padding | 14 top, 16 sides, 16 bottom |
| grid gap | 10 |
| card padding | 9 |
| operator column padding | 8 |
| operator card padding | 8 |
| header padding | 14 by 16 |
| toolbar padding | 7 by 16 |
| tab padding | 11 by 16 |
| status padding | 7 by 16 |

Knob cells and dials:

| Context | Cell | Dial |
| --- | --- | --- |
| default | 52 | 42 |
| operator envelope | 37 | 34 |
| operator oscillator and amplitude LFO | 56 | 34 |
| part settings | 62 | 38 |
| pitch envelope | 52 | 38 |
| key follow and velocity follow | 64 | 42 |

Borders:

| Item | Rule |
| --- | --- |
| plugin frame | 1px `lineStrong` |
| structural dividers | 1px `lineStrong` |
| surfaces and cards | none |
| buttons, toggles, selects, inputs, sliders | 1px `lineStrong` |
| active part | 1px `green` |
| selected slot or row | 1px `purple` |
| focus | 1px `green` for text inputs, 1px `pink` for selects |
| accent corners | 11 by 11, 2px `pink`, top left and bottom right of the window |

Shape:

- Radius is always 0.
- The active tab is a cut polygon:
  `polygon(5px 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 7px) 100%, 0 100%, 5px 50%)`.
- No gradients. No blurred shadows. The wordmark shadow is a solid 4 by 4 offset
  in `brandShadow`.

## Components

### Header

Brand left, algorithm centre-left, output scope right, patch controls far right.
The wordmark is `TYPE P.` in the brand font and `fm1` in lowercase Zen Dots,
with a pink dot. The brand line is
`p1onken // パンク派第１音響合成研究班` in 12px DotGothic `dim`.

The algorithm block is a button. It shows a 30px Zen Dots number, a caret, and the
routing graph. The graph is 240 by 128 in the viewBox, scaled to about 244 by 130.
The graph content is centred in that viewBox, so the header and the picker tiles
share one optical centre. White operators are modulators, pink operators are
carriers, grey lines are modulation, purple downward arrows mark carrier output.
Clicking the block opens the algorithm picker. The mouse wheel over the block
cycles the eight algorithms without opening the picker.

The output section is a label plus a `scope` and `spectro` segmented control. The
active segment is purple. The plot is 50px high, borderless, black.

The patch control shows `patch` and the current patch name, with a separate
`rename` button.

### Toolbar

Left: the mute legend. A small dark square with a pink outline and pink 猫 means
muted. A solid pink square with a black 猫 means active. Then the real mute tiles,
`op1` to `op4` and `p1`, `p2`, at 36 by 22. An active tile is solid pink with a
black label. A muted tile is black with a pink outline and a pink label. The 猫 is
only a legend glyph, never a button label.

Right: `now editing part:` with `part 1`, `part 2` and `edit`. The selected part
button has a green border and green text.

### Tabs

`patch settings`, `operators`, `fx / mod`. No vertical dividers. The active tab is
a pink cut polygon, not a rectangle. Inactive tabs are dim text on black.

### Patch settings

Two part cards. The title is `part n: name` in Zen Dots. The active part has a
green border, the inactive part has no visible border. Each card holds rename,
copy, paste and a mute switch, five knobs, a wide level slider with the caption
`level`, and two borderless visualisers, one scope and one spectro. No captions on
the visualisers. The five knobs are `midi channel`, `keyzone start`, `keyzone
end`, `tune` and `delay`. `tune` is the part detune in cents. Then a voice mode
block with `poly`, `mono`, `legato`, `unison` and the unison, detune and porta
knobs.

### Operators

Four borderless columns. Each has the operator name, copy and paste, the mute
switch, a scope and spectro pair, and three cards: `oscillator`, `envelope`,
`amplitude lfo`. The oscillator card holds ratio, detune, level, feedback and the
wave select. The envelope holds R1 to R4 on the first row and L1 to L3 on the
second row. The amplitude LFO holds rate, depth and the wave select. The four
oscillator knobs spread across the card, the two LFO knobs sit apart, and the
envelope rates and levels each get their own row.

### FX / MOD

One page, a four by two grid that fills the window. Filters 1 and 2, filter
envelope and wavefolder fill the first row. Pitch LFO, pitch envelope, key follow
and velocity follow fill the second row. Each filter card has cutoff, resonance
and env amount. Key and velocity tracking live in the two follow cards, not on
the filter cards.

Key follow and velocity follow are separate cards. Each has an on switch, a
`wipe all` button and its own target selector. Key follow has a breakpoint and
below and above amounts. Velocity follow has one amount. The wipe button sets
every target amount to 0%, so the card can be cleared without visiting each
target. The same target set is used for both cards: operator level, feedback and
amp envelope, pitch envelope, filter 1 and 2 cutoff, and filter envelope.

### Dialogs

Patch browser and part slot lists are vertical scrollers with a thin scrollbar.
Rows show the slot number, the name, and the state. Selected rows use a purple
border and text. Confirmations use the same dialog frame. The algorithm picker is
a wide dialog with eight routing tiles. Each tile centres its graph in the figure
area and keeps `alg n` on its own line below, with enough tile height that the
graph cannot clip or touch the caption.

### Status

`midi` and `sync` with green LEDs. No editing text on the right.

## State language

| State | Visual |
| --- | --- |
| unmuted | solid pink tile, black label |
| muted | black tile, pink outline, pink label |
| switch active side | word `active` in pink, thumb left and pink |
| switch muted side | word `mute` in pink, thumb right and dark |
| active part | 1px green border, green part name |
| selected tab | pink cut polygon, black text |
| selected list row | purple border and text, faint purple fill |
| focus | green text input, pink select |
| hover | pink border on buttons, lighter knob name, underlined value, purple row |
| disabled | 30 to 35 percent opacity |

## Signal language

- Scope trace: green.
- Spectro bars: pink with a purple band every fifth band.
- Amplitude and pitch envelopes: purple.
- Filter envelope and pitch LFO: green.
- Level slider fill: purple.
- Enabled switches: green.
- Voice mode active button: green.
- Routing: white modulator, pink carrier, purple carrier output arrow.

## Copy

- Lowercase everything except the wordmark and user-entered names.
- Labels are nouns. `oscillator`, not `pitch`.
- Note readouts show both forms, for example `60/c4` and `127/g9`.
- The mute words are `active` and `mute`.
- Part titles are `part n: name`.
- Do not add descriptions of the obvious.

## Platform mapping

- Web: use `tokens.css`. The mockup remains the visual reference. A production
  page should load the OFL fonts non-blocking and keep local fallbacks.
- JUCE: see `juce.md`. Generate `UiTokens` from `tokens.json` rather than typing
  the values again. Bundle the OFL fonts. Keep GPL-3.0-only.
- HiDPI: draw in logical units and scale the whole editor uniformly. Do not scale
  individual strokes or font sizes.

## Working method

The process lessons from building this mockup are in `agent-workflow.md`. Read it
before changing the interface.

## Open items

- Confirm the Digital Desolation Plus licence before bundling it. Until then the
  `TYPE P.` prefix uses Arial Black and the `fm1` suffix uses Zen Dots.
- Review the 9px select text when the real control is built.
- The `part settings` page is intentionally sparse at the top and fills with the
  two part visualisers. Do not add filler widgets to fill space.
