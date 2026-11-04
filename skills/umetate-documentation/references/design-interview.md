# Design interview

## What this is

The manual preface and any design note come from the author, not the model. The
interview is how the personal experience, the design motivation, and the lineage
get out. A point-blank "what is your design philosophy?" produces a press release.
A specific question about the first patch produces a paragraph.

The form is `templates/design-interview.md`. `umetate interview --write` copies it
into the project. `--next 3` prints the next gaps. `--check` lists every gap. The
questions are the source of truth. This file is the how-to.

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
7. Let the author digress. Follow the energy, then return to the gap.
8. Record the answers in their words. Do not clean up yet. Mark uncertain facts.
9. Do not invent an answer. If the author does not remember, ask for the nearest
   concrete thing or leave the gap.
10. Ask permission before publishing personal details.

## The question ladder

The form has nine sections. The order is a guide, not a script.

### The first sound

- What was the first patch or sound that made you want to build this synth?
- What did the synths you were using fail to do?
- What was the first version, and what did it get wrong?

Follow-ups: "What did it sound like?" "Which synth were you using?" "What did you
try first?" "What made you keep going?"

### The lineage

- Which Yamaha models or chips are in the DNA, and what did you take from each?
- What did you learn from ymfm and Dexed, and what did you deliberately not copy?
- Why phase modulation rather than frequency modulation, and what does that change
  in the DSP or the sound?

Follow-ups: "Which waveform?" "What did the OPL3 do that the DX7 did not?" "What
did you reject?" "What did the emulator get wrong?"

### The architecture

- Why two parts of four operators, not one part of six or eight?
- Why feedback on every operator?
- Why these eight algorithms, and what did you leave out?

Follow-ups: "What did the DX21/DX7 comparison teach you?" "What did the voice
budget allow?" "What did the panel make easy or hard?"

### The output chain

- Why two filters and a wavefolder, and why no delay, reverb, or chorus?
- What does the wavefolder do that the filters cannot, and where did the idea come
  from?

Follow-ups: "What patch made the wavefolder worth it?" "What did you try before
it?" "What did you cut to make room?"

### The interface

- Why the 240 by 240 panel and the M-VAVE surface, and what did the interface force
  you to simplify?
- Why the envelope graphs, copy and paste, and the page layout?
- What did you cut from the UI, and what is still awkward?

Follow-ups: "What did you have to move off the home page?" "What did the screen
width rule out?" "What did you copy from hardware you like?"

### The tradeoffs

- What did you cut from the original design, and why?
- What broke during development, and what was the worst bug?
- What is still missing or unsatisfying, and what would you change tomorrow?

Follow-ups: "What did the first version do badly?" "What did you think was a good
idea and was not?" "What is the next thing if the FM1 had more power?"

### The sound

- What is your favourite patch you made with it, and what does it do?
- What do you listen for when you tweak a patch?
- What is the first patch a new user should make?

Follow-ups: "What settings?" "What does it do at the high end?" "What is the
recipe?" "What do you reach for first?"

### The person and the name

- What does "sound design gal" mean for how you work?
- Where does the Type P.fm1 name come from, and what is the maritime and
  industrial theme about?
- What should a player understand before they touch it?

Follow-ups: "What do you sequence with?" "What is the live context?" "What is the
P1Onken name about?" "What do you want them to hear first?"

### The interview itself

- What did I not ask that I should have?

## Lineage and DSP specifics

The author may know more about the lineage and the algorithms than the manual
shows. Ask for it directly, but always through a concrete comparison.

- Which chips and models, and what did each contribute?
- What did ymfm and Dexed implement, and what did you do differently?
- PM vs FM: what changes in the operator, the feedback, the envelopes, or the
  aliasing?
- The operator order and feedback behaviour in the Yamaha chips: what did you
  keep?
- The OPL3 and TX81z/D11/V50 waveforms: which ones, and why?
- The band-limited pulse, square, and saw: what did you do about aliasing?
- The rate-level envelopes: what does that shape make easier on this panel?
- Key and velocity scaling: what did you simplify from the DX7?
- The voice budget and the dual-core split: what did the hardware force?
- The filters and wavefolder: what did you try before them?

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
  from the Yamaha chips" is better than a history of FM.
- Keep three to seven concrete decisions, each with the tradeoff. The hand
  rewrite's seven-item list is the shape.
- Include one failure, one limit, and one patch recipe.
- Keep the author's asides. Cut the interviewer's questions.
- Use the manual calibration in `voice.md`. Do not flatten the note into a spec
  sheet.
- Do not invent a fact. If the interview did not answer it, leave it out.

## When to stop

Stop when the answers can support:

- one origin story,
- one lineage comparison,
- three design decisions with tradeoffs,
- one failure or limit,
- one patch recipe,
- one sentence about who the synth is for.

That is enough for a manual preface. The interview can be longer than the public
note. The public note is the edit.

## Worked example

The hand rewrite's preface answers these prompts. The answers are edited into the
design note, not pasted as a Q&A.

- "What did the synths you were using fail to do?" becomes "I'm a hardcore fan of
  phase modulation synths, so for the longest time I've kept thinking about things
  I wanted to change on the Yamahas ... That's where Type P.fm1 comes from."
- "What is the lineage, and what did you reject?" becomes "It's not an emulation
  of any one Yamaha chip in particular ... but it **is** a DX-style synth, and it
  **does** take cues from ... ymfm and Dexed."
- "Why two parts of four operators?" becomes "It's two 4-operator parts because
  that's where I believe the sweet spot lies. There's this massive jump in
  complexity between editing a DX21 from the panel vs editing a DX7 ..."

The concrete names, models, and numbers stay. The interviewer's questions do not.
The author's asides stay. The order is the order of the argument, not the order of
the form.
