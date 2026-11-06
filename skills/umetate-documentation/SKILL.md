---
name: umetate-documentation
description: Write thorough, readable, human documentation for end users of a synthesizer built on umetate. Covers the user manual, including the panel walkthrough, the MIDI and SysEx reference, patch sheet, installation guide, release notes, and technical guides or instrument studies. Includes a journalist-style design interview for the manual preface and design note. Rewrites are measured against the author's own corpus, hand-rewritten manual, hand-rewritten guide, and hand-written README so they read like a person wrote them. Never uses em dashes or semi-colons, never loses information, and bans negative parallelism, heading chains, false dichotomies, marketing hooks, and the project vocabulary (claim, source of truth, I built, dogfood, lives in, gap). Preserves the author's contractions, asides, light UK slang, explanatory long sentences, joined clauses, self-description, chummy tone, and anti-slop promise. Includes a measured rhythm gate with mean, median, and standard deviation targets for the manual, guide, and reference registers.
version: 1.7.0
license: GPL-3.0-only
compatibility: OpenCode and Agent Skills-compatible loaders
allowed-tools: read, grep, glob, edit, write, shell, websearch, webfetch
---

# umetate documentation

Write the papers a musician actually reads: the manual, the panel walkthrough, the
MIDI sheet, the patch sheet, the install guide, and the release notes. The reader is
a person with the synthesizer in front of them, not a developer, so the job is to
help them get a sound and understand why it sounds that way. I'd keep that reader in
mind for every page, because the moment the prose turns into a spec sheet, they stop
reading and start guessing. Keep that reader.

## Six rules

These six rules are the whole skill, so read them before you write a word and come
back to them when a page feels flat.

1. **Synchronic, not historical.** Describe the instrument as it is right now.
   Release notes are the one exception, because they are a version history by
   nature. A guide or study of an existing instrument is the other, because there
   the history and lineage are the subject. Every other page says "here is how it
   works", never "we changed X to Y". That rule keeps a manual from reading like a
   changelog with a few knobs attached. Keep it current.
2. **From the instrument, not the code.** The reader sees a knob and hears a sound.
   Describe what the knob does and what the sound does. Leave the nodes, macros,
   buffers, and generator out of it. If the code has a "phasor" and a "tl" stage, the
   manual says "pitch" and "level", because that is what the player sees and hears.
   Name the knob.
3. **The author's voice, not the model's.** When two wordings are both correct,
   pick the one the author would write, and check it against
   `examples/type-p-fm1/publish-readme.md` and the root `README.md` when you are
   unsure. The full profile is in `references/voice.md`, and the writing craft below
   turns the profile into a working method. Check the samples.
4. **No information loss and no invention.** Humanising is allowed to cut, sharpen,
   and reorder, but not to drop a fact, and it is not allowed to invent one either.
   The author can add their own knowledge, whilst the model cannot. Compare every
   edited paragraph to the original and put back anything that went missing.
5. **No em dashes, no semi-colons.** Full stop. Rewrite around them.
6. **Radical rewrites are fine.** The goal is prose quality, not minimal diffs. A
   clean page that sounds like a spec sheet is not a success, even when every
   sentence is grammatically perfect. Start again.

The hand rewrite is the calibration for rule 3, and it doubled the first-person count
and the contractions. A rewrite that removes the author's slang, asides, and
contractions has gone too far, even when the prose is cleaner, because the voice is
part of the information.

## Project vocabulary

Six words are hard bans in prose, because each one carries a model's default framing
and hides the fact underneath. A bare `claim` for a feature becomes `claimed
feature`, or the feature's name. `Source of truth` becomes `only reference` or
`single reference`. `I built` becomes `I made`, unless the subject is a compiled
binary or a CI job. `Dogfood` becomes `test project made from our own readymade
components`, then `the test project` or `the worked example`. A file, folder,
sub-project, document, or component does not `live in` a place. It `is in the PATH
folder`, it `is stored at` a path, or its path within the repo is the path. A `gap`
for missing work becomes the missing work, the missing feature, the bug, the
oversight, or the problem. Use the plain phrase.

