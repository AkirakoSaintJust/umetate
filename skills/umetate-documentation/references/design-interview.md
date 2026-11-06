# Design interview

## Purpose

The manual preface and any design note come from the author, not the model. The
interview is how the personal experience, the design motivation, and the lineage
get out. A point-blank "what is your design philosophy?" produces a press release.
A specific question about the first patch produces a paragraph.

The form is generated from the project. `umetate interview --write` reads
`patch.json`, `panel.json`, `synth-brief.md`, and `plugin.json`, then renders the
generic core in `templates/design-interview.md` with the synth's own terms. It
does not assume FM, operators, or Type P.fm1. `--next 3` prints the next missing
items. `--check` lists every open question.

The generated form is a starting point. Read it, add or remove questions from the
brief, and ask one topic at a time. The template is the generic core. The
project's `design-interview.md` is the form you fill in.

## The role

You are a journalist who knows synth design. You are not a fan and not a
stenographer. You ask short questions, listen, and follow up. The author is the
expert on their own instrument. Your job is to get the concrete detail they would
not volunteer.

## The rules

1. Ask one topic at a time. Do not paste the whole form into the chat.
2. Start with a concrete memory, not an abstraction.
3. Follow up on every vague answer. "Which model?" "What did it sound like?" "What
   did you try first?" "What broke?" "Why that one?" "What did you keep?"
4. Ask for the tradeoff, not the feature. "What did it cost?" "What did you cut?"
   "What did you have to simplify?"
5. Ask for a specific patch, a specific bug, a specific comparison. A setting and
   a sound beat an adjective.
6. Do not accept "it sounds better" or "it is more flexible". Ask what it sounds
   like, at what setting, against what.
7. Let the author digress. Follow the energy, then return to the open question.
8. Record the answers in their words. Do not clean up yet. Mark uncertain facts.
9. Do not invent an answer. If the author does not remember, ask for the nearest
   concrete thing or leave the question open.
10. Ask permission before publishing personal details.

## Generator inputs

- `synth-brief.md` is the richest source. The generator reads the `- **Key:**`
  bullets: the working name, who plays it, what it should feel like, the reference
  sounds, the non-goals, the synthesis method, the oscillators or operators, the
  filters, the modulation, the output stage, the controls, and the polyphony.
- `patch.json` gives the name, the part count, the voice count, the parameter
  count, the voice and global node types, the tables, and the taps.
- `panel.json` gives the contexts, the pages, the home page, and the page titles.
- `plugin.json` gives the product name.

The generator adds questions from the voice and global node types and the panel
pages. If the brief calls the synth subtractive or wavetable, the questions use
the brief's words, not an FM template. If the brief is missing, the generic core
still works.

## The generic ladder

The generated form has nine sections. The order is a guide, not a script.

### First sound

- What was the first patch or sound that made you want to build the synth?
- What did the instruments you were using fail to do?
- What was the first version, and what did it get wrong?

Follow-ups: "What did it sound like?" "Which instrument were you using?" "What
did you try first?" "What made you keep going?"

### Lineage

- Which instruments, chips, or algorithms are in its DNA, and what did you take
  from each?
- Why this synthesis method rather than the obvious alternative?
- The brief's references and synthesis method, when the brief has them.

Follow-ups: "Which model?" "Which record or patch?" "What did the reference get
wrong?" "What did you reject?"

### Architecture

- Walk me through the voice architecture from the key to the output.
- Why this voice count and this part count?
- What did you try first, and why did it not survive?
- The generated questions from the voice node types.

Follow-ups: "What does each stage do?" "What did the voice budget allow?" "What
did the panel make easy or hard?"

### Output chain

- What is the output chain, and why does it end where it ends?
- What did you cut from the output stage, and why?
- The generated questions from the global node types.

Follow-ups: "What patch made the last stage worth it?" "What did you try before
it?" "What did you cut to make room?"

### Interface

- Why this panel and these controls?
- What did you cut from the UI, and what is still awkward?
- The generated questions from the panel contexts, the home page, and the brief's
  control surface.

Follow-ups: "What did you have to move off the home page?" "What did the screen
width rule out?" "What did you copy from hardware you like?"

### Tradeoffs

- What did you cut from the original design, and why?
- What broke during development, and what was the worst bug?
- What is still missing or unsatisfying, and what would you change tomorrow?
- The generated questions from the brief's non-goals and polyphony.

Follow-ups: "What did the first version do badly?" "What did you think was a good
idea and was not?" "What is the next thing if the hardware had more power?"

### Sound

- What is your favourite patch you made with it, and what does it do?
- What do you listen for when you tweak a patch?
- What is the first patch a new user should make?
- The generated questions from the brief's "what should it feel like" and "who
  plays it".

Follow-ups: "What settings?" "What does it do at the high end?" "What is the
recipe?" "What do you reach for first?"

### Person and name

- What does your workflow look like when you use it?
- Where does the name come from?
- What should a player understand before they touch it?

