---
name: umetate-humanizer
description: Rewrite prose in the author's voice, extracted from the Type P.fm1 manual, the K5/K5000 guide, and the hand-written README. Use when text sounds like a spec sheet, a chatbot, or marketing copy, when a draft needs the author's rhythm and causal links, or when editing a Markdown file in place. Covers the negation test, the connectivity pass, the aphorism ban, the "A, not B" ban, the project vocabulary bans (claim, source of truth, I built, dogfood, lives in, gap), the manual and guide registers, the anti-slop promise, and the no-information-loss check. Pure Markdown, no dependencies, no network calls.
version: 1.2.0
license: GPL-3.0-only
allowed-tools: read, grep, glob, edit, write, shell
---

# umetate humanizer

This is the voice method I use on my own docs, and it comes from the hand-written
Type P.fm1 manual and the K5/K5000 guide rewrite. It isn't a generic AI-tell
filter, because the target is narrower than that: a specific builder and player
talking to another builder or player, with the same dry asides and the same
impatience for a poster line.

The method has four jobs, and everything else follows from them: keep the facts,
choose the right register, join the clauses that belong together, and cut the
lines that sound like a poster. I'd read the rest of this file with those four
jobs in mind, because a rule that doesn't serve one of them is probably just
decoration.

## Target voice

The target is a builder and a player, writing to another builder or player, with
first person, normal contractions, dry asides, technical exactness, and light UK
slang. I like a long setup and a short landing, and I'm happy for the instrument to
be the actor when no person is doing anything. A manual can open with a design note
in the front-door register, then settle into the reference voice, whilst a guide
can open with the plain category and a causal link and carry longer explanatory
sentences later. Do not flatten either one into a spec sheet, because the flattening
is the failure mode this whole file is trying to prevent.

I'm opinionated and specific, and I'd rather say what is good, bad, boring, or
unremarkable and give the reason than hedge around it. I'll admit a limit, a failed
experiment, or a change of mind when the evidence says so, which is why "I" belongs
on the judgement and "you" belongs on the reader's experience. The instrument can
take the subject when no person is acting, and that's usually the clearer sentence.

I'm also chummy, nerdy, and British, and the front door can carry a dry aside, a
self-deprecating admission, or a direct request to the reader. The hand-written
README says the prose "might sound a bit chummy, nerdy and British", then asks the
reader to write their own release front door "because I'm going to feel guilty and
embarrassed if you use umetate to make something and publish it with awful slop
marketing blurb docs." That's the register I want: warm, direct, a bit embarrassed
about asking, and completely serious about the anti-slop promise. Keep the aside
when it carries a reason or a real care for the reader, and cut it when it turns
into a slogan.

## Six rules

1. **Synchronic, not historical.** Describe the instrument as it is now. Release
   notes are the exception. A guide or study can use history as its subject.
2. **From the instrument, not the code.** The reader sees a knob and hears a sound.
   Say what the knob does and what the sound does. Keep the panel's names.
3. **The author's voice, not the model's.** When two wordings are correct, pick the
   one the author would write. The reference samples are the hand-written manual
   and the K5/K5000 guide.
4. **No information loss and no invention.** A rewrite can cut, sharpen, and
   reorder. It cannot drop a fact. It cannot add a model, date, number, or quote.
5. **No em dashes, no semicolons.** Rewrite around them. Code blocks are the only
   exception.
6. **Radical rewrites are fine.** The goal is prose quality, not a minimal diff. A
   clean page that reads like a spec sheet is a failed rewrite.

## Project vocabulary bans

These words carry a model's default framing, and each one hides a simpler fact
underneath. Use the substitute or rewrite the sentence, because a hard ban in prose
is not a preference you can skip when the sentence feels awkward.

| Do not write | Write instead |
| --- | --- |
| claim, as a label for a feature | claimed feature, or name the feature |
| source of truth | only reference, single reference |
| I built, we built | I made, we made |
| dogfood | test project made from our own readymade components, or the worked example |
| lives in, live in, for a file, folder, sub-project, document, or component | is in the PATH folder, is stored at, PATH's path within the repo is |
| gap, for missing work | missing work, missing feature, bug, oversight, problem |

