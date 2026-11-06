# umetate voice data

This is the project voice data for `skills/umetate-humanizer/SKILL.md`, and I'd read
it before rewriting a manual, a README, release notes, a panel section, or a guide or
study. The runtime method is in `skills/umetate-humanizer/SKILL.md`, which carries the
negation test, the connectivity pass, the aphorism ban, the "A, not B" ban, the
registers, and the no-information-loss check. This file is the project-specific
voice data that sits underneath it.

The hand-written manual is `examples/type-p-fm1/docs/manual.md`, which the author
rewrote after the first release. That rewrite is the target, not the earlier, flatter
version. The K5/K5000 guide rewrite in `doc-test/` is the guide calibration, and it
isn't committed, but the excerpts in
`skills/umetate-documentation/references/voice-samples.md` are.

## The voice in one paragraph

The target is a builder and a player talking to another builder or player, with first
person, normal contractions, dry asides, technical exactness, and light UK slang. I
like a long setup and a short landing, and I'm happy for the instrument to be the
actor when no person is doing anything. The manual can open with a design note in the
front-door register, then settle into the reference voice, whilst a guide or study can
open with the plain category and a causal link and carry longer explanatory sentences
later. Do not flatten either one into a spec sheet, because the flattening is the
failure mode.

I'm chummy, nerdy, and British, and the hand-written README says the prose "might
sound a bit chummy, nerdy and British", then asks the reader to write their own
release front door. It also says "I'm going to feel guilty and embarrassed if you use
umetate to make something and publish it with awful slop marketing blurb docs." That's
the target: warm, direct, a little self-deprecating, and completely serious about
keeping the community's docs readable. An aside earns its place when it carries a
reason, a real stake, or a specific care for the reader, and a slogan doesn't.

## Calibration

The first manual was 971 words, with a mean sentence of 11.3, a median of 10, a
standard deviation of 6.4, 2 first-person pronouns, and 1 contraction, which is why
it read like a contract.

The hand rewrite is 1,899 words, with a mean sentence of 15.6, a median of 13, a
standard deviation of 12.1, 22 first-person pronouns, 33 contractions, 7 brackets,
and 4 exclamation marks. The longest sentence is 66 words, the shortest fragment is
one word, and the current manual appends the panel section, so the file is longer.
The hand-written part remains the calibration.

If a rewrite produces numbers near the first set, it has over-edited.

The guide's first 70 lines moved from 689 words in 58 sentences (mean 11.6, median
9.5, standard deviation 8.5, longest 52) to 737 words in 41 sentences (mean 17.6,
median 14, standard deviation 16.7, longest 80). The first-person count stayed at
three, because the change was explanatory sentence length and connective looseness
rather than self-reference, so don't add "I" to compensate for a flat draft.

## Preserve these

- **The self-description.** "I'm more of a sound design gal." Do not neutralise
  "gal" to "person" or "guy".
- **Light UK slang and internet asides.** "innit", "kinda", "gal", "whatever",
  "aka", "i.e.", "terminally online". A few per page, never in a step, a warning, or
  a reference table.
- **In-group references that are factual.** DX/OPwhatever, OPL3, TX81z/D11/V50,
  ymfm, Dexed, DX21/DX7.
- **The concrete patch tips.** The three feedback tips, the ratio ranges, the
  reverse-saw recipe, the wavefolder swell.
- **The Taco Bell aside.** It names the bell-like sound and is one sentence. Keep
  it.
- **Deliberate contrast bold.** `**is**` and `**does**` in "not an emulation, but it
  **is** a DX-style synth". This is not P42 erratic bolding.
- **Self-corrections and calibrated hedges.** "What I mean is", "I think", "kinda",
  "I've got to say". They are voice, not leftover hedge debris.
- **The instrument as actor.** "The filter removes", "the envelope holds". Correct
  in a manual, not P44 false agency.
- **Concrete triads and tip lists.** Three real settings are content, not P10 or
  P15.
- **The plain category opening.** "The K5 and K5000 are two additive synths from
  Kawai. Additive synths are rare, so they're an interesting case study." A plain
  category and a reason to care beat a balanced thesis.
- **The causal guess.** "The K5's shortcomings probably were part of what motivated
  the K5000's design." "Probably" is the right hedge for an inference.
- **The explanatory long sentence.** The guide rewrite has an 80-word sentence.
  Keep it if it reads as one thought.
- **The connectivity join.** "Each additive source holds 64 harmonics, with two
  possible settings: Low is 1 to 64, and High is 65 to 128." A specification
  attached to its main clause is voice, not a compression trick.
- **"In order to", "whilst", "has got", "sort of", "and so on", "a bunch of",
  "probably", "(!)"**. These are voice in explanatory prose. "(!)" is a genuine
  surprise marker, not P41.