The full table, the exceptions for technical uses, and the before and after samples
are in `references/voice.md` and in the writing craft below. Use this section as the
short version and the reference as the place to settle an argument.

## Voice

Read `references/voice.md` before you write the first paragraph, because it defines
four registers and tells you which one a page needs:

- **Front door:** the README, release notes, and manual preface. The author is
  present, in first person, with a specific story, a concrete comparison, and a
  plain statement of what the instrument is.
- **Manual:** the manual, including the panel walkthrough, the MIDI reference, and
  the install guide, written in warm technical prose that addresses the reader as
  "you" and uses first person in section intros and design asides. Keep procedures
  neutral, because a step is not the place for a joke.
- **Guide or study:** a document about an existing instrument, a lineage, or a design
  question, where the reader may not own the hardware and history is allowed. It
  opens with the plain category, uses definitions and causal links, and can carry
  longer explanatory sentences than a manual.
- **Reference:** the patch sheet and byte-level tables, kept terse and exact,
  because the reader is copying bytes.

Pick one before you start.

Then read `references/voice-samples.md`, which is a short set of excerpts from the
author's own reviews, forum posts, and notes, with a note on what each one teaches.
The first sections are the guide rewrite and the hand rewrite of the Type P.fm1
manual, and the full corpus is 9,015 words. `voice.md` is measured against it: a
median sentence of 16 words, a 90th percentile of 39, zero em dashes, one semicolon,
"I" 151 times, and "we" 10 times. The corpus is the calibration for the front door,
whilst the manual is the same voice with the procedure in front.

The hand rewrite is the manual calibration: 1,899 words, a mean sentence of 15.6, a
median of 13, a standard deviation of 12.1, 22 first-person pronouns, 33
contractions, 7 brackets, and 4 exclamation marks. The first release was 971 words,
with a mean of 11.3, a median of 10, a standard deviation of 6.4, 2 first-person
pronouns, and 1 contraction. That's why it read like a contract. The rewrite is the target.
That's the bar.

The current Type P.fm1 manual appends the panel section, so the file is longer than
the 1,899-word hand rewrite, but the hand-written preface and sound-design part
remains the calibration for the prose. The panel section follows the same register,
because a panel page is still part of the manual.

The guide rewrite is the guide calibration. Its first 70 lines moved from 689 words
in 58 sentences (mean 11.6, median 9.5, standard deviation 8.5, longest 52) to 737
words in 41 sentences (mean 17.6, median 14, standard deviation 16.7, longest 80). The first-person count stayed at three, because the change was explanatory
sentence length and connective looseness rather than self-reference, so don't add
"I" to compensate for a flat draft. The first 170 lines of the full draft sit at
2,100 words in 147 sentences (mean 13.8, median 12, standard deviation 11.0), which
means a connected opening can still sit above a flatter rest. Join the clauses when
you revise. That's the pass.

The samples use British spelling in prose, except "synthesizer". They carry
contractions, dry humour, and light UK slang. The hand rewrite uses "innit", "kinda",
"gal", and "whatever" in the preface and tips, whilst the samples avoid em dashes,
semicolons, marketing adjectives, and three-item padding. Copy the habits, not the
catchphrases. One or two personal asides belong in the preface, one per section in
the body, and never in a step.

I'm chummy, nerdy, and British, and the hand-written README says the prose "might
sound a bit chummy, nerdy and British", then asks the reader to write their own
release front door. It also says "I'm going to feel guilty and embarrassed if you
use umetate to make something and publish it with awful slop marketing blurb docs.
Please take care of the community." That's the front-door calibration: keep the dry
aside, the self-deprecating admission, and the direct request, because a community
paragraph earns its place when it names a real stake and asks for something
specific. It doesn't earn its place as "we are passionate about empowering
creators". That's the register.

## Rhythm gate

The doc skill uses the same gate as the humanizer. The hand-written manual is 15.6
mean, 13 median, 12.1 standard deviation, longest 66. The K5/K5000 guide is 17.6 /
14 / 16.7, longest 80. The repo-wide pass on 64 non-handwritten Markdown files moved
the prose from 13.1 / 11 / 9.1 to 15.5 / 13 / 10.3. The docs group landed at 17.0 /
15 / 10.4, the plugin group at 16.0 / 13 / 11.0, the design group at 16.8 / 14 /
11.6, and the worked example at 15.7 / 13 / 11.3. Use the numbers for the register
the page is in.