A bare "claim" is a debate word, so "the status of each claim" becomes "the status
of each claimed feature", which says what the thing is without turning it into a
courtroom. Keep "claim" as a verb when someone is claiming a fact and the evidence
matters, and keep it in a licence or warranty, but don't use it as a label for a
feature.

"Source of truth" is a status word borrowed from software management, and it sounds
more grand than the thing it describes. This repo has one reference for status,
`docs/roadmap.md`, so write "the only reference" or "the single reference" and let
the fact do the work.

"I built" is the model's construction metaphor, and it tends to turn a piece of
writing into a building project. I made the thing, so use "I made", "we made", or
"the example I made", and keep "built" for a compiled binary, a target package, or a
CI job, where the literal build is the subject.

"Dogfood" is insider jargon that hides who did what, and it always sounds like a
private joke rather than a description. Write "the test project made from our own
readymade components" on first use, then shorten it to "the test project" or "the
worked example" once the reader knows what you mean. If a build command or a
historical identifier uses the word, keep the literal token and explain it in plain
words around it.

A file, folder, sub-project, document, or component doesn't "live" anywhere, and
saying it does makes a path sound like a habitat. It is in a folder, it is stored at
a path, or its path within the repo is the path. "The plugin source lives in
`plugin/`" becomes "The plugin source is in the `plugin/` folder", and "The modules
live in `modules/nodes/`" becomes "The modules are stored at `modules/nodes/`."

"Gap" is a planning word that hides the concrete failure, and a plan full of gaps
is harder to act on than a list of jobs. Name the missing work, the missing feature,
the bug, the oversight, or the problem, so "the next gaps" becomes "the next missing
items" or "the open questions". Keep "gap" for a physical space, a grid gap, a
silent gap in audio, or a measured interval.

These bans apply to prose, so a code identifier, a command, a schema key, or a
quoted source keeps its spelling even when the word is on the list.

## Registers

- **Front door:** README, release notes, manual preface. The author is present, in
  first person, with a specific story, a concrete comparison, and a plain
  statement of what the instrument is. Contractions and asides belong here.
- **Manual:** the manual, panel section, MIDI reference, and install guide. Warm
  technical prose. Address the reader as "you". Use first person in section intros
  and design asides. Keep procedures neutral.
- **Guide or study:** a document about an existing instrument, a lineage, or a
  design question. The reader may not own the hardware. History and longer
  explanatory sentences are allowed.
- **Reference:** the patch sheet and byte-level tables. Terse and exact. No
  asides, no jokes, no first person.

## Calibration

The hand-written manual is 1,899 words, with a mean sentence of 15.6 words, a
median of 13, a standard deviation of 12.1, 22 first-person pronouns, 33
contractions, 7 brackets, and 4 exclamation marks. The current Type P.fm1 manual
appends the panel section, so the file is longer, but the hand-written part remains
the calibration and I'd keep coming back to it.

The K5/K5000 guide's first 70 lines are 737 words in 41 sentences, with a mean of
17.6, a median of 14, a standard deviation of 16.7, and a longest sentence of 80
words. The first-person count stayed at three, because the change was explanatory
length and connective looseness rather than self-reference, and that's the lesson
I'd take into a guide.

Don't add "I" to compensate for a flat draft. Add explanatory clauses, connectives,
and a longer sentence where the thought needs one, because a manual with two
first-person pronouns and one contraction in 1,000 words has been over-edited.

## Negation test

A negation earns its place only when it carries one of these:

- a causal link,
- a factual comparison,
- an explanation of something potentially counterintuitive,
- a real scope or limit,
- a correction of a specific misconception.

If it carries none of those, cut it, because it is a debate move with no
information in it.

Don't write "A, not B" as an adversative. "single precision, not double", "whole
waveforms, not partials", and "the framework, not the glue" read like a spec sheet,
and the contrast is usually doing less work than the writer thinks. Use "rather
than", a separate sentence, or a "but" clause, and keep the comma-not form only when
the second half is a precise factual limit and the sentence would be clumsy without
it. Even then, I'd prefer "rather than".

A conversational correction can keep the negative. "But that doesn't mean one is
necessarily better than the other! They've just got different personalities." The
negation carries a correction, and "just" scales it, whilst "That is just a tour-rig
claim, though, with no album credits to back it up" does the same with a limit. The
target is the theatrical label contrast, not every negative sentence, so don't go
through a draft with a red pen and remove every "not" you see.

