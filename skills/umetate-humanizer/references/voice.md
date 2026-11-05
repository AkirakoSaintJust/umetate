# umetate voice data

This is the project voice data for `skills/umetate-humanizer/SKILL.md`.

Read it before rewriting a manual, a README, release notes, a panel section, or a
guide or study.

The runtime method is `skills/umetate-humanizer/SKILL.md`. That file carries the
negation test, the connectivity pass, the aphorism ban, the "A, not B" ban, the
registers, and the no-information-loss check. This file is the project-specific
voice data.

The hand-written manual is `examples/type-p-fm1/docs/manual.md`. The author rewrote
it after the first release. That rewrite is the target, not the earlier, flatter
version. The K5/K5000 guide rewrite in `doc-test/` is the guide calibration. It is
not committed, but the excerpts in `skills/umetate-documentation/references/voice-samples.md`
are.

## The voice in one paragraph

A builder and a player talking to another builder or player. First person, normal
contractions, dry asides, technical exactness, light UK slang. Long setup and short
landing. The instrument can be the actor. The manual can open with a design note in
the front-door register, then settle into the reference voice. A guide or study can
open with the plain category and a causal link, then carry longer explanatory
sentences. Do not flatten either one into a spec sheet.

## Calibration

The first manual was 971 words: mean sentence 11.3, median 10, standard deviation
6.4, 2 first-person pronouns, 1 contraction. It read like a contract.

The hand rewrite is 1,899 words: mean sentence 15.6, median 13, standard deviation
12.1, 22 first-person pronouns, 33 contractions, 7 brackets, 4 exclamation marks.
The longest sentence is 66 words. The shortest fragment is one word. The current
manual appends the panel section, so the file is longer. The hand-written part
remains the calibration.

If a rewrite produces numbers near the first set, it has over-edited.

The guide first 70 lines moved from 689 words in 58 sentences (mean 11.6, median
9.5, standard deviation 8.5, longest 52) to 737 words in 41 sentences (mean 17.6,
median 14, standard deviation 16.7, longest 80). The first-person count stayed at
three. The change is explanatory sentence length and connective looseness, not
self-reference. Do not add "I" to compensate for a flat draft.

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
the guide. Do not add them back.

- Cut the setup and state the positive.
- Replace the label with the constraint.
- Replace the contrast with the cause.
- Use a comparative when the contrast is real: "more X than Y".
- Attach a needed qualification to the positive: "rather than just...".
- Keep factual limits ("you can't add...", "it isn't a universal system") and scope
  contrasts ("purely explanatory rather than factory schematics").
- If you remove a negation, keep the fact it carried.

The test: a negation earns its place only when it carries a causal link, a factual
comparison, a counterintuitive explanation, a real limit, or a correction of a
misconception. If it carries none of those, cut it.

The before and after table is in
`skills/umetate-documentation/references/voice-samples.md` under "Replacing the
negation".

## Conversational correction

A correction can keep the negative. The author wrote "But that doesn't mean one is
necessarily better than the other! They've just got different personalities." and
"That is just a tour-rig claim, though, with no album credits to back it up." The
negation carries a correction or a limit, so it stays. "Just", "though", and "more
of a" scale the claim. Do not turn it into a label contrast.

A concrete detail can end a paragraph. The author cut "That is the K5 in its
natural habitat: a professional tool under deadline." after the Jan Hammer detail.
A closing verdict that restates the paragraph is filler.

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

If a fact is genuinely needed at that point, make it a limit: "This needs a
browser with WebAudio and a current graphics driver." A limit helps the reader
decide. A product description does not.

## List drumbeats

A list where every item starts with "The" reads like a spec sheet. The repeated
article turns the items into a drumbeat: "The CLI. The development skill. The
safety skill." The reader stops hearing the jobs and starts hearing the grammar.

Drop the article and lead with the noun or the verb. "CLI. Everything starts at
`umetate`." "Development skill. It guides the workflow." If the items are really
sentences, write the paragraph instead of the list. A list earns its place when
the items are short, parallel, and easy to scan. A list of full sentences with the
same article is prose in disguise.

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

A heading made from a wh-clause is a question the reader did not ask. "What to
reach for first", "How to move", "What it does" and "Where they sit" read like a
generated outline or a help centre. They also make the writer sound unsure of the
noun.

Use a noun phrase for a topic and an imperative for an action. "What to reach for
first" becomes "Get started!". "How to move" becomes "Navigation". "What it does"
becomes "Functionality". The table header and the heading follow the same rule.

Before:

> What to reach for first
> How to move
> | Parameter | Range | What it does |

After:

> Get started!
> Navigation
> | Parameter | Range | Functionality |

The same rule applies to table column headers, checklist labels, and section
titles. A question can stay in body prose when the reader is actually asking it.

## Connectivity

A guide joins a fact to its cause, condition, or specification. The model draft
wrote "Each additive source holds 64 harmonics. Low is 1 to 64. High is 65 to 128."
The author wrote "Each additive source holds 64 harmonics, with two possible
settings: Low is 1 to 64, and High is 65 to 128."

- Attach a fact or an explanation with a relative clause: "Harmonic 64 is missing,
  which is a documented quirk of the instrument."
- Attach a specification with "with" and a colon.
- Attach a condition with "only when".
- Use a colon for a list that follows.
- Use a parenthesis for a source pointer.
- Join a cause to its consequence with "so" or "because" when the link is real.

The first 170 lines of the guide average 13.8 words per sentence against 17.6 in
the first 70, partly because the later sections carry lists and tables. The prose
still needs the joins. A page of short declaratives has lost the guide register
even when every fact is right.

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

## Hard bans

- No em dash. No semicolon.
- No swearing.
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

The rewrite adds the mechanism and the teaching voice. It is not padding.

Aphorism first release:

> The same settings, two very different instruments, is the whole of FM in one knob.

Hand rewrite:

> Try looking at the operator oscilloscopes to check out how the cascading phase
> modulation progressively warps each waveform!

The instruction is stronger than the aphorism. Prefer it.

### The guide opening

Model draft:

> The K5 and K5000 are the two Kawai instruments that take additive synthesis
> seriously. They are not the same idea at two sizes. The K5 is a spectral
> instrument you learn by doing. The K5000 is a spectral instrument you compose
> with.

Author rewrite:

> The K5 and K5000 are two additive synths from Kawai. Additive synths are rare, so
> they're an interesting case study. They came out at different times and the K5's
> shortcomings probably were part of what motivated the K5000's design.

The author cut the balanced thesis and the paired metaphors. The plain category and
the causal guess are the target.

### The factual contrast

Model draft:

> The K5000 is a different architecture, not a K5 with a bigger harmonic count.

Author rewrite:

> They came out at different times and the K5's shortcomings probably were part of
> what motivated the K5000's design.

The author preferred the causal and historical link over the neat contrast. Use a
contrast only when both sides are the point.

### The dropped qualifier

Model draft:

> Harmonic 64 is missing. That is a documented quirk of the K5, not a mistake in
> your patch.

Author rewrite:

> Harmonic 64 is missing for some quirky reason.

The casual phrase is fine. The loss of "documented" is not. Keep the fact and the
casual wrapper.

## Scope

These specifics apply to the author's own docs, including guides and studies about
other instruments. If you are rewriting someone else's text for a different author,
ignore the project-specific slang, the "gal" self-description, and the synth
references. The patterns in `ai-tells.md` still apply.