| Page | Register | Mean | Median | SD |
| --- | --- | --- | --- | --- |
| Manual, panel, install | Manual | 15.6 | 13 | 12.1 |
| Guide, study, long design note | Guide | 17.6 | 14 | 16.7 |
| Patch sheet, MIDI table, byte layout | Reference | terse | terse | terse |

Run:

```sh
python skills/umetate-humanizer/scripts/voice_stats.py docs/manual.md --register manual
python skills/umetate-humanizer/scripts/voice_stats.py docs/dsp-study.md --register guide
```

The script reports the mean, median, standard deviation, longest sentence, short
and long sentence counts, first person, contractions, brackets, and exclamations. A
mean in band is not enough. A high median with a low spread means the page is
uniformly long, and a low median with a low spread means it is uniformly short. Add
a longer setup, a shorter landing, or a split. Do not pad a reference page.

The gate covers prose paragraphs and multi-sentence comments. It does not cover
tables, register maps, one-line labels, forms, or reference sheets, because those
stay terse. The voice profile itself is a reference, so measure it with
`--register manual` or `--register reference`, not `--register guide`. A manual page
that passes the gate still needs the facts, the panel names, and the
no-information-loss check.

## Design interview

The manual preface and any design note come from the author, not from the model. A
point-blank "what is your design philosophy?" produces nothing, so run the interview
before you write the preface and ask for a specific patch, model, bug, or constraint.

`umetate interview --synth <dir> --write` generates the form from the project's
`patch.json`, `panel.json`, `synth-brief.md`, and `plugin.json`, and writes it to
`<dir>/design-interview.md`. The questions use the synth's own architecture and
the brief's words, so it doesn't assume FM or Type P.fm1. Read the generated form,
add or remove questions from the brief, then conduct the interview one topic at a
time. If the brief is missing, the generic core still works. `--next 3` prints the
next missing items, and `--check` lists every open question. The full protocol is in
`references/design-interview.md`, and the generic core is
`templates/design-interview.md`. Use it.

Ask for:

- the first patch or sound that made the synth happen,
- the synths or chips it came from, and what was rejected,
- the design decisions and what each one cost,
- a failure, a limit, and a patch recipe,
- what the author wants a player to understand.

Follow up on every vague answer. "Which model?" "What did it sound like?" "What
broke?" "What did you keep?" A setting and a sound beat an adjective, and one
concrete detail is worth more than a paragraph of taste.

The raw notes are private, so don't copy them into `docs/` or the release. Write the
public design note from them, in the author's voice and with the manual calibration,
cutting the questions and keeping the concrete details and the author's asides. Do
not invent an answer. Keep asking.

## Document set

A synthesizer project ships a small set of user-facing documents, and each one has a
job that the others cannot do. Give each one its job.

| Document | Job |
| --- | --- |
| README | The front door. A one-sentence description. The web app link. Install steps. |
| User manual | Architecture, sound design, and the panel walkthrough, from the player's chair. |
| Guide or instrument study | A historical or technical guide to an existing instrument or lineage. The reader may not own the hardware. |
| MIDI and SysEx reference | The CC map, the note routing, the SysEx message format. |
| Patch sheet | A blank form a user can print and write a patch on. |
| Installation | Flashing the firmware and running the web app. |
| Release notes | The changes in each version, for the person updating. |

The patch sheet uses the panel values and ranges, because that is what the player
sees. Ratio is 0.50 to 16.00, levels and rates are 0 to 99, and feedback and amounts
are 0 to 100%. Do not write 65536 or 32767.

The manual, including the panel section, is the most read page, so spend the most
care there. `docs/panel.md` is a short redirect for old links.

## User manual

Open with the sound, not the spec. Tell the player what kind of instrument this is
and what it is good at, then walk the signal from the keys to the output in the order
a player thinks about it. Then write it.

A guide or study may be for readers who do not own the instrument, so state the
audience early. The K5/K5000 guide says "for players and sound designers", and the
guide register is in `references/voice.md`.

