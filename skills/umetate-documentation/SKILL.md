---
name: umetate-documentation
description: Write thorough, readable, human documentation for end users of a synthesizer built on umetate. Covers the user manual, panel reference, MIDI and SysEx reference, patch sheet, installation guide, release notes, and technical guides or instrument studies. Includes a journalist-style design interview for the manual preface and design note. Rewrites are measured against the author's own corpus, hand-rewritten manual, and hand-rewritten guide so they read like a person wrote them. Never uses em dashes or semi-colons, never loses information, and bans negative parallelism, heading chains, false dichotomies, and marketing hooks. Preserves the author's contractions, asides, light UK slang, explanatory long sentences, joined clauses, and self-description.
version: 1.4.3
license: GPL-3.0-only
compatibility: OpenCode and Agent Skills-compatible loaders
allowed-tools: read, grep, glob, edit, write, shell, websearch, webfetch
---

# umetate documentation

Write the papers a musician actually reads: the manual, the panel walkthrough, the
MIDI sheet, the patch sheet, the install guide, and the release notes. The reader
is a person with the synthesizer in front of them, not a developer. Your job is to
help them get a sound and understand why.

## The six rules

These are the whole skill. Read them before writing a word.

1. **Synchronic, not historical.** Describe the instrument as it is right now.
   Do not narrate how it got here. Release notes are the one exception, they are a
   version history by nature. Every other page says "here is how it works", never
   "we changed X to Y". A guide or study of an existing instrument is the other
   exception. There, the history and lineage are the subject.
2. **From the instrument, not the code.** The reader sees a knob and hears a sound.
   Describe what the knob does and what the sound does. Do not mention nodes, macros,
   buffers, or the generator. If the code has a "phasor" and a "tl" stage, the
   manual says "pitch" and "level".
3. **The author's voice, not the model's.** When two wordings are both correct,
   pick the one the author would write. The reference samples are
   `examples/type-p-fm1/publish-readme.md` and the root `README.md`. The full
   profile is in `references/voice.md`. See the writing craft below.
4. **No information loss and no invention.** Humanising is allowed to cut, sharpen,
   and reorder, but not to drop a fact. It is also not allowed to invent a fact. The
   author can add their own knowledge; the model cannot. Compare every edited
   paragraph to the original and put back anything that went missing.
5. **No em dashes, no semi-colons.** Full stop. Rewrite around them.
6. **Radical rewrites are fine.** The goal is prose quality, not minimal diffs. A
   clean page that sounds like a spec sheet is not a success.

The hand rewrite is the calibration for rule 3. It doubled the first-person count and
the contractions. A rewrite that removes the author's slang, asides, and contractions
has gone too far, even if the prose is cleaner.

## The voice

Read `references/voice.md` before the first paragraph. It defines four
registers:

- **Front door:** the README, release notes, and manual preface. The author is
  present, in first person, with a specific story, a concrete comparison, and a
  plain statement of what the instrument is not.
- **Manual:** the manual, panel reference, MIDI reference, and install guide.
  Warm technical prose. Address the reader as "you", use first person in section
  intros and design asides, and keep procedures neutral.
- **Guide or study:** a document about an existing instrument, a lineage, or a
  design question. The reader may not own the hardware. History is allowed. It
  opens with the plain category, uses definitions and causal links, and can carry
  longer explanatory sentences than a manual.
- **Reference:** the patch sheet and byte-level tables. Terse and exact.

Then read `references/voice-samples.md`. It is a short set of excerpts from the
author's own reviews, forum posts, and notes, with a note on what each one teaches.
The first sections are the guide rewrite and the hand rewrite of the Type P.fm1
manual. The full corpus is 9,015 words. `voice.md` is measured against it: median
sentence 16 words, 90th percentile 39, zero em dashes, one semicolon, "I" 151
times, "we" 10 times. The corpus is the calibration for the front door. The manual
is the same voice with the procedure in front.

The hand rewrite is the manual calibration: 1,899 words, mean sentence 15.6, median
13, standard deviation 12.1, 22 first-person pronouns, 33 contractions, 7 brackets,
4 exclamation marks. The first release was 971 words, mean 11.3, median 10, standard
deviation 6.4, 2 first-person pronouns, 1 contraction. The rewrite is the target.

