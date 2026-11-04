# The umetate voice

The voice comes from the hand-written front doors in this repo. Read
`examples/type-p-fm1/publish-readme.md` first, then `README.md`. They are the
reference samples. When this file and a sample disagree, the sample wins.

The short version: a person who built the instrument is talking to a musician who
owns it. The person is enthusiastic, specific, and honest about limits. The
musician wants a sound, not a lecture.

## Three registers

Use the register that fits the page. Do not use the front-door register for a
procedure.

### 1. Front door

The README, the release notes, the preface of the manual, and any "why this
exists" page. This is the author talking.

- First person is normal: "I wanted", "I reckon", "I have not tested this yet".
- Digressions are allowed if they earn their place. A short story about the name
  or the design constraint helps the reader remember the instrument.
- Long sentences are fine when the clauses belong together. Follow one with a
  short sentence.
- British spelling: licence (noun), colour, behaviour, prioritise, organise,
  realise. Keep product names, API names, and file names as they are.
- Contractions are fine.
- Dry humour is fine. Marketing is not.
- End with a direct sign-off, not a call to action.

### 2. Manual

The user manual, the panel reference, the MIDI and SysEx reference, the
installation guide. This is the author explaining the instrument at the bench.

- Address the reader as "you". "Turn the knob" beats "the user turns the knob".
- Use first person in section intros and design asides: "I put the wavefolder
  before the filters because ...". Then return to direct instructions.
- Name every control exactly as the panel names it. If the panel says `SELECT`,
  the manual says `SELECT`, not "the page knob".
- For each parameter, answer three questions: what it does, what you hear when
  you turn it, and what the ends of the range sound like.
- Give a first patch. A reader should make a sound in the first minute.
- State limits and failure modes plainly. "Muting a modulator silences the
  carrier it drives" is better than "operator interaction may vary".
- Tables and step lists stay neutral. The voice lives in the prose around them.

### 3. Reference

The patch sheet, the CC table, the SysEx byte layout, the parameter index. Terse
and exact. No asides, no jokes, no first person. A reader is copying bytes.

## What the samples do

These are the habits to copy.

- Open with what the instrument is and what it is good at, in one or two
  sentences. The first sentence of the Type P.fm1 README says what it is, who
  made it, and why.
- Use a concrete comparison from the real world. The Type P.fm1 README compares
  the feedback trick to a reverse saw and the wavefolder to a string bow. That
  is more useful than "rich harmonic content".
- Say what the instrument is not. "Not an emulation", "no sequencer", "not a
  groovebox". This sets expectations and saves the reader time.
- Admit uncertainty once, plainly. "I can't offer any guarantee it'll work" is
  better than a page of hedges.
- Prefer a number to an adjective. "99 is full, 50 is about 12 decibels quieter"
  beats "a wide range of levels".
- Let the design reasoning show. "I prioritised those effects over delay and
  reverb because ..." tells the player how to use the instrument.
- Use the panel's vocabulary, then explain it once. Do not invent synonyms.

## What to avoid

These are the AI tells and the bad-manual habits.

- Em dashes. Rewrite the sentence.
- Semicolons. Full stop or comma.
- Filler: "in order to", "it is worth noting", "in the context of", "utilize",
  "delve", "seamless", "robust", "unleash", "state of the art".
- Openings that promise content: "In this section we will explore ...". Start
  with the content.
- Summaries that restate the heading.
- Rule-of-three padding. Two real items or four real items, not three abstract
  nouns.
- Hedging stacks. One genuine uncertainty is enough.
- "Whether you're a beginner or a seasoned producer". Pick the reader.
- The same personal anecdote on every page. One aside per page is plenty.
- Exclamation marks in procedures. Save them for the front door, if at all.
- Calling the framework "powerful". Describe what the instrument does.

## Research notes

These sources informed the rules above. Consult them for shape, never copy their
prose.

- Astrid Bin, *The Gliss Manual*: define the instrument's vocabulary from
  scratch, use a consistent layout per mode, offer more than one format, and
  treat the manual as a design review. If a feature is hard to explain, the
  feature may be wrong.
  <https://design.astridbin.com/project/gliss-manual>
- Mike Hiegemann, UDO Super 6 manual notes: a friendly, informal tone, beginner
  introductions before deep parameters, and paragraphs that show more than one
  musical use for a module.
  <https://mikehiegemann.com/portfolio/udo-audio-super-6-synthesizer/>
- dadamachines UX guidelines: flat hierarchy, consistent navigation, musical
  ranges rather than technical ones, and watch a stranger use the instrument.
  <https://dadamachines.github.io/ctag-tbd/uxguidelines.html>
- Elektronauts, "Best and worst manuals": reference manuals are not tutorials.
  Put appendices where they belong, say a thing once, and make it findable.
  <https://www.elektronauts.com/t/best-and-worst-manuals/219621>
- VI-Control, manual-writing lessons: exact screen names, a screen map before
  the detail, a hello-world example, a troubleshooting section, and a list of
  every way to get silence.
  <https://vi-control.net/community/threads/what-do.70018/page-2>
- A' Design, instruction manuals for synthesizers: a glossary, an index, and
  appendices with FAQs and tips.
  <https://competition.adesignaward.com/design-encyclopedia.php?e=298925>

## The final pass

- [ ] The page uses the register it should. A reference table has no jokes.
- [ ] The reader can make a sound or find a control without reading the code.
- [ ] Every control and parameter is named exactly as the panel names it.
- [ ] One concrete example, number, or comparison per major section.
- [ ] One plain statement of a limit or an unknown.
- [ ] No em dash. No semicolon.
- [ ] No filler, no promotion, no rule-of-three padding.
- [ ] British spelling in prose. Product and API names untouched.
- [ ] Read it aloud. If a patient teacher would stumble, rewrite it.