The manual can open with a design note, not a spec sheet. The design note is in the
front-door register: the history, the constraint, the things the author wanted to
change, and a short numbered list. The hand rewrite has seven. Then hand over to the
manual register. The preface can run to several paragraphs and 150-word paragraphs,
whilst the parameter sections stay 40 to 120 words. The design note comes from the
interview, not from the model. Use the answers in `design-interview.md`.

Fetch real manuals as style and content references before you write. Good anchors:
the Yamaha DX7 owner's manual and the Reface DX, the Korg opsix and Volca FM, the
Roland System-8 or JU-06, the Sonicware Liven series, and the Mutable Instruments
Plaits and Braids manuals. Read how they describe a parameter: one short sentence
for what it is, one for what you hear when you turn it. Copy that shape, never
their prose or their brand voice. Consult, do not derive.

For every parameter, answer three questions in plain words:

1. State the function.
2. Describe the sound when you change it.
3. Describe the ends of the range.

Write the explanatory prose with contractions, because the hand rewrite has 33 in
1,899 words and the first release had 1, which is why it read like a contract. Use
"you" for the player, "I" for the author's choices, and "it" for the instrument. One
or two "I" per section is fine, and the preface can carry more.

Example of the shape, from an FM level parameter: "Operator level. This sets how
loud operator 1 is inside the voice. At 99 it rings clearly, at 50 it is about 12
decibels quieter, at 0 it is silent." Three sentences, concrete, no theory, and the
reader can hear the change.

Name the operators and the parts the way the panel names them. If the panel says
OP1 through OP4, the manual says OP1 through OP4, and you shouldn't invent new names
for the sake of variety. Use the panel names.

A tip is allowed when it gives a setting and a sound: "a sine operator taking no
modulation will kinda become a reverse sawtooth at about 25%-35%." Label it "Tip:"
if the section is dense. Three concrete tips are content, not padding. End the
manual with a patch recipe or an instruction, not an aphorism.

The hand rewrite keeps "innit", "kinda", "gal", and "whatever", so keep them in the
preface and one-line tips and never in a procedure, a warning, or a reference table.
Keep the author's self-description ("I'm more of a sound design gal"), and do not
change "gal" to "guy" or "person".

## Panel section

Write the panel section as part of the user manual, after the sound-design chapters
and before the first-patch chapter. Read the filled control map and `panel.json`, so
the page inventory and the button chords match the firmware.
`templates/panel-reference.md` is the shape.

A fresh reader must be able to move without guessing, so name every context button,
say what pressing it again does, explain how the page encoder and HOME work, and
list every modifier chord. Then give every page a row: its title, KNOB 1 to 4
assignments, display widgets, and the job of the page. State the page-knob rule:
the four encoders edit the parameter rows in order, the extra encoders do nothing
on a short page, and display pages have no assignments. Name every button.

State the save, load, init, copy, and name flows exactly, because a reader who has
to guess at a confirmation will guess wrong. Say which buttons, which knobs, what
the screen confirms, and what auto-closes without committing.

Popups are worth a sentence: they own the controls while open, they close on their
own after about three seconds of no input, and a cancel does not lose work.

## MIDI and SysEx reference

State the receive channels, the CC to parameter map, sustain, panic, pitch bend, and
program change, then the SysEx format: the header, the command byte, the data layout,
and the exact bytes of each of the five commands the firmware answers. A user who
wants to back up patches with a SysEx librarian must be able to do it from this page
alone. Use tables for the maps, and keep the prose around them short. Keep it exact.

## Patch sheet

Fetch a few real patch sheets for comparable instruments (DX7, Volca FM, opsix) to
see how they lay out one patch per page, then build a blank template for this project
with a row for every parameter in the same order the panel walks them. Leave room for
a name, the algorithm, and a comment, and make it printable. Test it on paper.

## Installation

Two paths, both explained for a non-programmer: flashing the firmware, and opening
the web app. For flashing, give the exact command and the exact recovery step if
something goes wrong. For the web app, give the URL and the one thing to click, and
do not assume the reader knows what a terminal is. Assume nothing.