Follow-ups: "What do you sequence with?" "What is the live context?" "What is
the name about?" "What do you want them to hear first?"

### Interview itself

- What did I not ask that I should have?

## Synthesis-family branches

Use these when the generated form is thin, or when the brief names a family the
generator did not turn into a question. Ask only the branch the synth actually
uses.

**FM and phase modulation.** Why PM rather than FM? How many operators, and why?
Why these ratios, waveforms, and algorithms? What does feedback make possible?
Which waveforms are band-limited, and how? What did you take from the Yamaha
chips or the emulators?

**Subtractive.** Which oscillators, and why those shapes? What filter slope and
resonance? Does it self-oscillate? What does the drive do? Which envelopes and
LFOs, and why those destinations? What did you do about aliasing?

**Wavetable.** Where do the tables come from, and what is the size? How does the
morph work? What interpolation, and what does it cost? What did you do about
aliasing? Why tables rather than a waveform list?

**Additive.** How many partials? How are they controlled on this panel? What is
the phase relationship, and does it matter? How do you keep the edit manageable?

**Sample and granular.** What is the source, and how long is it? How do grains,
pitch, and time interact? What window and density? What does the memory budget
allow? What does the panel expose, and what is fixed?

**Physical modelling.** What is the exciter, and what is the resonator? What
material or geometry are you modelling? How does damping work? What did you have
to simplify to fit the voice budget?

**Noise and drums.** What are the noise sources? How do you shape the transient?
What filters and pitch envelopes? What makes the kit coherent?

**Hybrid.** Which parts use which family, and why? What does the split buy you?
What is shared, and what is per-part?

## Lineage and DSP specifics

The author may know more about the lineage and the algorithms than the manual
shows. Ask for it directly, but always through a concrete comparison.

- Which instruments, chips, or algorithms, and what did each contribute?
- Which synthesis method, and why this one rather than the obvious alternative?
- What did the references implement, and what did you do differently?
- Oscillator, operator, or source model: why this one?
- Filter or effect model: why this one, and what slope or topology?
- Modulation: why these sources and destinations?
- Voice budget and hardware: what did the compile or the panel force?
- Aliasing and quality tradeoff: what did you measure, and what did you accept?

## Recording

- Write the answers into `design-interview.md` under the question. Keep the
  author's words. Do not paraphrase into polished prose yet.
- Mark anything you could not verify with a note, not a guess.
- The notes are private by default. `umetate publish` does not copy them. Do not
  move them into `docs/`.
- If the author gives you a sentence you want to keep, keep it verbatim and mark
  it as a quote.

## Writing the design note

The design note is not the transcript. It is the author's voice, edited.

- Open with the first sound or the constraint, not the feature list.
- Use the lineage to explain a choice, not to show off. "I took the feedback order
  from the Yamaha chips" is better than a history of FM. Replace the model with
  the author's actual reference, whatever family it is.
- Keep three to seven concrete decisions, each with the tradeoff. The hand
  rewrite's seven-item list is the shape.
- Include one failure, one limit, and one patch recipe.
- Keep the author's asides. Cut the interviewer's questions.
- Use the manual calibration in `voice.md`. Do not flatten the note into a spec
  sheet.
- Do not invent a fact. If the interview did not answer it, leave it out.

## Stopping point

Stop when the answers can support:

- one origin story,
- one lineage comparison,
- three design decisions with tradeoffs,
- one failure or limit,
- one patch recipe,
- one sentence about who the synth is for.

That is enough for a manual preface. The interview can be longer than the public
note. The public note is the edit.

## Worked example: Type P.fm1

This is what a generated form looks like for one project, and how the answers
became prose. It is an example, not the template.

The generator read the Type P.fm1 brief and patch. It produced questions like:

- "What did the instruments you were using fail to do?" The answer became "I'm a
  hardcore fan of phase modulation synths, so for the longest time I've kept
  thinking about things I wanted to change on the Yamahas ... That's where Type
  P.fm1 comes from."
- "The brief describes the synthesis method as 4-operator phase-modulation FM,
  per-operator self-feedback, 12 waveforms per operator ... Why this method?"
  The answer became "It's not an emulation of any one Yamaha chip in particular
  ... but it **is** a DX-style synth, and it **does** take cues from ... ymfm and
  Dexed."
- "The voice zone uses fm_op x4, delay1 x4, algo, route ... Why this chain?" The
  answer became "It's two 4-operator parts because that's where I believe the
  sweet spot lies. There's this massive jump in complexity between editing a DX21
  from the panel vs editing a DX7 ..."
- "The panel has these contexts: home, edit, env, lfo, fx, glo. The home page shows
  ALGORITHM, A-ENVS, SCOPES ... Why these?" The answer became the workflow
  paragraph: "I'm more of a sound design gal, I fully sequence my music and I
  prefer trackers to little boxes ..."

The concrete names, models, and numbers stay. The interviewer's questions do not.
The author's asides stay. The order is the order of the argument, not the order of
the form.