The tell is easy to spot once you know it: "It's not just a synth, it's a way of
thinking", "This isn't about features, it's about feel", "Less a manual, more a
conversation", "Not X. Y." If the contrast is real, state both sides plainly and
stop: "The filter is 12 dB per octave. It does not self-oscillate."

## Connectivity

Join a fact to its cause, condition, or specification, because a page of separate
declaratives makes the reader do the joining. The model draft wrote "Each additive
source holds 64 harmonics. Low is 1 to 64. High is 65 to 128", and the author wrote
"Each additive source holds 64 harmonics, with two possible settings: Low is 1 to
64, and High is 65 to 128."

- Attach a fact or an explanation with a relative clause: "Harmonic 64 is missing,
  which is a documented quirk of the instrument."
- Attach a specification with "with" and a colon.
- Attach a condition with "only when".
- Use a colon for a list that follows.
- Use a parenthesis for a source pointer.
- Join a cause to its consequence with "so" or "because" when the link is real.
- Let a recommendation explain itself: "Its restrictions are instructive, so it is
  the synth to learn additive synthesis on."

Don't split a connected explanation into three declaratives, because a page of
short sentences has lost the guide register even when every fact is right. The
reader can feel the difference before they can name it.

## Commit bodies and code comments

A good commit body states the current constraint, the change, and the reason, and
then gets out of the way. The envelope refactor is the shape:

> The attack target was hardcoded at -12 dB. Make it a module constant next to the
> decay target, so an experiment can render other match points without touching the
> shipped value. The default stays -12 dB.

Three sentences do the whole job: what was fixed, what changed, why, and what
stayed. There's no "refactored the codebase" and no "improved maintainability",
because neither one tells the next reader anything. Name the constant, the file, or
the behaviour, and give a code comment the same treatment by naming the trade-off:

> Envelope match points. The attack aims at -12 dB below full. The decay aims 12 dB
> into the trip, which keeps the early body and the tail in the same region. A
> larger drop shortens the tail at the cost of a faster first few dB.

## Aphorisms and endings

An aphorism is a short, universal-sounding verdict that could go on a poster, and
it flatters the writer whilst adding no information. Cut "Its restrictions are the
lesson", "Two sources with clear jobs beat six sources with vague ones", "They are
instruments for composing the inside of a sound", "The K5 teaches you to think
spectrally", "The filter is useful, and it is also a trap", and "Hybridisation is
musically intelligent."

The quasi-aphorism is the same move with a concrete noun. "Its restrictions are the
lesson" sounds like a design principle, but it doesn't say which restrictions or
what they teach, so replace it with the concrete reason: "Its two sources and four
envelopes are enough to learn how harmonic groups move."

A specific verdict is allowed, so "The K5000W is the least immediate additive
instrument of the three" is fine. A slogan is not: "The K5000 is a way of thinking."
A concrete detail can end a paragraph without a closing verdict, which is why the
author cut "That is the K5 in its natural habitat: a professional tool under
deadline" after the Jan Hammer detail. The detail already carried the point, and a
closing verdict that restates the paragraph is filler.

## Preserve

- **Self-description.** "I'm more of a sound design gal." Keep "gal".
- **Light UK slang and internet asides.** "innit", "kinda", "gal", "whatever",
  "aka", "i.e.", "terminally online". A few per page. Never in a step, a warning,
  or a reference table.
- **In-group references that are factual.** DX/OPwhatever, OPL3, TX81z/D11/V50,
  ymfm, Dexed, DX21/DX7.
- **Concrete patch tips.** The feedback recipes, ratio ranges, reverse-saw recipe,
  and wavefolder swell are content.
- **Self-corrections and calibrated hedges.** "What I mean is", "I think", "kinda",
  "I've got to say". They are voice, not leftover hedge debris.
- **The instrument as actor.** "The filter removes", "the envelope holds".
- **Concrete triads and tip lists.** Three real settings are content.
- **The plain category opening.** "The K5 and K5000 are two additive synths from
  Kawai. Additive synths are rare, so they're an interesting case study."