## Release notes

One section per version, newest first, with the version number and a date. Write
for the person updating: what changed, what they will notice, and whether a saved
patch still loads. Keep each entry to a few lines. This is the one place a
"changed from X to Y" sentence is correct, because it is a changelog by definition.
Keep it short.

## Publishing

`umetate publish` copies the project's `docs/*.md` into the release and renames
`docs/release-notes.md` to `CHANGELOG.md`. The generated README is a fallback. If
the project has a hand-written `publish-readme.md`, publish copies it verbatim and
never overwrites it, so write that file by hand in the front-door register. The
generated template is there for a project that doesn't have one yet. The hand-written
README asks the author to do this: "Show that amount of passion for your own project
as well, I beg you." A release front door with a real reason, a specific sound, and a
plain limitation is the target, whilst a template full of marketing blurb is the
failure.

The three docs the generated README links to are `docs/manual.md`,
`docs/midi-and-sysex.md`, and `docs/patch-sheet.md`, so keep those names. The manual
includes the panel section, and `docs/panel.md` is a redirect for old links. If the
project has more docs, link them from the README and the manual index. Write it by
hand.

## Writing craft

This is the humanisation part, the anti-slop part, and it applies to every page. It
is a distillation of the author's corpus and the usual AI-tell catalogue, aimed at
technical prose, plus what good hardware manuals already do. The same method is
packaged for prose outside the user docs as `skills/umetate-humanizer/SKILL.md`, so
the two skills should sound like the same person. Same person.

**Do not flatten the voice.** The biggest failure mode is a manual that reads like a
spec sheet. The first release did. The hand rewrite has 22 first-person pronouns and
33 contractions. If your draft has 2 and 1, you have over-edited. The guide rewrite
kept the same three first-person tokens as the draft and changed the sentence
structure instead. Do not add "I" to compensate for a flat draft. Add explanatory
clauses, connectives, and a longer sentence where the thought needs it. Attach a
fact with a relative clause, a specification with "with" and a colon, a condition
with "only when", and a cause with "so" or "because".

**Address the reader as "you".** "Turn the knob" beats "the user turns the knob",
because the second one puts a help desk between the player and the instrument. Put
the player in the room.

**Active voice, named actors.** "Hold SHIFT and press SAVE" beats "the save
function is triggered by pressing the button", because the first one tells the reader
what to do. The instrument is the actor where there is no person, and that is fine,
since the instrument is the thing the reader owns.

**Concrete over abstract.** "The low end thins out" beats "the timbre becomes
brighter", and a number is better still when there is a number to give. A sentence
that could describe any synthesizer describes none of them.

**One main point per sentence.** When a sentence has three unrelated clauses, it is
two sentences, but when the clauses belong to one thought, a longer sentence is
fine. Let a short sentence land next to a long one, and vary the length on purpose.
The hand rewrite has a 66-word sentence, and the guide rewrite has an 80-word
sentence and a 16.7-word standard deviation. A long sentence is fine when the
clauses belong together, so split it only when the reader has to backtrack.

**Plain words over jargon.** The exact term stays where the panel uses it, so don't
invent synonyms for "operator" or "algorithm". Everything else gets the plain word.
Pick the plain word. Keep the author's deliberate vagueness: "OPwhatever", "or
whatever", "aka". Pair
"OPwhatever" with "DX" so a reader can infer the family, and don't replace it with a
precise model list the author did not write.

**Kill the filler.** Delete "in order to", "it is worth noting", "in the context of",
and "utilize". Delete the summary sentence that restates the heading, and delete the
opening that promises what is coming. Start with the content. "In order to" is
usually "To", but the author sometimes uses it to set up a purpose clause, so suggest
the short form only when it does not flatten the rhythm.

**No hedging stacks.** Commit to what you know. One genuine uncertainty is fine, but
two qualifiers are slop, and this is an instrument manual rather than a research
paper. "Sort of" and "probably" are calibrated hedges in the guide, and "and so on"
and "a bunch of" are generalisers, so keep the ones that are doing work. Commit.

