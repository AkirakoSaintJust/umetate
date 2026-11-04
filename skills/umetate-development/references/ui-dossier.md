# UI dossier: what to study and what to take

This is a curated casebook, not a mood board. For each reference, read the
instrument or the article, name the lesson, and decide whether it applies. Do not
copy a look. Copy a decision that made the instrument easier to play.

The method is in `ui-design.md`. The exact Type P.fm1 language is in
`design/README.md`.

## Hardware and firmware

### Direct panels: the state is the interface

**Roland TR-808.** Nearly every control is one function, and the panel state is
the machine state. The dadamachines analysis calls it near-perfect WYSIWYG. The
lesson is not "make a drum machine". It is that a visible state is a trustworthy
state, and a simple surface can be fast because there is nothing to remember.
The caution is that there is no undo. Modern instruments can keep the directness
and add a safety net.

**Erica Synths Pērkons HD-01.** The same analysis praises its "one knob, not more
than two functions" approach and its near-zero mental tax. This is the strongest
argument against feature packing. If a knob needs a paragraph, the paragraph is
the design smell. The caution is that patterns and kits need a deliberate save,
and an accidental loss is unrecoverable.

**Make Noise 0-Coast and Hologram Microcosm.** No screen, few controls, a clear
signal path or a clear set of modes. The panel is the manual. The lesson is that
a small instrument can be deep when every control has a stable meaning. The
caution is documentation. A hidden interaction needs a card, a manual, or a
cheat sheet.

### Page-based screens: one page, one job

**Elektron Digitakt II and Digitone.** A row of encoders under the screen, one
page per function, and consistent navigation. The screen labels the encoders, so
the same hardware control can do many jobs without ambiguity. The lesson is the
page-slot model, used consistently. The caution is the multi-key chord and the
deep menu. The dadamachines analysis rates Elektron high on capability and high
on recall.

**Elektron Octatrack.** The cautionary version of the same idea. It is powerful
and loved by experts, but the mental load and the menu choreography are high. A
new player needs a manual and a cheat sheet. The lesson is that depth has a
cost, and the cost is paid by the first month, not the first minute.

**Dirtywave M8 and Polyend Tracker.** A small screen, eight buttons, and a
tracker grid. The mental model is strong and consistent, so expert users move
fast. The lesson is that a dense, consistent model can beat a larger screen. The
caution is the learning curve and the reliance on memorised shortcuts. If you
choose this path, invest in the first-run experience.

**1010music Blackbox.** A compact touchscreen with encoders. The lesson is direct
manipulation on a small surface. The caution is that a touchscreen can dominate
the instrument, and the targets must be large enough for a thumb. The screen
should not become the only place where the state lives.

**Synthstrom Deluge.** A screenless groovebox with a huge feature set and many
encoder-button combinations. The lesson is that a strong workflow can carry a
small display. The caution is discoverability. When the state is only in the
player's head, a new user cannot see it.

### One-principle instruments: the strongest reference

**Mutable Instruments Rings and Tides, as described by Émilie Gillet.** This is
the most useful design interview in the dossier. Gillet's rules:

- The label printed on the panel must match the knob's function. This bans
  collections of unrelated functions with knobs labelled 1, 2, 3, 4.
- Infer settings from the patch where possible, instead of asking the player to
  press a button. Rings switches from an internal to an external exciter when a
  cable is patched.
- OLED and encoder interfaces are acceptable for "set once and set aside"
  settings, not for a performance instrument.
- Aim for "convexity": if the instrument can reach A and B, it should reach the
  useful path between them, and it should visit the sweet spots. Continuity alone
  is not enough. A pulse-width knob that crossfades between 1 percent and 99
  percent is continuous but never reaches the hollow 50 percent square.
- Uniform roles for knobs and jacks. A multi-function module is fine when every
  function comes from one underlying principle.

**Mutable Instruments Braids and Clouds, by Gillet's own account.** She calls
Braids a mistake and Clouds a mistake in this interview, not because they sound
bad, but because they became collections of features and hidden settings. This is
the best cautionary tale from a designer who shipped the popular version. A
feature that cannot be reached, named, and understood from the panel is a
liability.

### Big panels: keep the musical controls on the surface

**Moog One.** The design team's stated principles are familiar flow, flat
interface hierarchy, and synth panel focus. The "More" panel holds the advanced
parameters in a flat list, while the performance controls stay on the surface.
The lesson is progressive disclosure with a stable top layer. Do not hide the
performance controls to make room for the advanced ones.

**ASM Hydrasynth, Novation Peak, Arturia MicroFreak, Sequential Prophet-6.**
These sit between the one-knob-per-function panel and the page-based screen. The
common pattern is a grouped signal path, a small display, and a clear set of
performance controls. The lesson is to group by signal flow and put the controls
the player reaches for during a performance on the top layer.

**Korg opsix and Yamaha Reface DX.** Small screens with page-based editing, but a
visible algorithm or operator map. The lesson is to draw the structure. A player
who can see the routing learns the instrument faster than a player who reads a
parameter name.