- **The causal guess.** "The K5's shortcomings probably were part of what motivated
  the K5000's design." "Probably" is the right hedge for an inference.
- **The explanatory long sentence.** Keep an 80-word sentence when it reads as one
  thought. Split it only when the reader has to backtrack.
- **The connectivity join.** "Each additive source holds 64 harmonics, with two
  possible settings: Low is 1 to 64, and High is 65 to 128."
- **"In order to", "whilst", "has got", "sort of", "and so on", "a bunch of",
  "probably", "(!)".** These are voice in explanatory prose.
- **Factual "rather than just" contrasts.** "A complete voice path, rather than
  just the oscillator" names both sides.
- **A spoken correction.** "That is just a tour-rig claim, though, with no album
  credits to back it up." The negation carries a limit.
- **A slash in a scope label.** "anecdotal/historical records" is a category label.
- **A parenthetical source pointer.** "(see sources at the end)."

## Cut

- **Marketing adjectives.** "seamless", "robust", "state of the art", "unleash",
  "vibrant", "cutting-edge", "world-class".
- **Status shorthand.** "source of truth" becomes "only reference" or "single
  reference". A bare "claim" becomes "claimed feature" or the feature's name.
- **Construction metaphors.** "I built" becomes "I made" unless the subject is a
  compiled binary or a CI job.
- **Insider jargon.** "dogfood" becomes "test project made from our own readymade
  components", then "the test project" or "the worked example".
- **Location verbs.** A file, folder, sub-project, document, or component does not
  "live in" a place. It is in a folder, it is stored at a path, or its path within
  the repo is the path.
- **Planning words that hide the failure.** "Gap" for missing work becomes the
  missing work, the missing feature, the bug, the oversight, or the problem.
- **Significance inflation.** "stands as", "is a testament to", "pivotal moment",
  "underscores the importance", "evolving landscape".
- **Vague attributions.** "experts argue", "research suggests", "industry reports",
  "it is widely believed".
- **Superficial -ing clauses.** "highlighting", "underscoring", "ensuring",
  "reflecting", "showcasing".
- **Negative parallelism.** "not just X, but Y", "not X, it's Y", "less X than Y".
- **Aphorisms and summary verdicts.**
- **Meta-commentary.** "This is the detail most online summaries get wrong."
- **Product self-description.** A standalone "what this is" section in the
  product's own interface. The reader is already looking at the thing. Cut it or
  replace it with the next action, the controls, or a real limit.
- **"The... The..." lists.** A list where every item starts with the same article.
  Drop the article, lead with the noun or verb, or write the list as prose.
- **Wh-word headings and labels.** "What to reach for first", "How to move",
  "What it does". Use a noun phrase or an imperative.
- **Counted couplets.** A heading, caption, or table description built as two
  counts: "One page, one job", "Two sources, one filter", "One phase, many
  amplitudes". It sells a shape instead of naming the section. Use a noun phrase
  or an imperative, and put the count in the body.
- **Storage-value leakage.** A user document gives the raw firmware value
  (`65536`, `32767`) instead of the on-screen value. Show the panel range next to
  the name.
- **Heading chains.** "The Engine", "The Filter", "The Envelope: Shaping Your
  Sound" for every section.
- **False dichotomies.** "Most synths make you menu-dive. This one doesn't."
- **Rule-of-three padding.** Three abstract nouns doing the work of one fact.
- **Hedging stacks.** "Perhaps it might be argued that the filter could possibly..."
- **Filler.** "in order to" when "To" is shorter, "it is worth noting", "in the
  context of", "utilize".
- **Summary sentences that restate the heading.**
- **"In this section" openings.**
- **Corporate "we".** Use "I" for the author and "you" for the reader.
- **The "actually" tic.** Cut it unless it corrects a real misconception.
- **Uniform sentence length.** Vary it on purpose.
- **Dropped qualifiers.** If a casual phrase loses "documented", put the fact back.

## Workflow

1. **Read the source and name the facts.** List the concrete claims, numbers,
   names, limits, and quotations. This is the no-information-loss baseline.
2. **Choose the register.** Front door, manual, guide/study, or reference.
3. **Rewrite the paragraph as one thought.** Join the clauses that belong together.
   Keep the short sentence for the landing.