**No rule of three padding.** List the real items, and two or four is fine. Three
abstract nouns in a row is a tell, whilst a 7-item design list is content and three
concrete tips are content. The ban is on three abstract nouns doing the work of one
fact.

**No promotion.** "Seamless", "robust", "state of the art", and "unleash" have no
place next to a knob. Say what it does, and let the player decide if it is good.

**State it directly.** A fact is a fact, an analysis is an analysis, and an assertion
is an assertion, so don't dress an assertion as a question, a fact as a maybe, or a
contrast as a revelation. "The filter is 12 dB per octave and does not
self-oscillate" is the whole sentence, and it does not need a setup. State it.

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
of attached qualification. The ban is on the theatrical "not just X, it's Y" hook,
not on a factual limit that carries real information.

**No heading chains.** Don't write "The Engine", "The Filter", "The Envelope:
Shaping Your Sound" for every section. Vary the grammar, use the reader's words, and
don't make a section for every noun. One "The X" heading is fine, but a chain is a
generated outline. Vary it.

**No article drumbeats.** A list where every item starts with "The" reads like a
specification, so drop the article, lead with the noun or the verb, or write the list
as prose. "CLI. It checks the environment." reads better than "The CLI. It checks
the environment." repeated down the page.

**No wh-word headings or labels.** "What to reach for first", "How to move", and
"What it does" are questions the reader did not ask, so use a noun phrase or an
imperative: "Get started!", "Navigation", "Functionality". The rule covers headings,
table column headers, and checklist labels.

**No counted couplets.** A heading, caption, or table description built as two
counts reads like a slogan: "One page, one job", "Two sources, one filter", "One
phase, many amplitudes". It sells a shape instead of naming the section, so use a
noun phrase or an imperative and put the count in the body where it can be
explained. The rule covers headings, captions, and table descriptions, not prose.

**No raw storage values.** A user document describes the value on the screen, not
the number in the firmware. "Ratio is written 65536" and "feedback runs 0 to 32767"
tell the reader about a representation they cannot see, so write the panel range:
"ratio 0.50 to 16.00", "feedback 0 to 100%". A patch sheet is a panel form, not a
memory dump. Show the value.

**Use the project vocabulary.** Six words carry a model's framing and hide the fact
underneath, and they are hard bans in prose.

| Do not write | Write instead |
| --- | --- |
| claim, as a label for a feature | claimed feature, or name the feature |
| source of truth | only reference, single reference |
| I built, we built | I made, we made |
| dogfood | test project made from our own readymade components, then the test project or the worked example |
| lives in, live in, for a file, folder, sub-project, document, or component | is in the PATH folder, is stored at, PATH's path within the repo is |
| gap, for missing work | missing work, missing feature, bug, oversight, problem |

"`docs/roadmap.md` is the source of truth for the status of each claim" becomes
"`docs/roadmap.md` is the only reference for the status of each claimed feature."
"The example's implementation lives in `modules/nodes/`" becomes "The
implementation is stored at `modules/nodes/`." "The build composes the dogfood
firmware" becomes "The build composes the example firmware made out of the pre-made
umetate components." "I built the example to expose the next gaps" becomes "I made
the example to expose the next missing work."

Keep "claim" as a verb when the evidence matters, and in a licence or warranty. Keep
"built" for a compiled binary, a target package, or a CI job, and keep "gap" for a
grid gap, a silent gap in audio, or a measured interval. Keep a code identifier, a
command, a schema key, or a quoted source exactly as it is. A `gap` column in a table
of missing hardware is a missing item, so rename it.

**No product self-description.** A "what this is" section in a manual or an app's
help rail explains the product to someone already using it, so put the proof in the
README or the release notes. Use the page for the next action, the controls, or a
real limit. Use the page.

**No false dichotomies.** Don't invent a strawman to make the instrument look
different. "Most synths make you menu-dive. This one doesn't" only works if you can
name the synths and the difference is real. If the instrument is a four-operator FM
synth, say that, because it does not need an enemy.

**No marketing hooks.** No "Imagine", "What if", "Meet", "Say hello", "Unlock",
"Dive into", "Whether you're a beginner or a seasoned producer", "The result?", "But
here's the thing", or "Let's break it down". Start with the content.