The guide rewrite is the guide calibration. Its first 70 lines moved from 689
words in 58 sentences (mean 11.6, median 9.5, standard deviation 8.5, longest 52)
to 737 words in 41 sentences (mean 17.6, median 14, standard deviation 16.7,
longest 80). The first-person count stayed at three. The change is explanatory
sentence length and connective looseness, not self-reference. Do not add "I" to
compensate for a flat draft. The first 170 lines of the full draft sit at 2,110
words in 148 sentences (mean 13.7, median 12, standard deviation 10.9), so a
connected opening can still sit above a flatter rest. Join the clauses when you
revise.

The samples use British spelling in prose, except "synthesizer", contractions, dry
humour, and light UK slang. The hand rewrite uses "innit", "kinda", "gal", and
"whatever" in the preface and tips. The samples do not use em dashes, semicolons,
marketing adjectives, or three-item padding. Copy the habits, not the catchphrases.
One or two personal asides in the preface, one per section in the body. Never in a
step.


## The design interview

The manual preface and any design note come from the author. A point-blank "what is
your design philosophy?" produces nothing. Run the interview before you write the
preface.

`umetate interview --synth <dir> --write` generates the form from the project's
`patch.json`, `panel.json`, `synth-brief.md`, and `plugin.json`, and writes it to
`<dir>/design-interview.md`. The questions use the synth's own architecture and
the brief's words. It does not assume FM or Type P.fm1. Read the generated form,
add or remove questions from the brief, then conduct the interview one topic at a
time. If the brief is missing, the generic core still works. `--next 3` prints the
next gaps. `--check` lists every gap. The full protocol is in
`references/design-interview.md`, and the generic core is
`templates/design-interview.md`.

Ask for:

- the first patch or sound that made the synth happen,
- the synths or chips it came from, and what was rejected,
- the design decisions and what each one cost,
- a failure, a limit, and a patch recipe,
- what the author wants a player to understand.

Follow up on every vague answer. "Which model?" "What did it sound like?" "What
broke?" "What did you keep?" A setting and a sound beat an adjective.

The raw notes are private. Do not copy them into `docs/` or the release. Write the
public design note from them, in the author's voice, with the manual calibration.
Cut the questions, keep the concrete details and the author's asides. Do not invent
an answer.

## The document set

A synthesizer project ships these user-facing documents. Each one has a job.

| Document | Job |
| --- | --- |
| README | The front door. What it is, one sentence. The web app link. How to install. |
| User manual | Architecture and sound design, from the player's chair. |
| Guide or instrument study | A historical or technical guide to an existing instrument or lineage. The reader may not own the hardware. |
| Panel reference | Every control, menu, key combination, and how to save. |
| MIDI and SysEx reference | The CC map, the note routing, the SysEx message format. |
| Patch sheet | A blank form a user can print and write a patch on. |
| Installation | How to flash the firmware and how to run the web app. |
| Release notes | What changed in each version, for the person updating. |

The manual and the panel reference are the two most read. Spend the most care there.

## The user manual

Open with the sound, not the spec. Tell the player what kind of instrument this is
and what it is good at. Then walk the signal, from the keys to the output, in the
order a player thinks about it.

A guide or study may be for readers who do not own the instrument. State the
audience. The K5/K5000 guide says "for players and sound designers". The guide
register is in `references/voice.md`.

The manual can open with a design note, not a spec sheet. The design note is in the
front-door register: the history, the constraint, the things the author wanted to
change, and a short numbered list. The hand rewrite has seven. Then hand over to the
manual register. The preface can run to several paragraphs and 150-word paragraphs.
The parameter sections stay 40 to 120 words. The design note comes from the
interview, not from the model. Use the answers in `design-interview.md`.

Fetch real manuals as style and content references before you write. Good anchors:
the Yamaha DX7 owner's manual and the Reface DX, the Korg opsix and Volca FM, the
Roland System-8 or JU-06, the Sonicware Liven series, and the Mutable Instruments
Plaits and Braids manuals. Read how they describe a parameter: one short sentence
for what it is, one for what you hear when you turn it. Copy that shape, never
their prose or their brand voice. Consult, do not derive.

For every parameter, answer three questions in plain words:

1. What it does.
2. What you hear when you change it.
3. What the ends of the range sound like.

