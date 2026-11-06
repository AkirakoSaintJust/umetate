# Interface work for the agent

The process that produced the Type P.fm1 interface. Use it for any future web or
JUCE interface work in this repository. The design language is in `README.md`.

The general method, the firmware and plugin mapping, and the design reference
dossier sit in the development skill:
`skills/umetate-development/references/ui-design.md` and
`ui-dossier.md`. The ten-item written gate is in
`skills/umetate-development/SKILL.md` section 2.

## Use cases

Use this workflow when the task is visual or interaction design: a new page, a
component, a restyle, a font change, a layout change, or a plugin editor.

Start with a clickable mockup and make it right in a browser first. Do not start
with production code. The interface is designed before it is written.

## Design loop

1. **Orient.** Read the design tokens, the mockup, and the parameter manifest for
   the project. `examples/type-p-fm1/patch.json` is the only reference for
   controls and ranges.
2. **Decide one set.** Take the smallest coherent set of changes. Do not batch
   unrelated restyles.
3. **Back up.** Before an experiment, copy the mockup and commit it. The user may
   ask for the backup to be removed later.
4. **Change.** Edit the mockup, not a generated bundle.
5. **Render.** Open the page at a fixed viewport, at 1x, and take a screenshot.
6. **Inspect.** Look at the full page and zoom into dense areas. Check labels,
   collisions, clipping, scrollbars and alignment.
7. **Verify interaction.** Open the dialogs, change a value, mute a part, switch a
   tab. Static screenshots do not prove a control works.
8. **Check the height.** All pages must keep one fixed window height. Re-measure
   after any type or content change.
9. **Commit.** One decision set, one commit. Update the tokens and the roadmap
   when the design changes.

## Lesson record

These are the mistakes that cost time while building the mockup.

- **A screenshot can lie about timing.** Read the file only after the browser has
  exited or the capture is complete. A missing screenshot is often a race, not a
  rendering bug.
- **Check the page and the state.** Many captures share a filename. Confirm the
  fragment, the selected tab, and the open dialog before judging a change.
- **A class-based rule only works if the class exists.** The operator knobs stayed
  cramped because the section kind class was never applied to the card. When a
  specific rule does not take effect, inspect the DOM before changing the rule.
- **Font loading can block the page.** A stylesheet in the head can hold the
  inline script until the network answers. Preload it and append the stylesheet
  after the first paint, with local fallbacks.
- **A fixed height drifts with type changes.** Measure the operator page after
  every font change and update the body minimum height and the grid minimum
  heights together.
- **Tag labels need real spacing.** Enlarging type without widening the knob cell
  makes `ratio` and `detune` touch. Check the rendered label edges as well as the
  dial centers.
- **Hidden scrollbars can hide a layout bug.** The screenshot flag can hide the
  scrollbar. Verify scrollers in a normal browser profile.
- **Japanese and kanji need the right font.** DotGothic16 covers the brand line
  and the 猫 glyph. Do not assume a Latin-only display font covers them.
- **Do not add filler to fill space.** Fix the layout, or leave the space. The
  user does not need a description of the product inside the product.

## Design review checklist

- Does every page show black, pink, purple and green in a meaningful role?
- Are the fonts the intended families, at the intended sizes, in lowercase?
- Do the labels and values have clear space at 1x?
- Is there exactly one fixed window height across pages?
- Are all surfaces borderless except controls, selection and the frame?
- Does the active tab use the cut polygon?
- Is the mute state legible, with the correct word lit?
- Do scrollers work and show a scrollbar in a normal browser?
- Do note fields show both the MIDI number and the note name?
- Does the legal state match the firmware manifest, with no invented controls?
- Are the OFL fonts bundled or loaded non-blocking, is the wordmark all Zen Dots,
  and is the brand font out of the binary?
- Does the page read as an instrument, not as a settings form for an app?

## Definition of done

- Mockup and tokens are committed and in sync.
- Every interactive control has been clicked in a browser.
- Screenshots of every page and dialog are current.
- Fixed height is measured, not assumed.
- Roadmap has one line for the milestone.
- JUCE and web mapping documents still describe the mockup.

## Handoff to implementation

When the mockup is signed off, extract tokens and build the shared component
recipes. Do not translate pixels by eye in C++. Generate `UiTokens.h` from
`tokens.json`. Keep the web and JUCE sides reading the same values.

The first implementation milestone is a reusable host plus a generated
`type-p-fm1` project, not a one-off plugin. The parameter manifest drives the
controls, the plugin state and the host automation.