- **Factual "rather than just" contrasts.** "A complete voice path, rather than
  just the oscillator" names both sides. It is not the P9 hook.
- **A spoken correction.** "That is just a tour-rig claim, though, with no album
  credits to back it up." The negation carries a limit, and the aside stays.
- **A slash in a scope label.** "anecdotal/historical records" is a category label,
  not prose punctuation.

## Negation

The author removed almost every "It's a X, not a Y" and "It's not an X" setup from
the guide, so don't add them back.

- Cut the setup and state the positive.
- Replace the label with the constraint.
- Replace the contrast with the cause.
- Use a comparative when the contrast is real: "more X than Y".
- Attach a needed qualification to the positive: "rather than just...".
- Keep factual limits ("you can't add...", "it isn't a universal system") and scope
  contrasts ("purely explanatory rather than factory schematics").
- If you remove a negation, keep the fact it carried.

The test is simple: a negation earns its place only when it carries a causal link, a
factual comparison, a counterintuitive explanation, a real limit, or a correction of
a misconception. If it carries none of those, cut it.

The before and after table is in
`skills/umetate-documentation/references/voice-samples.md` under "Replacing the
negation".

## Conversational correction

A correction can keep the negative. The author wrote "But that doesn't mean one is
necessarily better than the other! They've just got different personalities." and
"That is just a tour-rig claim, though, with no album credits to back it up." The
negation carries a correction or a limit, so it stays, and "just", "though", and
"more of a" scale the claim. Don't turn it into a label contrast.

A concrete detail can end a paragraph. The author cut "That is the K5 in its natural
habitat: a professional tool under deadline." after the Jan Hammer detail, because
the detail already carried the point and a closing verdict that restates the
paragraph is filler.

Anecdotal asides use "anecdotally, though" and "I'd really like to". One per
section at most.

## Aphorisms

An aphorism is a short, universal-sounding verdict that could go on a poster. The
author cuts them. "Its restrictions are the lesson" becomes "The K5's two sources
and four envelopes are enough to learn how harmonic groups move." "Two sources
with clear jobs beat six sources with vague ones" becomes "Start with two sources
and add another only when you can name its job." A specific verdict is fine. A
slogan is not.

Do not write "A, not B" as an adversative. Use "rather than", a separate sentence,
or a "but" clause. The comma-not form is a spec-sheet habit.

## Product self-description

A standalone "what this is" section in the product's own interface is a writer's
note left on the page. The reader is already looking at the instrument. The
heading restates the category, and the paragraph offers proof the reader cannot
use yet: "the firmware, compiled to WASM", "the same 44.1 kHz engine", "the real
240 by 240 screen". All of it can be true and still be slop, because none of it
helps the reader play a note.

The tell is the mismatch between the reader's situation and the section's job. A
person who opens the app wants to make a sound. A "what this is" section answers
a question the maker is anxious about: is this a real instrument, is it the same
engine, is the screen real. Put that proof in the README, the release notes, or
the manual. In the app, spend the words on the next action, the controls, or a
real limit.

Before:

> What this is
> The FM-1 firmware, compiled to WASM. It runs the same 44.1 kHz engine as the
> device and the plugin. The screen is the firmware's own 240 by 240 framebuffer.

After:

> Press switch on, then play the keys.

If a fact is genuinely needed at that point, make it a limit: "This needs a browser
with WebAudio and a current graphics driver." A limit helps the reader decide, and a
product description does not.

## List drumbeats

A list where every item starts with "The" reads like a spec sheet, because the
repeated article turns the items into a drumbeat: "The CLI. The development skill.
The safety skill." The reader stops hearing the jobs and starts hearing the grammar.

Drop the article and lead with the noun or the verb. "CLI. Everything starts at
`umetate`." "Development skill. It guides the workflow." If the items are really
sentences, write the paragraph instead of the list, because a list earns its place
when the items are short, parallel, and easy to scan, and a list of full sentences
with the same article is prose in disguise.

Before:

> - The CLI. It checks the environment.
> - The development skill. It guides the workflow.
> - The safety skill. It holds the gates.

After:

> - CLI. It checks the environment.
> - Development skill. It guides the workflow.
> - Safety skill. It holds the gates.

The facts are the same. The drumbeat is gone.

## Wh-word headings

A heading made from a wh-clause is a question the reader did not ask, so "What to
reach for first", "How to move", "What it does" and "Where they sit" read like a
generated outline or a help centre. They also make the writer sound unsure of the
noun.

Use a noun phrase for a topic and an imperative for an action. "What to reach for
first" becomes "Get started!", "How to move" becomes "Navigation", and "What it does"
becomes "Functionality". The table header and the heading follow the same rule.

Before:

> What to reach for first
> How to move
> | Parameter | Range | What it does |

After:

> Get started!
> Navigation
> | Parameter | Range | Functionality |