Write the explanatory prose with contractions. The hand rewrite has 33 in 1,899
words. The first release had 1, and it read like a contract. Use "you" for the
player, "I" for the author's choices, and "it" for the instrument. One or two "I"
per section is fine. The preface can carry more.

Example of the shape, from an FM level parameter: "Operator level. This sets how
loud operator 1 is inside the voice. At 99 it rings clearly, at 50 it is about 12
decibels quieter, at 0 it is silent." Three sentences, concrete, no theory.

Name the operators and the parts the way the panel names them. If the panel says
OP1 through OP4, the manual says OP1 through OP4. Do not invent new names.

A tip is allowed when it gives a setting and a sound: "a sine operator taking no
modulation will kinda become a reverse sawtooth at about 25%-35%." Label it "Tip:"
if the section is dense. Three concrete tips are content, not padding. End the
manual with a patch recipe or an instruction, not an aphorism.

The hand rewrite keeps "innit", "kinda", "gal", and "whatever". Keep them in the
preface and one-line tips. Never in a procedure, a warning, or a reference table.
Keep the author's self-description ("I'm more of a sound design gal"). Do not change
"gal" to "guy" or "person".

## The panel reference

A fresh reader must be able to find any function without guessing. For each control
give its kind (knob, button, key, encoder), what it does on each page, and how to
reach every page. State the save flow exactly: which buttons, in what order, what
the screen confirms. Note the key combinations as combos, not as code.

Popups are worth a sentence: they own the controls while open, they close on their
own after about three seconds of no input, and a cancel does not lose work.

## The MIDI and SysEx reference

State the receive channels, the CC to parameter map, sustain, panic, pitch bend,
and program change. Then the SysEx format: the header, the command byte, the data
layout, and the exact bytes of each of the five commands the firmware answers. A
user who wants to back up patches with a SysEx librarian must be able to do it from
this page alone. Use tables for the maps, keep the prose around them short.

## The patch sheet

Fetch a few real patch sheets for comparable instruments (DX7, Volca FM, opsix) to
see how they lay out one patch per page. Then build a blank template for this
project with a row for every parameter, in the same order the panel walks them.
Leave room for a name, the algorithm, and a comment. Make it printable.

## Installation

Two paths, both explained for a non-programmer: flashing the firmware, and opening
the web app. For flashing, give the exact command and the exact recovery step if
something goes wrong. For the web app, give the URL and the one thing to click. Do
not assume the reader knows what a terminal is.

## Release notes

One section per version, newest first, with the version number and a date. Write
for the person updating: what changed, what they will notice, and whether a saved
patch still loads. Keep each entry to a few lines. This is the one place a
"changed from X to Y" sentence is correct, because it is a changelog by definition.

## Publishing

`umetate publish` copies the project's `docs/*.md` into the release and renames
`docs/release-notes.md` to `CHANGELOG.md`. The generated README is a fallback. If
the project has a hand-written `publish-readme.md`, publish copies it verbatim and
never overwrites it. Write that file by hand in the front-door register. The
generated template is there for a project that does not have one yet.

The four docs the generated README links to are `docs/manual.md`, `docs/panel.md`,
`docs/midi-and-sysex.md`, and `docs/patch-sheet.md`. Keep those names. If the
project has more docs, link them from the README and the manual index.

## The writing craft

This is the humanisation part, the anti-slop part. Apply it to every page. It is a
distillation of the author's corpus and the usual AI-tell catalogue, aimed at
technical prose, plus what good hardware manuals already do.

**Do not flatten the voice.** The biggest failure mode is a manual that reads like a
spec sheet. The first release did. The hand rewrite has 22 first-person pronouns and
33 contractions. If your draft has 2 and 1, you have over-edited. The guide rewrite
kept the same three first-person tokens as the draft and changed the sentence
structure instead. Do not add "I" to compensate for a flat draft. Add explanatory
clauses, connectives, and a longer sentence where the thought needs it. Attach a
fact with a relative clause, a specification with "with" and a colon, a condition
with "only when", and a cause with "so" or "because".

**Address the reader as "you".** "Turn the knob" beats "the user turns the knob".
Put the player in the room.

**Active voice, named actors.** "Hold SHIFT and press SAVE" beats "the save
function is triggered by pressing the button". The instrument is the actor where
there is no person, and that is fine, the instrument is the thing the reader owns.