### Cautionary panels

**Teenage Engineering OP-1.** A strong identity, a constrained surface, and a
colour-coded screen that maps to the physical controls. The lesson is that
constraint and identity can make an instrument memorable. The caution is
learnability. A distinctive interface still has to explain itself, and the
colour coding must be more than decoration.

**Any panel with hidden modes.** If the same knob does three things and the
screen does not say which one is live, the player will change an unseen value.
This is the most common firmware UI bug. Make the mode visible, or do not use
the mode.

## DAW plugins

### Direct manipulation: touch the thing you hear

**FabFilter Pro-Q.** The EQ curve is the control. Drag a band on the spectrum,
see the result, and stay on one screen. The lesson is direct manipulation of the
representation, not a form of numbers beside it. The consistent band colours and
the lack of modal dialogs keep the flow.

**iZotope Ozone.** Real-time visual feedback and an assisted workflow. The lesson
is to show the result of a change. The caution is that an assistant can hide the
model. A player who does not know what the assistant did cannot reproduce it.

### Minimal surfaces

**Valhalla DSP.** A few knobs, clear modes, and a musical default. The lesson is
that a small surface with good ranges beats a large surface with bad ranges. The
"instant result" is a design decision, not a preset trick.

**u-he Diva.** A one-page layout for a complex analogue-style synth, with clear
module grouping and resizable UI. The lesson is that a single page can hold a
complex instrument when the modules are visually grouped and the signal path is
stable.

**u-he Zebra.** A modular synth with a stable grid and a visible routing model.
The lesson is that modularity needs a persistent spatial model. If the modules
move, the player cannot build muscle memory.

### Visual modulation

**Xfer Serum.** Drag a modulation source onto a destination, with a real-time
waveform. The lesson is to show the source, the destination, and the result in
the same gesture.

**Vital.** Drag-and-drop modulation with a preview before the drop, colour-coded
sources, and a visible modulation depth. The lesson is to preview the connection
before the commit. The player should not have to undo to find out what a drop
does.

**Arturia Pigments.** Colour-coded modulation sources, visible connections, and a
play view. The lesson is one colour per source, used everywhere. The caution is
that colour alone cannot carry the meaning. Pair it with a label, a shape, or a
line.

### Host-native and cautionary

**Ableton Live and Bitwig Studio stock devices.** Flat, consistent, and
functional. The lesson is host consistency. A plugin that fights the host's
scaling, focus, or automation model feels broken even when it sounds good.

**Kilohearts Phase Plant and similar modular plugins.** Very powerful and very
dense. The lesson is that power needs progressive disclosure. A first screen full
of empty slots is not an invitation, it is a questionnaire.

**Skeuomorphic plugins with small text.** Texture and character are fine. A
wood-grain panel with 9 pixel labels is not. The lesson is that the metaphor
must survive the actual size and the actual display.

**Five common plugin UX failures.** A design studio's list is a useful
checklist: cluttered interfaces, no visual feedback, poor accessibility, intrusive
popups, and poor adaptation to different screen sizes. Every one of these is a
bug in an instrument.

## Theory

**Don Norman, The Design of Everyday Things.** Affordances are what an object can
do. Signifiers are what tells you it can do it. Mapping is the relation between a
control and its effect. Feedback tells you what happened. A conceptual model is
the story the user tells themselves about the system. Design for error, because
people will make slips and mistakes. In a synth, the knob is the affordance, the
label is the signifier, and the screen is the feedback. If the screen lags, the
model breaks.

**Jakob Nielsen, 10 usability heuristics.** Visibility of system status, match
with the real world, user control and freedom, consistency, error prevention,
recognition over recall, flexibility and efficiency, aesthetic and minimalist
design, error recovery, and help. The heuristics are a review method, not a
recipe. Use them to find problems, then test with a player.

**Dieter Rams, ten principles for good design.** Useful, understandable,
unobtrusive, honest, long-lasting, thorough, and as little design as possible.
"Less, but better" is the relevant one for a panel. The instrument should not
shout. It should be a tool for the player's expression.

**The laws of UX.** Fitts's law says large, close targets are faster. Hick's law
says more choices take longer. Miller's law says working memory is small. Jakob's
law says players expect your instrument to behave like the ones they already
know. The Gestalt principles of proximity, common region, and similarity explain
why grouping works. Use them to structure the panel, not to decorate it.

**WCAG contrast.** Normal text needs 4.5:1, large text needs 3:1, and graphical
objects and interface components need 3:1. These are floors, not targets. A dark
synth panel with dim grey labels often fails. Check the actual token pairs.

**Edward Tufte.** The data-ink ratio says most of the ink should carry data.
Chartjunk is decoration that competes with the data. Small multiples compare
many series on the same scale. A scope and a spectrogram are data displays. The
grid, the axes, and the glow should earn their pixels.