4. **Apply the negation test.** Cut every negation that carries no cause,
   comparison, counterintuitive explanation, limit, or correction. Replace "A, not
   B" with "rather than", a separate sentence, or a "but" clause.
5. **Apply the connectivity pass.** Attach facts, specifications, and conditions to
   their main clauses. Do not split a connected explanation.
6. **Cut the aphorisms and summary verdicts.** End on a fact, an instruction, or a
   specific judgement.
7. **Check the surface and the vocabulary.** No em dashes, no semicolons, British
   spelling in prose except "synthesizer", panel names exact. No bare claim, no
   source-of-truth shorthand, no "I built" for a made thing, no dogfood, no "lives
   in" for a location, and no "gap" for missing work.
8. **Audit for information loss and invention.** Compare the rewrite with the
   source paragraph by paragraph. Put back anything that went missing.
9. **Read it aloud.** If it sounds like a press release or a generated outline,
   rewrite it.
10. **Self-audit.** Ask what still sounds AI. Answer in two or three bullets, then
    fix exactly those. The checklist catches the rest.

## Modes

- **`detect`:** report the tells and the weak spots. No rewrite.
- **`rewrite`:** full rewrite. Default.
- **`edit`:** targeted changes in a file. Preserve the author's existing voice.

Useful flags:

- `--file path`: read the source file.
- `--register front-door|manual|guide|reference`: choose the register.
- `--score`: report a 0-100 voice score.
- `--ignore-code`: mask fenced code blocks before detection and editing.
- `--ignore-quotes`: mask block quotes and quoted samples.

Read `references/voice.md` for the full project voice data: the preservation list,
the fixes, the hard bans, and the before and after samples.

## References

- `references/voice.md`: the full project voice data, preservation list, fixes,
  hard bans, and before and after samples.
- `references/ai-tells.md`: the reviewed pattern reference, false positives, detect
  report, and edit safety.
- `references/always-on.md`: short standing-instruction blocks for `AGENTS.md`,
  system prompts, and umetate docs.

## AI-tell checklist

| Tell | Fix |
| --- | --- |
| Bare claim for a feature | Write "claimed feature" or name the feature. |
| "Source of truth" | Write "only reference" or "single reference". |
| "I built" for a made thing | Write "I made". Keep "built" for a compiled binary or a CI job. |
| "Dogfood" | Write "test project made from our own readymade components", then "the test project". |
| "Lives in" for a file, folder, sub-project, document, or component | Write "is in the PATH folder", "is stored at", or "PATH's path within the repo is". |
| "Gap" for missing work | Name the missing work, the missing feature, the bug, the oversight, or the problem. |
| Commit body with no constraint or reason | State what was fixed, what changed, why, and what stayed. |
| Significance inflation | State what the thing is or does. Cut the "represents" commentary. |
| Promotional adjectives | Replace with a specific fact, setting, or sound. |
| Vague attribution | Name the source and what it said, or cut the claim. |
| Superficial -ing clause | Delete it or promote its information into a sourced sentence. |
| Negative parallelism | State the positive, the cause, or the comparison. |
| "A, not B" adversative | Use "rather than", a separate sentence, or a "but" clause. |
| Aphorism | Replace with the concrete reason, instruction, or specific judgement. |
| Meta-commentary | State the fact and let it stand. |
| Product self-description | Cut the section. Use the space for the next action, the controls, or a real limit. |
| "The... The..." list | Drop the article, lead with the noun or verb, or write prose. |
| Wh-word heading or table label | Use a noun phrase or an imperative. |
| Counted-couplet heading, caption, or table description | Name the section and put the count in the body. |
| Storage-value leakage | Show the panel value and range, not the raw number. |
| Heading chain | Vary the grammar and use the reader's words. |
| False dichotomy | Name the real difference or cut the contrast. |
| Rule-of-three padding | List the real items. Two or four is fine. |
| Hedging stack | Pick one hedge, then commit. |
| Filler transition | Start with the content. |
| Summary verdict | End on the concrete detail. |
| "In this section" | Say the thing. |
| Em dash or semicolon | Rewrite around it. |
| Uniform sentence length | Let a short sentence land next to a long one. |
| Dropped qualifier | Put the documented fact back. |

The reviewed pattern reference is `references/ai-tells.md`. It adds the deeper
trigger lists, the false positives, the detect report, and the edit safety rules.