**Concrete over abstract.** "The low end thins out" beats "the timbre becomes
brighter". Give a number where there is a number. A sentence that could describe
any synthesizer describes none.

**One main point per sentence.** When a sentence has three unrelated clauses, it is
two sentences. When the clauses belong to one thought, a longer sentence is fine.
Let a short sentence land next to a long one. Vary the length on purpose. The hand
rewrite has a 66-word sentence. The guide rewrite has an 80-word sentence and a
16.7-word standard deviation. A long sentence is fine when the clauses belong
together. Split it when the reader has to backtrack.

**Plain words over jargon.** The exact term stays where the panel uses it. Do not
invent synonyms for "operator" or "algorithm". Everything else gets the plain word.
Keep the author's deliberate vagueness: "OPwhatever", "or whatever", "aka". Pair
"OPwhatever" with "DX" so a reader can infer the family. Do not replace it with a
precise model list the author did not write.

**Kill the filler.** Delete "in order to", "it is worth noting", "in the context
of", "utilize". Delete the summary sentence that restates the heading. Delete the
opening that promises what is coming. Start with the content. "In order to" is
usually "To", but the author sometimes uses it to set up a purpose clause. Suggest
the short form only when it does not flatten the rhythm.

**No hedging stacks.** Commit to what you know. One genuine uncertainty is fine,
two qualifiers are slop. This is an instrument manual, not a research paper. "Sort
of" and "probably" are calibrated hedges in the guide. "And so on" and "a bunch of"
are generalisers. Keep the ones that are doing work.

**No rule of three padding.** List the real items, two or four is fine. Three
abstract nouns in a row is a tell. A 7-item design list is content. Three concrete
tips are content. The ban is on three abstract nouns doing the work of one fact.

**No promotion.** "Seamless", "robust", "state of the art", "unleash" have no place
next to a knob. Say what it does, let the player decide if it is good.

**State it directly.** A fact is a fact, an analysis is an analysis, an assertion is
an assertion. Do not dress an assertion as a question, a fact as a maybe, or a
contrast as a revelation. "The filter is 12 dB per octave and does not self-oscillate"
is the whole sentence. It does not need a setup.