The same rule applies to table column headers, checklist labels, and section titles,
and a question can stay in body prose when the reader is actually asking it.

## Counted couplets

A heading, caption, or table description built as two counts reads like a slogan,
because "One page, one job", "Two sources, one filter", "Four operators, eight
algorithms" and "One phase, many amplitudes" sell a shape instead of naming the
section. The counts sound balanced, so the line feels finished before it says
anything.

Use a noun phrase or an imperative, and put the count in the body where it can be
explained. "One page, one job" becomes "Page-based screens", then the paragraph says
how many jobs each page carries, and "One phase, many amplitudes" becomes "The shared
phase accumulator", then the paragraph explains why one phase drives every partial.

Before:

> ## One page, one job
> ## One phase, many amplitudes
> | A-ENVS | Four envelope graphs, one per operator. |

After:

> ## Page-based screens
> ## The shared phase accumulator
> | A-ENVS | An amplitude-envelope graph for each operator of the active part. |

The rule covers headings, captions, and table descriptions. A counted pair in body
prose can be a real comparison: "One source is enough for a sine, two give you the
Low/High split." Keep it when the numbers do work.

## Storage values

A user document describes the value on the screen, not the number in the firmware,
because "Ratio is written 65536" and "feedback runs 0 to 32767" tell the reader about
a representation they cannot see. Write the range the panel shows: "ratio 0.50 to
16.00", "feedback 0 to 100%". A patch sheet is a panel form, not a memory dump.

Before:

> A ratio of 1.00 is written 65536 in the panel's raw value. Feedback runs 0 to 32767.

After:

> ratio (0.50..16.00), feedback (0..100%).

## Connectivity

A guide joins a fact to its cause, condition, or specification, because a page of
separate declaratives makes the reader do the joining. The model draft wrote "Each
additive source holds 64 harmonics. Low is 1 to 64. High is 65 to 128", and the
author wrote "Each additive source holds 64 harmonics, with two possible settings:
Low is 1 to 64, and High is 65 to 128."

- Attach a fact or an explanation with a relative clause: "Harmonic 64 is missing,
  which is a documented quirk of the instrument."
- Attach a specification with "with" and a colon.
- Attach a condition with "only when".
- Use a colon for a list that follows.
- Use a parenthesis for a source pointer.
- Join a cause to its consequence with "so" or "because" when the link is real.

The first 170 lines of the guide average 13.8 words per sentence against 17.6 in the
first 70, partly because the later sections carry lists and tables, but the prose
still needs the joins. A page of short declaratives has lost the guide register even
when every fact is right.

## Fix these

- **Possessive grammar.** "both parts's algorithms" becomes "both parts'
  algorithms".
- **Comma splices only when the reader has to backtrack.** A 66-word or 80-word
  sentence can stay if it reads as one thought.
- **Repeated "so" and "kinda" only when they crowd a paragraph.** Do not ban them
  outright.
- **Hyphenation.** "phase-modulation synthesizer" is a compound modifier. "phase
  modulation" is the noun. Both are correct.
- **The two guide errors.** "the even harmonics over from the odd ones" becomes
  "take over from". "more of an specialised tool" becomes "more of a specialised
  tool".
- **The dropped qualifier.** "Harmonic 64 is missing for some quirky reason" is fine
  as a phrase, but it loses "documented". Keep the fact: "for some quirky reason.
  It's a documented quirk, not a mistake in your patch."

## Project vocabulary bans

These are hard bans in prose, and the substitute is the plain phrase rather than a
synonym with the same framing.

| Do not write | Write instead |
| --- | --- |
| claim, as a label for a feature | claimed feature, or name the feature |
| source of truth | only reference, single reference |
| I built, we built | I made, we made |
| dogfood | test project made from our own readymade components, then the test project or the worked example |
| lives in, live in, for a file, folder, sub-project, document, or component | is in the PATH folder, is stored at, PATH's path within the repo is |
| gap, for missing work | missing work, missing feature, bug, oversight, problem |

Keep "claim" as a verb when the evidence matters, and in a licence or warranty. Keep
"built" for a compiled binary, a target package, or a CI job, and keep "gap" for a
grid gap, a silent gap in audio, or a measured interval. Keep a code identifier, a
command, a schema key, or a quoted source exactly as it is.

"Source of truth" was the old status word, and the new reference is "only reference"
or "the single reference". The README now says `docs/roadmap.md` is "the only
reference for the design, implementation plan, and status of each claimed feature."

"I built" became "I made" in the worked example: "Type P.fm1 is a worked example I
made to put the framework through the process." Keep the author's hands in the
sentence.

"Dogfood" became "the example firmware made out of the pre-made umetate components"
in the build comment, and "the test project" in the status prose, because the word hid
the fact that the author was testing their own components. Say the fact.

