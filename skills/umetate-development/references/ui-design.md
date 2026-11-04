# Designing an instrument interface

Read this before any panel, screen, editor, or web UI work. The Type P.fm1
language is in `design/README.md`. The casebook and research links are in
`ui-dossier.md`.

## The one rule

The interface is designed before it is written.

The Type P.fm1 firmware UI was underspecified on the first pass. Button meanings,
page contents, and per-parameter semantics were decided while the panel was being
coded. The result was buggy, incomplete, and cryptic, and the navigation map had
to be re-derived after the code existed. The fix was not more code. It was a
written control map, a written brief, and a mockup that was signed off before the
panel was authored. The full lesson is L8 and L10 in `docs/roadmap.md`.

The plugin editor followed the same rule. The design language was fixed first,
the mockup was made clickable, the tokens were extracted, and only then was the
JUCE editor built. The editor is a projection of the tokens, not a new design.

## What "determined" means

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

## The loop

This is the loop that produced the Type P.fm1 mockup and the JUCE editor.

1. **Orient.** Read the brief, the control map, the parameter manifest, the
   tokens, and the current mockup. The manifest is the source of truth. Do not
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
   fixed height. Check the state, not only the default page.
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

## The design language that worked

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
- **One home per token.** Colours, type sizes, spacing, and metrics live in one
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

## Firmware UI

The physical panel and the 240 by 240 screen are one interface. The screen does
not get to be a settings form for an app.

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

## The review

Before you call a UI done, run this:

- A 1x screenshot of every page and every dialog, current with the code.
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
- A fresh reader test: can they make a sound and find the save without help?

## Definition of done

- The control map is complete to the ten-item bar.
- The tokens are in sync and the generated headers are current.
- The mockup and the implementation show the same layout, type, and state.
- Every interactive control has been exercised.
- Every page has a current snapshot.
- The roadmap has one line for the milestone.
- The design docs and the skill references still describe what was built.