**No negative parallelism.** Humans rarely introduce a thing by saying what it is
not. The author removed most "It's a X, not a Y" and "It's not an X" setups from the
guide. Start with the positive, the cause, or the constraint. Use a comparative or
an attached qualification when the contrast is real. Keep factual limits ("you
can't add inharmonic partials") and scope contrasts ("purely explanatory rather
than factory schematics"). A negation earns its place only when it carries a causal
link, a factual comparison, a counterintuitive explanation, a real limit, or a
correction of a misconception. If it carries none of those, cut it. A conversational
correction can keep the negative: "that doesn't mean one is necessarily better than
the other, they've just got different personalities." The negation carries a
correction, so it earns its place. "It's not just a
synth, it's a way of thinking", "not X, it's Y", "less X than Y", "X isn't about Y,
it's about Z" are hooks. They invent a contrast so the sentence sounds deeper. Say
what the thing is. If the contrast is real, state both sides plainly.
`references/voice.md` has the full rule. A factual contrast is the exception, not
the default: "It's not an emulation of any one Yamaha chip in particular, but it
**is** a DX-style synth" names both sides and prevents a false expectation. "Each
source is a complete voice path, rather than just the oscillator" is the same kind
of attached qualification. The ban is on the theatrical "not just X, it's Y" hook.

**No heading chains.** Do not write "The Engine", "The Filter", "The Envelope:
Shaping Your Sound" for every section. Vary the grammar, use the reader's words, and
do not make a section for every noun. One "The X" heading is fine. A chain is a
generated outline.

**No false dichotomies.** Do not invent a strawman to make the instrument look
different. "Most synths make you menu-dive. This one doesn't" only works if you can
name the synths and the difference is real. If the instrument is a four-operator FM
synth, say that. It does not need an enemy.

**No marketing hooks.** No "Imagine", "What if", "Meet", "Say hello", "Unlock",
"Dive into", "Whether you're a beginner or a seasoned producer", "The result?",
"But here's the thing", "Let's break it down". Start with the content.

**Open with the plain category.** A guide can start with a fact and a reason to
care, not a balanced thesis. The K5/K5000 guide opens "The K5 and K5000 are two
additive synths from Kawai. Additive synths are rare, so they're an interesting
case study." The model draft's "The K5 is a spectral instrument you learn by doing.
The K5000 is a spectral instrument you compose with" was cut. Plain category first.

**State the audience and the scope.** "This guide is for players and sound
designers" and "it isn't a technical manual, so the diagrams are purely explanatory
rather than factory schematics." The reader may not own the hardware. Say so early.

**Do not drop the qualifier.** A casual phrase can replace a precise one, but it
must not lose the fact. "Harmonic 64 is missing for some quirky reason" is fine, but
it drops "documented". Keep the fact and the casual wrapper.

**Fix grammar, not voice.** "both parts's algorithms" becomes "both parts'
algorithms". A comma splice can stay if it reads as one thought. Do not replace
"kinda" with "somewhat", "gal" with "person", or "innit" with "right?" unless the
author asks. Do not turn "2x4-op" into "two-by-four-operator" in every mention.
"the even harmonics over from the odd ones" becomes "the even harmonics take over
from the odd ones". "more of an specialised tool" becomes "more of a specialised
tool".

**No invented facts.** A humanising pass may not add a model, a date, a number, or a
quote. The hand rewrite's DX21/DX7 comparison, Chowning, ymfm, Dexed, and Yamaha
chip order are the author's knowledge. The model does not get to add its own. The
guide rewrite's definition of a harmonic, its comparison to PM sidebands, and its
"probably" about the K5/K5000 are also the author's. Keep them.

**Read it back as speech.** If you cannot imagine a patient teacher saying the
sentence out loud, rewrite it.

## The no information loss check

After you write a page, go back paragraph by paragraph. For each original paragraph,
name its facts and compare them to what you wrote. If a fact did not survive, put it
back, in the new voice. This is not optional. A humanised page that dropped the
SysEx checksum is a broken page.

Checklist for the final pass:

- [ ] Every fact from the source is present or deliberately scoped out with a reason.
- [ ] No fact was invented. The model added no model, date, number, or quote.
- [ ] The page uses the right register from `references/voice.md`.
- [ ] No em dash anywhere. No semi-colon anywhere.
- [ ] Every parameter, control, and command is named exactly as the panel names it.
- [ ] The current state only for a manual. Release notes and guides or studies
      excepted, no "now uses", "was added", "previously".
- [ ] A reader who has never seen the code can follow it.
- [ ] The explanatory prose has contractions. The hand rewrite has 33 in 1,899
      words.
- [ ] The author's slang, asides, and self-description survive.
- [ ] The manual is not flatter than the corpus. The median is roughly 13 to 16
      words and the variance is visible.
- [ ] The preface has at least one concrete design decision, one lineage reference,
      one failure or limit, and one first-patch recipe from the interview.
- [ ] A guide or study uses the guide register. The opening is a plain category and
      a reason to care, not a polished thesis.
- [ ] The audience is stated. It does not assume the reader owns the hardware.
- [ ] The scope and the status of the diagrams are stated.
- [ ] The guide's long sentences, generalisers, and parenthetical asides survive.
- [ ] The clauses are joined where they belong together: a relative clause for a
      fact, "with" and a colon for a specification, "only when" for a condition,
      and "so" or "because" for a cause.
- [ ] No documented qualifier was lost to a casual phrase.
- [ ] No negative parallelism ("not just X, but Y", "not X, it's Y", "less X than Y").
- [ ] No needless "It's a X, not a Y" or "It's not an X" setup. The positive comes
      first.
- [ ] A conversational correction can keep the negative when it corrects an
      inference or names missing evidence.
- [ ] Factual limits and real scope contrasts stay.
- [ ] A concrete detail can end a paragraph without a summary verdict.
- [ ] No heading chain ("The X", "The Y", "The Z: ...").
- [ ] No false dichotomy and no invented contrast.
- [ ] No marketing hook.
- [ ] The closing is an instruction or a verdict, not an aphorism.
- [ ] The first sentence says the thing, not "In this section".

## Credits and licences

When you fetch a real manual or patch sheet, you consult it for shape and approach.
You do not copy its prose or its layout verbatim. If you adapt a specific diagram or
table closely, credit the maker and note the licence in the project's LICENSING file,
the same rule the development skill applies to code. A manual's ideas are generally
facts you restate, not text you reproduce.