**Open with the plain category.** A guide can start with a fact and a reason to
care, not a balanced thesis. The K5/K5000 guide opens "The K5 and K5000 are two
additive synths from Kawai. Additive synths are rare, so they're an interesting case
study." The model draft's "The K5 is a spectral instrument you learn by doing. The
K5000 is a spectral instrument you compose with" was cut, so plain category first.

**State the audience and the scope.** "This guide is for players and sound
designers" and "it isn't a technical manual, so the diagrams are purely explanatory
rather than factory schematics." The reader may not own the hardware, so say so
early.

**Do not drop the qualifier.** A casual phrase can replace a precise one, but it
must not lose the fact. "Harmonic 64 is missing for some quirky reason" is fine, but
it drops "documented", so keep the fact and the casual wrapper. Keep the fact.

**Fix grammar, not voice.** "both parts's algorithms" becomes "both parts'
algorithms". A comma splice can stay if it reads as one thought. Don't replace
"kinda" with "somewhat", "gal" with "person", or "innit" with "right?" unless the
author asks. Don't turn "2x4-op" into "two-by-four-operator" in every mention. "the
even harmonics over from the odd ones" becomes "the even harmonics take over from
the odd ones", and "more of an specialised tool" becomes "more of a specialised
tool". Fix the grammar.

**No invented facts.** A humanising pass may not add a model, a date, a number, or a
quote. The hand rewrite's DX21/DX7 comparison, Chowning, ymfm, Dexed, and Yamaha
chip order are the author's knowledge, so the model doesn't get to add its own. The
guide rewrite's definition of a harmonic, its comparison to PM sidebands, and its
"probably" about the K5/K5000 are also the author's, so keep them.

**Read it back as speech.** If you can't imagine a patient teacher saying the
sentence out loud, rewrite it until you can. Read it aloud.

## No information loss check

After you write a page, go back paragraph by paragraph. For each original paragraph,
name its facts and compare them to what you wrote, and if a fact did not survive, put
it back in the new voice. This is not optional, because a humanised page that dropped
the SysEx checksum is a broken page. Check every paragraph.

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
- [ ] No `The... The...` list. Drop the article or lead with the noun or verb.
- [ ] No wh-word heading or table label. Use a noun phrase or an imperative.
- [ ] No counted-couplet heading, caption, or table description. Name the section
      and put the count in the body.
- [ ] No raw storage value. Show the panel value and range.
- [ ] No bare claim for a feature, no "source of truth", no "I built" for a made
      thing, no dogfood, no "lives in" for a location, and no "gap" for missing work.
- [ ] A last grep for `claim`, `source of truth`, `dogfood`, `lives in`, `gap`, and
      `I built` finds no prose use.
- [ ] The rhythm gate passes for the page's register, or the page is a reference
      where the gate does not apply.
- [ ] The median and standard deviation are in band, not only the mean.
- [ ] The front-door asides carry a reason or a real stake. They are not slogans.
- [ ] No what-this-is section in an app or a manual.
- [ ] No needless "It's a X, not a Y" or "It's not an X" setup. The positive comes
      first.
- [ ] A conversational correction can keep the negative when it corrects an
      inference or names missing evidence.
- [ ] Factual limits and real scope contrasts stay.
- [ ] A concrete detail can end a paragraph without a summary verdict.
- [ ] No aphorisms or poster-slogan conclusions. End on a concrete fact, an
      instruction, or a specific judgement.
- [ ] No "A, not B" adversative. Use "rather than", a separate sentence, or a "but"
      clause.
- [ ] No heading chain ("The X", "The Y", "The Z: ...").
- [ ] No false dichotomy and no invented contrast.
- [ ] No marketing hook.
- [ ] The closing is an instruction or a verdict, not an aphorism.
- [ ] The first sentence says the thing, not "In this section".

## Credits and licences

When you fetch a real manual or patch sheet, you consult it for shape and approach,
and you don't copy its prose or its layout verbatim. If you adapt a specific diagram
or table closely, credit the maker and note the licence in the project's LICENSING
file, which is the same rule the development skill applies to code. A manual's ideas
are generally facts you restate, not text you reproduce.
