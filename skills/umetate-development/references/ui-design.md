# Designing an instrument interface

Read this before any panel, screen, editor, or web UI work. The Type P.fm1
language is in `design/README.md`. The casebook and research links are in
`ui-dossier.md`.

## One rule

The interface is designed before it is written.

The Type P.fm1 firmware UI was underspecified on the first pass. Button meanings,
page contents, and per-parameter semantics were decided while the panel was being
coded. The result was buggy, incomplete, and cryptic, and the navigation map had
to be re-derived after the code existed. The fix was not more code. It was a
written control map, a written brief, and a mockup that was signed off before the
panel was authored. The full lesson is L8 and L10 in `docs/roadmap.md`.

The plugin editor followed the same rule. The design language was fixed first,
the mockup was made clickable, the tokens were extracted, and only then was the
JUCE editor built. The editor projects the tokens. It is not a new design.

## The meaning of "determined"

A UI is not specified until all of these are written and checkable. This is the
minimum bar. Do not author the panel or the editor until each one is filled in.

1. **Surface inventory.** Every physical control, its kind, its printed label, and
   the controls that are deliberately unmapped.
2. **Button map.** Every button and encoder, its single-press meaning, every
   multi-tap and hold chord, and what each chord replaces. A chord that mutes
   must not also fire a note.
3. **Menu and page map.** Every menu, its pages in order, the exact page count,
   and each page's contents.
4. **Always-visible header.** The fields shown on every page, without exception.
   For Type P.fm1: active part, active operator, mute states, algorithm, current
   menu, and page N/M.
5. **Parameter placement.** Which menu owns each parameter. No parameter is
   reachable only by accident.
6. **Per-parameter display form.** The display form (`raw`, `ratio`, `pct`,
   `onoff`, `hz`, `semi`, and so on), the user-facing range, the unit, and the
   stepping curve. Clamp the value to the same range the display uses, so the
   display and the value never disagree.
7. **Widget layout.** Which widget each page draws, in what order, including the
   empty space. Do not add a widget to fill a hole.
8. **Preset browser and save chooser.** The trigger, the timeout, the load and
   erase rule, and the confirmation for a destructive save.
9. **INIT PATCH and INIT PART defaults.** The exact values. "Same as the other
   one" is not a specification.
10. **Screen rules.** The redraw model and rate, no display work in the audio
    callback, a full clear on page change, and held notes still playable during a
    redraw.

The same list works for a plugin editor, with "screen" replaced by "editor page"
and "button" replaced by "control". The plugin adds host automation, resizing,
and keyboard focus to item 10.

## Design loop

This is the loop that produced the Type P.fm1 mockup and the JUCE editor.

1. **Orient.** Read the brief, the control map, the parameter manifest, the
   tokens, and the current mockup. The manifest is the only reference. Do not
   invent a control that has no parameter.
2. **Decide one set.** Take the smallest coherent set of changes. Do not batch
   unrelated restyles.
3. **Write the spec.** Fill the missing items from the list above before touching
   the mockup. If a feature is hard to draw, the feature is not ready.
4. **Mock up in the real medium.** HTML for the web and the plugin. The panel
   emulator for firmware. Do not start in C++.
5. **Render at 1x.** Open the page at a fixed viewport, capture the full page, and
   capture the dense areas zoomed in. A screenshot can lie about timing. Read it
   only after the browser or capture has finished.
6. **Inspect.** Check labels, collisions, clipping, scrollbars, alignment, and the
   fixed height. Check the state as well as the default page.
7. **Test the interaction.** Open the dialogs, change a value, mute a part, switch
   a tab, type a name, and cancel a destructive action. A static screenshot does
   not prove a control works.
8. **Measure.** The window height is a design constraint. Re-measure after every
   type or content change.
9. **Commit.** One decision set, one commit. Update the tokens and the roadmap in
   the same commit.
10. **Implement from the tokens.** Generate `UiTokens.h` and `theme.h` from
    `tokens.json`. Do not translate pixels by eye. Add a snapshot test that
    renders every page and dialog. Keep the web and the plugin reading the same
    values.

## Design language that worked

The exact values are in `design/README.md` and `design/tokens.json`. These are
the transferable principles behind them.

