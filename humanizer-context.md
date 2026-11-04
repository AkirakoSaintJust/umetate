# umetate voice context

This file is auto-loaded by the humanizer skill. It overrides the generic defaults
for umetate prose. Read it before rewriting a manual, a README, release notes, or a
panel reference.

The hand-written manual is `examples/type-p-fm1/docs/manual.md`. The author rewrote
it after the first release. That rewrite is the target, not the earlier, flatter
version.

## The voice in one paragraph

A builder and a player talking to another builder or player. First person, normal
contractions, dry asides, technical exactness, light UK slang. Long setup and short
landing. The instrument can be the actor. The manual can open with a design note in
the front-door register, then settle into the reference voice. Do not flatten it
into a spec sheet.

## Calibration

The first manual was 971 words: mean sentence 11.3, median 10, standard deviation
6.4, 2 first-person pronouns, 1 contraction. It read like a contract.

The hand rewrite is 1,899 words: mean sentence 15.6, median 13, standard deviation
12.1, 22 first-person pronouns, 33 contractions, 7 brackets, 4 exclamation marks.
The longest sentence is 66 words. The shortest fragment is one word.

If a rewrite produces numbers near the first set, it has over-edited.

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

## Fix these

- **Possessive grammar.** "both parts's algorithms" becomes "both parts'
  algorithms".
- **Comma splices only when the reader has to backtrack.** A 66-word sentence can
  stay if it reads as one thought.
- **Repeated "so" and "kinda" only when they crowd a paragraph.** Do not ban them
  outright.
- **Hyphenation.** "phase-modulation synthesizer" is a compound modifier. "phase
  modulation" is the noun. Both are correct.

## Hard bans

- No em dash. No semicolon.
- No swearing.
- No marketing hooks, negative-parallelism hooks, false dichotomies, or heading
  chains.
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

## Scope

These specifics apply to umetate. If you are rewriting something else, ignore the
slang, the "gal" self-description, and the synth references. The generic 55 patterns
still apply.
