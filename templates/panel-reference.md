<!-- This is a section of the user manual, so insert it after the sound-design
chapters and before the first-patch chapter. -->

## The panel

<One paragraph: say what the panel is, what this section covers, and the one habit
that makes the instrument easy to use. Name the physical surface and the screen
size.>

### The surface

<Every physical control, in the order a player meets it, with its kind, its
default job, and any global behaviour. Include the keys, the volume control, the
dedicated encoders, the page encoders, the context buttons, and the transport
buttons.>

- **<control>** <function>.
- **<control>** <function>.

### Navigation

<Explain the navigation model before the page tables, because a fresh reader has
to reach every page without guessing.>

- Press a context button to open that context. Press the same button again to
  advance to its next page. The page encoder moves forward and back. Pages wrap.
- <HOME behaviour.>
- <The page-knob rule: the four page encoders edit the parameter rows from top to
  bottom, whilst the extra encoders do nothing on a page with fewer than four
  rows, and display pages have no assignments.>
- <The header and footer, with the fields that stay visible and the legend text.>
- <Popup behaviour: modal, idle auto-close, and the commit action.>

| Gesture | Action |
| --- | --- |
| <chord or tap> | <action> |

### <Context name>

<The context's job and its page count, then which pages are part-level and which
follow the selected part or operator.>

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| <page title> | <param> | <param> | <param> | <param> | <display widget and its contents> |

<Notes for pages with fewer than four parameters, duplicate page titles, or
unusual behaviour.>

### Parameter reference

<Write one table per context or per page. The page tables above say which page a
parameter belongs to, and this section defines it: its range or units, its
function, and the sound you hear when you turn it. Use the panel value and range,
and leave the raw storage value out. Do not list the label twice and call that a
description. The sound-design chapters can explain the main parameters in depth,
whilst this is the quick lookup for every page row.>

| Parameter | Range | Functionality |
| --- | --- | --- |
| <name> | <range or units> | <function and sound> |

### Saving and loading

<The exact save chooser, the single-part and multi-patch paths, the save modes,
the preset browser, the init flow, the copy flow, and the name editor. Give the
buttons and the knob assignments rather than a summary.>

### The screen and the LEDs

<Header fields, colour roles, footer legend, key LEDs, mute indicators, popup
behaviour.>

### Quick reference

| Context | Pages | Functionality |
| --- | --- | --- |
| <context> | <n> | <one line> |