- **Ground first.** Black is the room. A surface does not need an outline to
  exist. Depth comes from value, not from borders and shadows.
- **One meaning per colour.** Pink is identity and the primary value. Green is
  live signal and active state. Purple is selection and modulation. No other
  hues. A colour never means two things.
- **Controls are outlined, content surfaces are not.** If it cannot be clicked
  or typed into, it probably should not have a border.
- **Square, flat, no decoration.** No gradients, blur, or glow. The only shadow
  is a solid offset behind the wordmark. The style is a decision, not a default.
- **Type is part of the instrument.** Pixel-sharp, lowercase, two families with
  different jobs. The wordmark and user names keep their case. Every size is in
  the token file.
- **Every label earns its place.** No filler copy, no voice counts, no
  description of the product inside the product.
- **One home per token.** Colours, type sizes, spacing, and metrics sit in one
  file. The web CSS, the JUCE header, and the firmware theme are generated from
  it. A value typed twice will drift.
- **A fixed canvas, uniformly scaled.** The plugin canvas is 1240 by 985 logical
  pixels and scales as one image. The host cannot reflow it. The firmware screen
  is 240 by 240 and every page keeps the same frame. A fixed frame makes the
  layout comparable and the screenshots meaningful.
- **State has a language.** Unmuted, muted, active part, selected tab, selected
  row, focus, hover, and disabled each have one visual treatment. The user learns
  the language once.
- **Signal has a language.** Scope traces, spectra, envelopes, level fills, and
  routing colours say what the signal is doing. Decorative colour is banned.

What generalises: role-based colour, border discipline, a token file, a fixed
canvas, a state language, and copy rules. What does not: the exact hex values,
the two fonts, and the Type P.fm1 page count.

## Graphic design crib

These are the visual craft rules that apply to any panel or editor page.

- **Align to a grid.** A small set of shared edges makes a dense panel look
  deliberate. The eye catches a two-pixel misalignment before it reads a label.
- **Group by proximity.** Put more space around a group than inside it. If the
  spacing is ambiguous, the grouping is ambiguous.
- **Build one hierarchy per region.** Size, weight, contrast, and colour are the
  tools. A region gets one primary element, a few secondary ones, and the rest is
  tertiary. Do not make everything the same weight.
- **Let empty space work.** Do not fill a hole with a widget. The space is part of
  the composition and part of the instrument's calm.
- **Limit the palette.** A few hues with clear roles beat a rainbow. Use value
  and saturation for shades, not new hues. One accent is enough.
- **Use a type scale.** Two families and a small set of sizes. Keep the case
  consistent. Check the line length and the line height at the real size.
- **Contrast is value first.** A colour can be pretty and still fail. Check the
  actual foreground and background pair.
- **Repeat the same control.** The same kind of control gets the same shape,
  size, and behaviour everywhere. Consistency is a feature.
- **One focal point per page.** The player should know where to look first. In a
  synth, that is usually the sound or the algorithm, not the chrome.
- **Depth is optional.** Flat design can show depth with value and a solid
  offset. A shadow that does not describe a layer is decoration.
- **Motion is feedback.** Animate a change to explain it, not to entertain. A
  moving scope is data. A pulsing button is noise.
- **Follow the platform.** A plugin follows the host's scaling, focus, and
  automation. A firmware panel follows the device's silkscreen and control
  kinds. Familiarity is cheaper than novelty.

## Composition and visual weight

A page needs one composition centre, the element the eye lands on first. It is
not necessarily the geometric centre. It is the element with the most visual
weight, and it should be the thing the player needs first.

Weight comes from contrast, not decoration. Use one or two of these at a time:

- Colour: a complementary hue, or a much brighter or darker value.
- Scale: a clearly larger or smaller element.
- Shape or texture: a solid form among outlines, or the reverse.
- Brightness and saturation: a vivid element among muted ones.
- Direction and rotation: an element that breaks the flow.
- Position and negative space: an element set apart from the group.

Balance the page around that centre. Symmetry gives calm and order. Asymmetry
gives movement and tension. Rhythm comes from repeated spacing and repeated
shapes, not from repeated decoration. The player should feel where to look
before they read a label.

