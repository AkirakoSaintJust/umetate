---
name: umetate-humanizer
description: Rewrite prose in the author's voice, extracted from the Type P.fm1 manual and the K5/K5000 guide. Use when text sounds like a spec sheet, a chatbot, or marketing copy, when a draft needs the author's rhythm and causal links, or when editing a Markdown file in place. Covers the negation test, the connectivity pass, the aphorism ban, the "A, not B" ban, the manual and guide registers, and the no-information-loss check. Pure Markdown, no dependencies, no network calls.
version: 1.0.0
license: GPL-3.0-only
allowed-tools: read, grep, glob, edit, write, shell
---

# umetate humanizer

This is the author's voice method. It comes from the hand-written Type P.fm1
manual and the K5/K5000 guide rewrite. It is not a generic AI-tell filter. The
target is a specific builder and player talking to another builder or player.

The method has four jobs: keep the facts, choose the right register, join the
clauses, and cut the lines that sound like a poster. Everything else follows from
those.

## The target voice

A builder and a player, writing to another builder or player. First person, normal
contractions, dry asides, technical exactness, light UK slang. Long setup and short
landing. The instrument can be the actor. A manual can open with a design note in
the front-door register, then settle into the reference voice. A guide can open
with the plain category and a causal link, then carry longer explanatory
sentences. Do not flatten either one into a spec sheet.

The author is opinionated and specific. They say what is good, bad, boring, or
unremarkable, and give the reason. They admit a limit, a failed experiment, or a
change of mind. They use "I" when the judgement is theirs. They use "you" for the
reader. They let the instrument be the subject when no person is acting.

## The six rules

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

The hand-written manual is 1,899 words: mean sentence 15.6, median 13, standard
deviation 12.1, 22 first-person pronouns, 33 contractions, 7 brackets, 4
exclamation marks. The current Type P.fm1 manual appends the panel section, so the
file is longer. The hand-written part remains the calibration.

The K5/K5000 guide's first 70 lines are 737 words in 41 sentences: mean 17.6,
median 14, standard deviation 16.7, longest 80. The first-person count stayed at
three. The change was explanatory length and connective looseness, not
self-reference.

Do not add "I" to compensate for a flat draft. Add explanatory clauses,
connectives, and a longer sentence where the thought needs it. A manual with two
first-person pronouns and one contraction in 1,000 words has been over-edited.

## The negation test

A negation earns its place only when it carries one of these:

- a causal link,
- a factual comparison,
- an explanation of something potentially counterintuitive,
- a real scope or limit,
- a correction of a specific misconception.

If it carries none of those, cut it. It is a debate move with no information.

Do not write "A, not B" as an adversative. "single precision, not double", "whole
waveforms, not partials", and "the framework, not the glue" read like a spec
sheet. Use "rather than", a separate sentence, or a "but" clause. Keep the
comma-not form only when the second half is a precise factual limit and the
sentence would be clumsy without it, and even then prefer "rather than".

A conversational correction can keep the negative. "But that doesn't mean one is
necessarily better than the other! They've just got different personalities." The
negation carries a correction, and "just" scales it. "That is just a tour-rig
claim, though, with no album credits to back it up" does the same with a limit.
The target is the theatrical label contrast, not every negative sentence.

The tell: "It's not just a synth, it's a way of thinking." "This isn't about
features, it's about feel." "Less a manual, more a conversation." "Not X. Y." If
the contrast is real, state both sides plainly: "The filter is 12 dB per octave.
It does not self-oscillate."

## Connectivity

Join a fact to its cause, condition, or specification. The model draft wrote
"Each additive source holds 64 harmonics. Low is 1 to 64. High is 65 to 128." The
author wrote "Each additive source holds 64 harmonics, with two possible settings:
Low is 1 to 64, and High is 65 to 128."

- Attach a fact or an explanation with a relative clause: "Harmonic 64 is missing,
  which is a documented quirk of the instrument."
- Attach a specification with "with" and a colon.
- Attach a condition with "only when".
- Use a colon for a list that follows.
- Use a parenthesis for a source pointer.
- Join a cause to its consequence with "so" or "because" when the link is real.
- Let a recommendation explain itself: "Its restrictions are instructive, so it is
  the synth to learn additive synthesis on."

Do not split a connected explanation into three declaratives. A page of short
sentences has lost the guide register even when every fact is right.

## Aphorisms and endings

An aphorism is a short, universal-sounding verdict that could go on a poster. It
flatters the writer and adds no information. Cut "Its restrictions are the
lesson", "Two sources with clear jobs beat six sources with vague ones", "They are
instruments for composing the inside of a sound", "The K5 teaches you to think
spectrally", "The filter is useful, and it is also a trap", and "Hybridisation is
musically intelligent."

The quasi-aphorism is the same move with a concrete noun. "Its restrictions are the
lesson" sounds like a design principle, but it does not say which restrictions or
what they teach. Replace it with the concrete reason: "Its two sources and four
envelopes are enough to learn how harmonic groups move."

A specific verdict is allowed: "The K5000W is the least immediate additive
instrument of the three." A slogan is not: "The K5000 is a way of thinking."

A concrete detail can end a paragraph. The author cut "That is the K5 in its
natural habitat: a professional tool under deadline." after the Jan Hammer detail.
A closing verdict that restates the paragraph is filler.

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
7. **Check the surface.** No em dashes, no semicolons, British spelling in prose
   except "synthesizer", panel names exact.
8. **Audit for information loss and invention.** Compare the rewrite with the
   source paragraph by paragraph. Put back anything that went missing.
9. **Read it aloud.** If it sounds like a press release or a generated outline,
   rewrite it.
10. **Self-audit.** Ask what still sounds AI. Answer in two or three bullets, then
    fix exactly those. The checklist catches the rest.

## Modes

- **`detect`:** report the tells and the voice gaps. No rewrite.
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

## Final check

- Every fact from the source is present, or deliberately scoped out with a reason.
- No fact was invented.
- The register is right.
- No em dash, no semicolon in prose.
- Panel names and parameter names are exact.
- The prose has contractions, first person in the right places, and a visible
  sentence-length variance.
- The author's slang, asides, and self-description survive.
- The clauses are joined where they belong together.
- No aphorism and no summary verdict.
- No "A, not B" adversative.
- No negative parallelism, heading chain, false dichotomy, or marketing hook.
- No product self-description section, no `The... The...` list, and no wh-word heading
  or table label.
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