**Refactoring UI.** Visual hierarchy is not document hierarchy. Use fewer
borders. Start with too much space, then remove it. Build a spacing and type
scale. Avoid ambiguous spacing. Do not rely on colour alone. These are practical
tactics for making a dense panel readable without making it loud.

**Jef Raskin, The Humane Interface, via Designing Sound.** Minimise cognitive
load and physical effort. A small set of controls can become an instrument
through muscle memory. A large set of controls can become a form. The article
also makes the ergonomic case: repetitive click-and-drag is not free.

**A heuristic review of synth interfaces (2004).** The academic study compares
direct engagement with parameter access. It finds that neither style wins in
general. Graphic envelopes are easier than typing numbers, and a broad menu is
easier than a deep one. The lesson is to match the interaction to the task, not
to pick a camp.

**dadamachines UX guidelines and hardware patterns.** The guidelines give the
practical rules: map the navigation, limit cognitive load, keep the hierarchy
flat, use musical ranges, use consistent gestures, and watch a stranger use the
device. The patterns page applies Nielsen and NASA-TLX to real instruments and
names the visual dominance problem. A bright screen pulls attention away from
listening.

**Astrid Bin, The Gliss Manual.** Writing the manual exposed interface problems
before launch. The vocabulary was defined from scratch, the layout was consistent
per mode, and the manual shipped in more than one format. The lesson is that the
documentation is a design review. If you cannot explain a feature, fix the
feature.

## A reading order

1. Don Norman, for the vocabulary.
2. Jakob Nielsen, for the review method.
3. Dieter Rams, for restraint.
4. Refactoring UI, for the visual craft.
5. Émilie Gillet, for the instrument design principles.
6. dadamachines, for the hardware UX analysis.
7. The manual and the panel of every instrument you study.

## Links

- Don Norman, The Design of Everyday Things: <https://en.wikipedia.org/wiki/The_Design_of_Everyday_Things>
- Don Norman's site: <https://jnd.org/>
- Nielsen, 10 usability heuristics: <https://www.nngroup.com/articles/ten-usability-heuristics/>
- Rams, ten principles: <https://www.vitsoe.com/gb/about/good-design>
- Laws of UX: <https://lawsofux.com/>
- Fitts's law: <https://lawsofux.com/fittss-law/>
- Hick's law: <https://lawsofux.com/hicks-law/>
- Miller's law: <https://lawsofux.com/millers-law/>
- Jakob's law: <https://lawsofux.com/jakobs-law/>
- WCAG contrast minimum: <https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html>
- WCAG non-text contrast: <https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html>
- Tufte, chartjunk: <https://www.edwardtufte.com/notebook/chartjunk/>
- Refactoring UI: <https://refactoringui.com/>
- Designing Sound, humane interface design: <https://designingsound.org/2018/02/28/humane-interface-design-for-synthesis/>
- Synth UI heuristic review (2004): <https://oro.open.ac.uk/90139/1/2004_20.pdf>
- dadamachines UX guidelines: <https://dadamachines.github.io/ctag-tbd/uxguidelines.html>
- dadamachines hardware UX patterns: <https://dadamachines.github.io/ctag-tbd/ux-hardware-patterns.html>
- Émilie Gillet interview: <https://en.clockfacemodular.com/blogs/waveguide/interview-with-designers-emilie-gillet-mutable-instruments>
- Mutable Instruments retrospective: <https://www.perfectcircuit.com/signal/mutable-instruments-retrospective>
- Moog One UX principles: <https://www.slideshare.net/slideshow/intuitive-user-interface-design-for-modern-synthesizers/239022977>
- Astrid Bin, The Gliss Manual: <https://design.astridbin.com/project/gliss-manual>
- Voger Design, audio plugin UX: <https://vogerdesign.com/blog/make-audio-plugin-with-great-ux/>
- FabFilter Pro-Q: <https://www.fabfilter.com/products/pro-q-4-equalizer-plug-in>
- u-he: <https://u-he.com/>
- Valhalla DSP: <https://valhalladsp.com/>
- Xfer Serum: <https://xferrecords.com/products/serum>
- Vital: <https://vital.audio/>
- Arturia Pigments: <https://www.arturia.com/products/software-instruments/pigments/overview>
- iZotope Ozone: <https://www.izotope.com/en/products/ozone.html>
- Kilohearts Phase Plant: <https://kilohearts.com/products/phase_plant>
- Elektron: <https://www.elektron.se/>
- Dirtywave: <https://dirtywave.com/>
- Synthstrom: <https://synthstrom.com/>
- 1010music: <https://1010music.com/>
- Teenage Engineering: <https://teenage.engineering/>
- ASM Hydrasynth: <https://www.ashunsoundmachines.com/>
- Novation: <https://novationmusic.com/>
- Arturia: <https://www.arturia.com/>
- Sequential: <https://www.sequential.com/>
- Moog: <https://www.moogmusic.com/>
- Make Noise: <https://www.makenoisemusic.com/>
- Hologram Electronics: <https://www.hologramelectronics.com/>