## Gestalt grouping

The eye groups before it reads. Use the principles deliberately:

- **Proximity:** related controls sit closer to each other than to unrelated
  ones. The space around a group must be larger than the space inside it.
- **Similarity:** the same kind of control looks the same. Similarity in colour
  is stronger than similarity in size, which is stronger than similarity in
  shape.
- **Figure and ground:** the control must separate cleanly from the surface. A
  stable figure-ground relationship is easier to read than an ambiguous one.
- **Closure:** the eye completes a shape. You can omit a border or a line if the
  form still reads, which reduces noise.
- **Common fate:** things that move or change together are seen as related. Use
  motion for feedback, not for decoration.
- **Uniform connectedness:** a line, frame, or shared region groups elements more
  strongly than proximity or similarity. Use it when the grouping must be
  unmistakable.
- **Good continuation:** align elements along a line or a curve. The eye follows
  the path of least resistance.
- **1 + 1 = 3:** the space between two elements becomes a third visual element.
  When elements are too close, the gap starts to read as a shape.

## Colour

Colour is a role system.

- Pick a small set of hues and give each one a job. A hue that means two things
  is a bug.
- Use value and saturation for shades. Do not add a new hue to make a variant.
- Warm colours advance and cool colours recede. Use the temperature deliberately.
- Contrast is a readability requirement. Check the actual text and background
  pair, not the swatch in isolation.
- Colour is cultural and subjective. A colour that reads as warning in one
  context may read as celebration in another. The label and the shape must carry
  the meaning too.
- Readability and accessibility beat prettiness. A beautiful palette that fails
  contrast is a failed palette.
- Do not rely on colour alone. Pair it with a label, an icon, a shape, or a
  position.

## Type

Typography is the interface's voice. It should disappear into the reading
experience, not compete with it.

- Use no more than two type families. One for body or controls, one for display
  or headings. A third family needs a job that the first two cannot do.
- Build a small type scale and stick to it. Size is relative. A one-pixel change
  at 12 pixels is visible, the same change at 72 pixels is not.
- Body text on screen is comfortable at about 14 to 16 pixels in a dense
  interface, and 15 to 25 pixels for long reading. A synth panel can go smaller
  for labels, but the value and the label still need space.
- Line length for prose is about 45 to 90 characters. In a panel, a label is
  short by design. A paragraph in a manual should not run the full width of a
  wide window.
- Line spacing is about 120 to 145 percent of the type size. A dense panel can
  use tighter leading for labels, but not for sentences.
- Left-align prose. Justified text on the web creates rivers without good
  hyphenation. Centred text is for short captions, not for paragraphs.
- Use all caps sparingly, and add letterspacing when you do. All caps is a
  rectangle of even shapes, which is hard to scan.
- Use real small caps, real curly quotes, and the proper dash. Do not fake them
  with scale or multiple hyphens.
- Use bold and italic as little as possible, and not together. One emphasis
  parameter at a time is enough.
- Use a professional typeface with a real fallback stack. A distinctive display
  face is fine for the wordmark. It is not fine for a parameter label.

## Grid

A grid gives the page a repeatable structure and saves decisions. It is an aid,
not a guarantee. It does not make the composition good on its own.

- Define the module, the columns, the rows, the gutters, and the margins. Use a
  small set of spacing values that are multiples of the base unit.
- Choose the grid that fits the content. A manuscript grid for prose, a column
  grid for lists and cards, a modular grid for a dense panel.
- A baseline grid aligns text across columns. It matters most when two columns
  sit side by side.
- Keep the same module and the same spacing across pages. Repetition is what
  makes the interface feel like one instrument.
- Break the grid deliberately, not accidentally. A single element can leave the
  grid to become the composition centre. Two elements leaving it in different
  directions is noise.

## Token architecture

A design system needs one source and two layers.

- **Primitive tokens** are raw values: `#ff2e7e`, `16`, `10`. They are not used
  directly by components.
- **Semantic tokens** are roles: `pink` is identity, `green` is signal, `text`
  is body text, `lineStrong` is a control border. Components use the semantic
  token, never the raw value.