## Before and after

The plain category:

> The K5 and K5000 are two additive synths from Kawai. Additive synths are rare, so
> they're an interesting case study. They came out at different times and the K5's
> shortcomings probably were part of what motivated the K5000's design.

The balanced thesis and the paired metaphors are gone. The plain category and the
causal guess are the target.

The negation:

> The interesting part is not the list. It is how each harmonic can evolve.

becomes:

> The interesting part for sound design is how each harmonic can evolve throughout
> the sound.

The connectivity:

> Each additive source holds 64 harmonics. Low is 1 to 64. High is 65 to 128.

becomes:

> Each additive source holds 64 harmonics, with two possible settings: Low is 1 to
> 64, and High is 65 to 128.

The aphorism:

> Its restrictions are the lesson.

becomes:

> Its two sources and four envelopes are enough to learn how harmonic groups move.

The "A, not B" adversative:

> The hardware supports single precision, not double.

becomes:

> The hardware supports single precision only, so keep double out of the DSP.

The conversational correction:

> The K5000 is more polished, but it can sound clinical. That is a difference in
> personality, not a ranking.

becomes:

> The K5000 is more polished, but it can sound clinical unless you use its
> envelopes, modulation and resonance with intent.

The cut summary verdict:

> When ideas did not come, he would stop watching the screen and experiment until a
> new sound appeared. That is the K5 in its natural habitat: a professional tool
> under deadline.

becomes:

> When ideas did not come, he would stop watching the screen and experiment until a
> new sound appeared.

### Project vocabulary

Before:

> `docs/roadmap.md` is the source of truth for the status of each claim. The dogfood
> firmware lives in `examples/type-p-fm1`, and I built it to expose the next gaps.

After:

> `docs/roadmap.md` is the only reference for the status of each claimed feature. The
> test project made from our own readymade components is in the
> `examples/type-p-fm1` folder, and I made it to expose the next missing work.

The facts are the same. The status shorthand, the insider jargon, the construction
metaphor, the location verb, and the planning word are gone.

### Anti-slop promise

The front door can say why the docs matter. The hand-written README does:

> I've tried to calibrate the resulting prose from my own personal writing, which
> might sound a bit chummy, nerdy and British. If that's not your thing I appreciate
> your position, but I'm going to feel guilty and embarrassed if you use umetate to
> make something and publish it with awful slop marketing blurb docs. Please take
> care of the community.

Keep that register. It is an aside with a reason, a real stake, and a direct request.
Do not turn it into "we are passionate about empowering creators to unlock their
sonic journey". The author would rather admit the embarrassment than sell the
feeling.

## Final check

- Every fact from the source is present, or deliberately scoped out with a reason.
- No fact was invented.
- The register is right.
- No em dash, no semicolon in prose.
- Panel names and parameter names are exact.
- The prose has contractions, first person in the right places, and a visible
  sentence-length variance.
- Author's slang, asides, and self-description survive.
- Clauses are joined where they belong together.
- No aphorism and no summary verdict.
- No "A, not B" adversative.
- No negative parallelism, heading chain, false dichotomy, or marketing hook.
- No product self-description section, no `The... The...` list, no wh-word heading
  or table label, and no counted-couplet heading, caption, or table description.
- No raw storage value in a user document. Show the panel value and range.
- No bare claim for a feature, no "source of truth", no "I built" for a made thing,
  no dogfood, no "lives in" for a location, and no "gap" for missing work.
- A last grep for the six banned words finds no prose use.
- The front-door asides carry a reason or a real stake. They are not slogans.
- A commit body names the constraint, the change, the reason, and what stayed.
- Read it aloud. If it sounds like a press release, rewrite it.

## Score

Use the score as a signal, not a verdict. A model grading its own output inflates
the result.

| Range | Meaning |
| --- | --- |
| 0-20 | Reads like the author. |
| 21-40 | A few flat or generic lines. |
| 41-60 | Half rewritten, still spec-sheet shaped. |
| 61-80 | Chatbot or corporate voice with some facts. |
| 81-100 | Pure slop. Start again. |

Count the tells, the missing joins, the aphorisms, and the flat sentence runs.
Do not score a sample under 40 words.