A file does not live. The plugin source is in the `plugin/` folder, the modules are
stored at `modules/nodes/`, and the framework source's path within the repo is
`umetate/`.

"Gap" became "missing work", "missing items", "open questions", "bug", "oversight",
or "problem", because a gap in a plan is a missing feature, a gap in the interview is
an unanswered question, and a gap in the evidence is a missing measurement. Name it.

## Hard bans

- No em dash. No semicolon.
- No swearing in published docs. The corpus swears, the release does not.
- No bare claim for a feature, no "source of truth", no "I built" for a made thing,
  no dogfood, no "lives in" for a location, and no "gap" for missing work.
- No marketing hooks, negative-parallelism hooks, false dichotomies, or heading
  chains.
- No needless "It's a X, not a Y" or "It's not an X" setup. Start with the positive.
  Keep factual limits and real scope contrasts.
- No invented facts. A rewrite may not add a model, a date, a number, or a quote.

## Before and after

Flat first release:

> Feedback works on any operator, but it shows up most on carriers and on the top
> operator of a stack.

Hand rewrite:

> All operators have feedback, but traditionally it shows up the most on carriers
> and on the top operator of a stack. That's because of the way Yamaha chips work:
> the operators were always computed in the same order and the one with feedback
> was always the first one.

The rewrite adds the mechanism and the teaching voice, and it isn't padding.

Aphorism first release:

> The same settings, two very different instruments, is the whole of FM in one knob.

Hand rewrite:

> Try looking at the operator oscilloscopes to check out how the cascading phase
> modulation progressively warps each waveform!

The instruction is stronger than the aphorism, so prefer it.

### Project vocabulary

Old draft:

> `docs/roadmap.md` is the source of truth for the status of each claim. The dogfood
> firmware lives in `examples/type-p-fm1`, and I built it to expose the next gaps.

Hand rewrite:

> `docs/roadmap.md` is the only reference for the design, implementation plan, and
> status of each claimed feature. The test project made from our own readymade
> components is in the `examples/type-p-fm1` folder, and I made it to expose the next
> missing work.

The facts survive. The status shorthand, the insider jargon, the construction
metaphor, the location verb, and the planning word do not survive.

### Anti-slop promise

The hand-written README is the calibration for the front-door aside:

> I've tried to calibrate the resulting prose from my own personal writing, which
> might sound a bit chummy, nerdy and British. If that's not your thing I appreciate
> your position, but I'm going to feel guilty and embarrassed if you use umetate to
> make something and publish it with awful slop marketing blurb docs. Please take
> care of the community.

The aside admits a taste, names the stake, and asks for something, so keep that
shape. A line like "we are passionate about empowering creators" has the same topic
and no person in it.

### Guide opening

Model draft:

> The K5 and K5000 are the two Kawai instruments that take additive synthesis
> seriously. They are not the same idea at two sizes. The K5 is a spectral
> instrument you learn by doing. The K5000 is a spectral instrument you compose
> with.

Author rewrite:

> The K5 and K5000 are two additive synths from Kawai. Additive synths are rare, so
> they're an interesting case study. They came out at different times and the K5's
> shortcomings probably were part of what motivated the K5000's design.

The author cut the balanced thesis and the paired metaphors, because the plain
category and the causal guess are the target.

### Technical guide

> A Kawai-style harmonic source does not need 64 or 128 independent oscillators.
> The partials share one fundamental, so one phase accumulator can drive them all.
> For a note with fundamental f0, the kth partial is at k times f0, and its phase
> is k times the fundamental phase. The engine keeps one phase trajectory and a
> set of amplitude trajectories. That is the central computational simplification,
> and it is why these instruments could produce so many partials on the hardware
> they had.

The paragraph gives the constraint, the mechanism and the reason. The numbers are
exact, the metaphor is absent, and the engineering vocabulary stays in the
sentence. This is the register for a software reconstruction: explain the machine
to a reader who will build it.

### Factual contrast

Model draft:

> The K5000 is a different architecture, not a K5 with a bigger harmonic count.

Author rewrite:

> They came out at different times and the K5's shortcomings probably were part of
> what motivated the K5000's design.

The author preferred the causal and historical link over the neat contrast, so use a
contrast only when both sides are the point.

### Dropped qualifier

Model draft:

> Harmonic 64 is missing. That is a documented quirk of the K5, not a mistake in
> your patch.

Author rewrite:

> Harmonic 64 is missing for some quirky reason.

The casual phrase is fine, but the loss of "documented" is not. Keep the fact and the
casual wrapper.

## Scope

These specifics apply to the author's own docs, including guides and studies about
other instruments. If you are rewriting someone else's text for a different author,
ignore the project-specific slang, the "gal" self-description, and the synth
references. The patterns in `ai-tells.md` still apply.