- **Theme scopes** override semantic tokens, not component rules. A dark theme,
  a firmware palette, or a high-contrast mode swaps the semantic values in one
  place. It does not rewrite every button.
- **One projection per platform.** Generate the CSS variables, the JUCE header,
  and the firmware theme from the same source. A value typed twice will drift.
- **Avoid the specificity fight.** Do not stack theme classes and component
  classes and then patch the build order with `!important`. Separate the
  component's shape and type from the theme's colour. The theme supplies the
  colour, the component supplies the rest.
- **Name by role, not by appearance.** `text-muted` survives a palette change.
  `grey-500` does not.

## Inclusive design

The Inclusive Design Principles are a good review lens for an instrument:

- **Provide comparable experience.** A keyboard player, a screen reader user,
  and a touch user should be able to reach the same result with comparable
  effort.
- **Consider situation.** A dim stage, bright daylight, a small laptop screen,
  and a noisy room all change what works. Contrast and target size matter.
- **Be consistent.** Use familiar conventions, the same words, and the same
  layout across pages.
- **Give control.** Do not trap the user in a modal, an animation, or a zoom
  level. Let them stop, undo, and leave.
- **Offer choice.** Where a task has more than one natural route, allow it. A
  list and a grid, a knob and a typed value, a mouse and a keyboard.
- **Prioritise content.** Put the musical controls first. Progressively reveal
  the advanced settings.
- **Add value.** A feature should make the instrument easier to play rather than
  just longer to learn.

## Wayfinding

A player who arrives on a page should know where they are, what they can do,
and how to get back.

- **Orientation:** show the active part, operator, page, mode, and mute state.
- **Route decisions:** make the next action visible. Do not hide it behind a
  chord the player has to remember.
- **Mental map:** use the same page order and the same control positions across
  modes. A player should be able to predict where a control lives.
- **No self-description.** Do not spend the page explaining what the instrument
  is. The title, panel, and controls already say it. Use the words for the next
  action or a real limit.
- **No article drumbeats.** A list where every item starts with `The` reads like a
  specification. Lead with the noun or the verb, or write the list as prose.
- **No wh-word headings.** Use a noun or an imperative. `Navigation` and
  `Get started!` say what the section does. `How to move` asks a question the
  player did not ask.
- **No counted-couplet headings or table descriptions.** `One page, one job` and
  `Two sources, one filter` sell a shape instead of naming the section. Use a
  noun phrase and put the count in the body.
- **Closure:** confirm that an action happened. A save, a load, a mute, and a
  page change all need a visible result.
- **No dead ends:** every page has a way home and a way back.
- **Landmarks:** the header, the tabs, the active part, and the algorithm are
  landmarks. Keep them stable.

## Design as a practice

Frank Chimero's *The Shape of Design* is a reminder that design is not
decoration. It is imagining a future and working toward it for other people. A
panel is a gift to the player, not a display of the designer's taste. The
instrument should help them make the sound they hear in their head.

## Firmware UI

The physical panel and the 240 by 240 screen are one interface. The screen does
not get to be a settings form for an app.

The firmware mockup gate is `design/firmware-mockup.html`. It renders a project's
`panel.json` on the 240 by 240 screen with the 16 pixel row grid, the 120 pixel
column, the header, the page title, the widgets, and the legend. The dot grid and
guides are design overlays, not part of the screen. It loads the firmware's own
4-bit bitmap font from `design/firmware-font.json`, so the glyphs and advances
match the device. Use it before the panel code, inspect every page at 3x, and fix
the labels and rows in `panel.json` first. The mockup is a projection of the
spec. The web emulator is the parity check.

- **The silkscreen is law.** A printed label fixes a control's meaning. Do not
  reassign a labelled control. If the panel says `MASTER`, it is volume.
- **Know the control kind.** A smooth pot is not a detented encoder. A dedicated
  knob is not a page-slot knob. Treat them differently in the control map.
- **Prefer the page-slot model.** A small fixed set of encoders whose meaning
  changes per page, with the labels on screen, beats deep menus for a few knobs
  and a small screen.
- **Keys are a menu surface.** A keybed can select operators, mute parts, and
  open pages. Use it so a few controls reach every parameter.
- **No skeuomorphic knobs on a 240 by 240 screen.** Draw the value, the range,
  and the state. A fake knob wastes pixels and adds no affordance.
- **Popups own control.** A modal popup drains the page encoders, so a stray
  twist never changes the page behind it. It closes on its own after about three
  seconds for a non-destructive choice. A destructive save does not time out.
- **One knob, not more than two functions.** The Pērkons is the reference. If a
  knob needs a manual page, the page is doing too much.
- **Infer from the patch when you can.** Rings switches its exciter from internal
  to external when a cable is patched. The player does not press a button to say
  what the cable already says.
- **Visit the sweet spots.** A parameter should travel through the musical
  settings, not jump over them. Mutable Instruments calls the stronger version
  "convexity": if the instrument can reach A and B, it should reach the useful
  path between them, and not wander into a dead zone.
- **Recognition beats recall.** Show the current menu, page, part, operator, and
  mute state. Do not make the player remember a chord from the manual.
- **WYSIWYG beats a hidden mode.** The TR-808 is the reference. A state you can
  see on the panel is a state you can trust.
- **Do not let the screen steal the listening.** A bright, busy display pulls the
  player from listening to operating. Use motion and colour for feedback, not
  decoration. The Colavita effect is real.
- **Test with a stranger.** Do not explain the panel. Watch where they hesitate.
  The hesitation is the design bug.

The existing firmware checklist in `SKILL.md` §2 remains the gate. This section
is the reasoning behind it.

## Plugin UI

The plugin is an instrument panel inside a host window. The host owns the frame,
the scaling, the focus, and the automation. The plugin owns the layout and the
state language.

- **Fixed canvas, uniform scale.** Draw in logical units and scale the whole
  editor. Do not scale individual strokes or font sizes. At 50 percent the
  layout must still read as the same instrument.
- **HiDPI.** The canvas is logical pixels. The renderer may be 2x or 3x. Test at
  1x and at 2x.
- **Host automation.** Every control has a stable parameter id, a name, a range,
  a default, and a display string. The editor reads the same parameter tree as
  the host, not a private copy.
- **Snapshot every page and dialog.** The Type P.fm1 test renders the three pages,
  the algorithm picker, the rename dialog, active part 2, and the 50 percent
  scale. A UI change without a new snapshot is not verified.
- **Keyboard and focus.** Text entry, tab order, escape to cancel, and enter to
  commit. A plugin that traps the keyboard is hostile in a DAW.
- **Resizable, not reflowable.** The host may resize the window. The design does
  not reflow. If the window is too small, scale down or show a minimum size.
- **No modal traps.** A dialog that cannot be dismissed, or that steals a
  transport key, is a bug.
- **Accessibility.** Meet the contrast ratios, keep targets large enough to hit,
  and never use colour as the only signal. The Web Content Accessibility
  Guidelines apply to the web view and are a good floor for the plugin.

## Review

Before you call a UI done, run this:

- A 1x screenshot of every page and every dialog, current with the code.
- The snapshot diff gate is green, or the change was reviewed and accepted with
  `snapshot_check.py --update` in the same commit.
- A zoomed check of the dense areas, the labels, and the value fields.
- Every control clicked or typed once, including cancel and the destructive path.
- The fixed height measured across every page.
- A heuristic pass against Nielsen's ten, Rams's ten, and the laws of UX.
- A contrast check for every text and control colour.
- A check that colour is never the only carrier of meaning.
- A firmware check that every control maps to a manifest parameter, and every
  parameter is reachable.
- A plugin check that every control maps to a host parameter, and every host
  parameter is reachable.
- `umetate tokens` is clean: one token source, generated headers current, no raw
  colours or font families in the UI source.
- A fresh reader test: can they make a sound and find the save without help?

## Definition of done

- Control map is complete to the ten-item bar.
- Tokens are in sync and the generated headers are current.
- Mockup and implementation show the same layout, type, and state.
- Every interactive control has been exercised.
- Every page has a current snapshot, and the snapshot diff is green or the change
  was accepted deliberately.
- Roadmap has one line for the milestone.
- Design docs and skill references still describe what was built.
