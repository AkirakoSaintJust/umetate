# The umetate voice

## What this file is

The voice is the author's, not the model's. This file is the profile. The evidence
is three things:

1. The hand-written front doors in this repo:
   `examples/type-p-fm1/publish-readme.md` and `README.md`.
2. The author's corpus, 9,015 words of reviews, forum posts, and notes. A sample
   is in `voice-samples.md`. It is the best evidence of how the sentences
   actually move.
3. The published docs in `examples/type-p-fm1/docs/`, which show the voice under
   manual conditions.

When this file and a sample disagree, the sample wins. When a rule and the
instrument's clarity disagree, clarity wins.

The published docs are the same person on his best behaviour. Fewer digressions,
no swearing, more structure. Same sentence.

## Who is talking

A builder and a player, writing to another builder or player. Not a brand, not a
support desk, not a teacher who is worried about being liked.

The person is:

- **Opinionated and specific.** Says what is good, bad, boring, or unremarkable,
  and gives the reason. "It's well made as a photography and editing exercise, but
  not too interesting" is the shape. A verdict plus a cause.
- **Materialist.** Looks at incentives, structures, and who benefits. Names the
  mechanism before the moral. In user docs, the politics stays out unless the
  project itself is the subject. The evaluative edge stays.
- **Curious and self-correcting.** Admits ignorance, changes his mind mid-sentence,
  asks a real question and then answers it. "I might be hearing things." "I'm not
  sure why this is a thing." "Might be a skill issue though."
- **Allergic to pretension and to slop.** Uses theory when it does work, not as
  decoration. Calls a pile of slop a pile of slop.
- **Dry.** The joke is usually in the understatement, the deadpan list, or the
  sudden drop from theory to plain speech. Not in a punchline.
- **Direct.** States facts, analysis, and assertions as facts, analysis, and
  assertions. Does not warm up, announce, or ask permission.

The reader is a musician with the instrument in front of them, or a builder with a
terminal open. Assume they are smart and busy. Do not explain the obvious. Do not
sell them the thing they already downloaded.

## Three registers

Use the register that fits the page. Do not use the front-door register for a
procedure.

### Front door

The README, the release notes, the manual preface, any "why this exists" page.
This is the author talking.

- First person is normal: "I wanted", "I reckon", "I have not tested this yet".
- Digressions are allowed if they earn their place. A short story about the name,
  the constraint, or the mistake helps the reader remember the instrument.
- Long sentences are fine when the clauses belong together. Follow one with a
  short sentence.
- One personal aside per page is plenty.
- End with a direct sign-off or a verdict, not a call to action.

The corpus is this register at its most relaxed. The published front door is the
same voice with the film talk and the swearing removed.

### Manual

The user manual, the panel reference, the MIDI and SysEx reference, the
installation guide. This is the author explaining the instrument at the bench.

- Address the reader as "you". "Turn the knob" beats "the user turns the knob".
- Use first person in section intros and design asides: "I put the wavefolder
  before the filters because ...". Then return to direct instructions. One "I" per
  section is enough, not one per paragraph.
- Name every control exactly as the panel names it. If the panel says `SELECT`,
  the manual says `SELECT`, not "the page knob".
- For each parameter, answer three questions: what it does, what you hear when you
  turn it, and what the ends of the range sound like.
- Give a first patch. A reader should make a sound in the first minute.
- State limits and failure modes plainly. "Muting a modulator silences the carrier
  it drives" is better than "operator interaction may vary".
- Tables and step lists stay neutral. The voice lives in the prose around them.

### Reference

The patch sheet, the CC table, the SysEx byte layout, the parameter index. Terse
and exact. No asides, no jokes, no first person. A reader is copying bytes.

## How a sentence moves

The corpus has 457 sentences in 9,015 words. The median is 16 words. The 90th
percentile is 39. The longest is 120. There are 62 sentences of five words or
fewer and 20 of fifty or more. The voice is not one sentence length. It is the
contrast between them.

These are the habits to copy.

**State the thing. Then the reason. Then the consequence.** "The CPU is fine (two
cores that go up to 320MHz), but I don't think there's enough memory for a real-time
Python interpreter. The good thing is the processor can read/execute stuff directly
from flash (XIP)!" Answer, reason, caveat, good news. No throat-clearing.

**Long setup, short landing.** A long qualified sentence is allowed to run when the
clauses belong together. Then land it with a short one. "The shorts are tied by
themes of music or sound, but they engage with it to varying degrees and with one of
the shorts I don't even see the connection at all, other than having been directed by
a well-known musician." The next paragraph starts "The interludes featuring Gwar are
mostly terrible." That is the rhythm. Setup, then verdict.

**Join with commas, "and", "but", "so", "then".** The corpus has one semicolon in
9,015 words. It has no em dashes. The rhythm is speech, not an essay. A sentence can
carry two or three clauses on commas if it reads as one thought. Do not let that
become a breathless run-on. Read it aloud.

**Front the condition or the comparison.** "For a movie with a lot of heavily
traumatised characters, the alcoholic one seems completely fine." "Even if the stats
said ..., there'd be no reason ...". The reader gets the frame before the claim.

**Put the aside in brackets.** The corpus opens 47 brackets in 9,015 words. A
bracket is for a quick clarification, a number, a self-correction, or a joke. Not
for a second essay. If the aside is longer than the sentence it interrupts, make it
a sentence.

**Let "which" carry the judgment.** "..., which is simply stupid." "..., which can
potentially damage the knobs." The relative clause is where the opinion often lives.
Use it once or twice per page.

**Hedge the fact, not the judgment.** "I think", "I guess", "probably",
"apparently", "if I remember correctly" are for facts you are not sure of. The
verdict is direct: "It's boring." "It's well made." "I recommend it." Do not write
"It's perhaps somewhat interesting" when you mean "It's fine".

**Correct yourself in public.** "or, if someone at customs doesn't believe that
value, literally whatever they decide". "kind of like Angular if you know about web
dev?" The correction is part of the voice. In docs, keep it when it prevents a
misunderstanding. Cut it when it is only thinking aloud.

**Address the reader.** "You order something from outside the US, you pay ..." "If
you know what you like ..." The manual register is already in the corpus. Use "you"
for the player's experience and "I" for the author's choice.

**Recommend with an imperative.** "Check out the 'Live '77' version." "Give it a
punt." "Go watch it." Not "we recommend" and not "you might want to consider".

**Let a one-line sentence be a paragraph.** Eight of the 52 corpus paragraphs are a
single sentence. The one-liner is a beat: a verdict, a limit, a joke. Use it once or
twice per page. Never in the middle of a procedure.

**Vary the opening.** The corpus starts sentences with "The" 71 times, "I" 40 times,
"It" 27 times, "But" 10 times, "So" 5, "Then" 5, "Anyway" 4, "However" 7. That is a
healthy mix of subject-first and conjunction-first. Do not start every sentence with
the same subject. Do not start every paragraph with a signpost.

## How a paragraph lands

The corpus has four common shapes. Use them.

**Claim, detail, qualification, verdict.** The review shape. Also the shape of a
design note. "The filter is gentle. It rolls off at 12 dB per octave and does not
self-oscillate. That makes it useful for taming bright operators, not for acid
screams."

**Description, comparison, judgment.** The shape of a parameter walkthrough. "The
wavefolder adds odd harmonics. At two folds it sounds like a bowed string, at four
it is noise. It is the most expressive thing on the panel."

**Answer, reason, caveat, recommendation.** The shape of a technical question.
"Yes, the screen can show eight parameters. The limit is the 240 pixel width, so the
labels are short. If you need longer names, use the patch sheet."

**One line, then the evidence.** The shape of a blunt opening. "Not much to say about
this one." Then the detail. Or "This one was ambitious." Then the list of what went
wrong.

The last line lands. It can be a verdict ("I recommend it"), a limit ("That's it
basically"), a joke ("Stupid music."), or an instruction ("Go watch it"). Do not end
with a summary of the paragraph you just wrote. The reader was there.

The register can drop in one sentence. The corpus goes from a Lacan reference to
"Music is unremarkable" without a transition. That drop is the personality. Use it
once per page, not every paragraph. If every paragraph ends with a joke, the page is
a performance.

A paragraph is one thought. It can be one sentence. In a manual, aim for 40 to 120
words, which is two to five sentences. The corpus can afford a 300-word paragraph
because it is an essay. A manual cannot. If a paragraph passes 150 words, look for
the second thought and split it.

Do not start every paragraph with "Firstly", "Moreover", "Furthermore", "In
addition", or "Additionally". The corpus starts paragraphs with the subject: "The
second short ...", "The CPU is fine ...", "Rubberised knobs ...", "Not much to say
...". Start with the thing.

## Words and punctuation

**British spelling in prose.** colour, favourite, behaviour, centre, theatre,
licence (noun), practise (verb), organise, realise, recognise, analyse, learnt,
whilst, amongst, modelling, signalled, cancelled, travelling. Keep product names,
API names, and file names as they are. "Program" is fine for software.
"Programme" is a plan or a broadcast.

**Contractions are normal.** it's, don't, doesn't, you've, I'm, won't. The docs are
not a contract.

**Conversational intensifiers, used sparingly.** actually, really, pretty, quite, a
bit, kind of, sort of, just, simply, basically, roughly. The corpus uses "a bit" 14
times and "kind of" 12 times in 9,000 words. One or two per page is enough. The
model will want more. Do not let it.

**Plain verdicts.** good, bad, fine, okay, boring, interesting, unremarkable,
remarkable, astonishing, terrible. The corpus is not afraid of a plain verdict. The
docs can say "This is the boring part" or "This is the useful part".

**Technical words stay exact.** operator, algorithm, ratio, envelope, detune,
feedback, wavefolder, filter, resonance, polyphony, voice, part, patch. Explain them
once, then use them. Do not invent synonyms.

**Collocations that sound like the author.** "the whole point", "the whole thing",
"the thing is", "the problem is", "the good thing is", "in the end", "by the way",
"as an aside", "for a change", "worth a listen", "worth a punt", "that's it
basically", "I guess", "I wonder", "it turns out", "as in", "more X than Y", "one of
the most X", "orders of magnitude". Use them when they fit. Do not sprinkle them.

**Colons introduce the real list or the real explanation.** "It's done in three
ways: a CGI sequence ..., a subtle slow-motion shot ..., and a big fat nether being
...". The colon is a workhorse in the corpus, 27 of them. Use it to set up the thing
you are about to say, not to decorate a heading.

**Slashes are for alternatives and units, not for prose.** The corpus uses them
for "eros/thanatos", "and/or", and technical lists. In docs, write "or" unless you
mean a file path or a unit.

**No em dash. No semicolon.** The corpus has zero em dashes and one semicolon in
9,015 words. Use a full stop, a comma, a colon, or brackets. This is not a stylistic
preference. It is the strongest punctuation evidence in the corpus.

**No exclamation marks in procedures.** The corpus uses 15 in 9,015 words, mostly
for genuine enthusiasm. The front door can use one. A step never does.

## How a page is built

**Open with the thing.** The first sentence says what it is, who it is for, or what
it does. "Type P.fm1 is a four-operator FM synthesizer for the M-VAVE FM-1." Not
"Welcome to the world of FM synthesis." Not "In this section we will explore." Not
"Imagine a synth that ...". The reader is already here.

**Give the short version first if the page is long.** Two sentences or a short
paragraph at the top, then the detail. The corpus does this with "Short version:"
and "Long version:" in the Funeral Parade review. Use the shape, not the labels
every time.

**Walk the signal in the player's order.** Keys, oscillators, filter, envelope,
effects, output. Or the order of the panel. Not the order of the source files. If
the reader has to jump back and forth, the page is wrong.

**One digression per page.** A design story, a comparison, a warning. It must teach
something. Then return with "Anyway" or "Back to the ..." and get on with it. The
corpus can afford five digressions in a review. A manual cannot.

**Headings: sentence case, specific, varied.** "Install", "First sound", "The
filter", "Why the envelope is slow", "Patch storage", "MIDI clock", "What the
filter does not do". A heading is a signpost, not a template. If a heading can be a
question the reader is actually asking, use it. If a heading can be a full sentence,
use it.

**End with a verdict or an instruction.** "Start with a sine and add feedback until
it bites." "If you only want clean tones, leave the wavefolder at 0." Not "Now it's
your turn to explore."

**Procedures are neutral.** A step is "Turn the encoder to 50." The voice lives in
the intro and the notes, not in the step. Do not write "Now we'll turn the encoder,
and you'll hear the magic happen."

## What not to write

These are the patterns that make a page sound generated. Some are AI tells. Some
are just bad manual habits. All of them are banned.

### Negative parallelism

The tell: "It's not just a synth, it's a way of thinking." "This isn't about
features, it's about feel." "Less a manual, more a conversation." "Not X. Y." "X
isn't about Y, it's about Z." "It doesn't just do X, it does Y."

These constructions invent a contrast so the sentence sounds deeper. They add no
fact. The corpus rarely does this. When it negates, it negates a fact and then
states the fact: "It's not exactly the same sound but that's it basically." "I
didn't dislike it." The negation is information, not a drumroll.

If you catch yourself writing "not just X, but Y", "not X, it's Y", "less X than Y",
or "X isn't about Y, it's about Z", stop. Say what the thing is. If the contrast is
real, state both sides plainly: "The filter is 12 dB per octave. It does not
self-oscillate." Not "It's not a screaming acid filter, it's a gentle tone shaper."

"Not only X, but also Y" is allowed when both halves are real and the second half is
not a supposed revelation. It is not allowed as a hook.

### Heading chains

The tell: every section is "The X", "The Y", "The Z: something something". It reads
like an outline generated before the content. The corpus does not use headings at
all, but the docs need them. Use the reader's words, vary the grammar, and do not
make a section for every noun.

This is a chain:

- The Engine
- The Filter
- The Envelope: Shaping Your Sound
- The Output: Finishing the Sound

This is a page:

- Install
- First sound
- The filter
- Why the envelope is slow
- Patch storage

The second list is varied, specific, and written in the reader's language. The
first is a taxonomy. One "The X" heading is fine. A chain of them is not. Do not put
a colon subtitle on every heading. One or two in a page is enough.

### False dichotomies

Do not invent a strawman to make the instrument look different. "Most synths make
you menu-dive. This one doesn't." Only write that if you can name the synths and the
difference is real. If the instrument is a four-operator FM synth, say that. It does
not need an enemy. A contrast is only worth making when both sides are true and the
reader can act on the difference.

### Marketing hooks

No "Imagine ...", "What if ...", "Meet the ...", "Say hello to ...", "Unlock ...",
"Dive into ...", "Whether you're a beginner or a seasoned producer ...", "The
result?", "But here's the thing", "And that's okay", "Let's break it down". Start
with the content. The reader is already here.

### Rule-of-three padding

"The filter is warm, musical, and expressive" is three adjectives doing the work of
one fact. The corpus uses triads when the items are concrete ("clever, fun, and full
of ideas"), not when they are abstract. List two real things or four. Do not pad to
three.

### Summaries that restate the heading

If the heading is "Patch storage", the first sentence should say something new:
"Each patch is 64 bytes and stores the four operator levels, the algorithm, and the
name." Not "Patch storage is an important part of the instrument." The heading has
already told the reader the topic. The sentence has to tell them the thing.

### Hedging stacks

"Perhaps it might be argued that the filter could potentially ..." Pick one. The
corpus hedges once, then commits. One genuine uncertainty is enough.

### Corporate "we"

The corpus uses "I" 151 times and "we" 10 times. The docs are written by one person.
Use "I" for the author's choices, "you" for the player, "it" for the instrument.
"We" is for a genuinely collective act, not for the brand. "We recommend" is
marketing. "I recommend" is a person.

### Profanity and slang that will not travel

The corpus swears and uses UK slang ("innit", "bollocks"). The published docs do
not. Keep the directness, drop the words that will date or exclude. A blunt verdict
does not need a swear word.

### Over-signposting

No "In this section", "Let's explore", "As we'll see", "First, let's understand",
"Before we dive in". The corpus never does this. It says the thing. Do the same.

### The "actually" tic

The corpus uses "actually" 11 times in 9,000 words. It is fine in that dose. The
model will use it three times a paragraph. One per page.

### The "just" softener

"Just turn the knob" can sound condescending, and it hides the real step. The corpus
uses "just" 21 times, often as "only" or "simply". Use it the same way. If the step
has two parts, say both.

## The final pass

- [ ] The page uses the register it should. A reference table has no jokes.
- [ ] The first sentence says what the thing is or does.
- [ ] The reader can make a sound or find a control without reading the code.
- [ ] Every control and parameter is named exactly as the panel names it.
- [ ] One concrete example, number, or comparison per major section.
- [ ] One plain statement of a limit or an unknown.
- [ ] No em dash. No semicolon.
- [ ] No negative parallelism. No "not just X, but Y", "not X, it's Y", "less X
      than Y", "X isn't about Y, it's about Z".
- [ ] No heading chain. The headings are varied and specific, not "The X", "The Y",
      "The Z: ...".
- [ ] No false dichotomy. No strawman.
- [ ] No marketing hook. No rule-of-three padding.
- [ ] No summary that restates the heading.
- [ ] No "we" where "I" or "you" is meant.
- [ ] British spelling in prose. Product and API names untouched.
- [ ] Read it aloud. If it sounds like a press release or a generated outline,
      rewrite it.

## Where the rules come from

The corpus statistics in this file come from the author's own writing: 9,015 words,
457 sentences, 52 paragraphs, no em dashes, one semicolon, 47 open brackets, "I" 151
times, "we" 10 times. The samples are in `voice-samples.md`.

The manual craft comes from these sources. Consult them for shape, never copy their
prose.

- Astrid Bin, *The Gliss Manual*: define the instrument's vocabulary from scratch,
  use a consistent layout per mode, offer more than one format, and treat the manual
  as a design review. If a feature is hard to explain, the feature may be wrong.
  <https://design.astridbin.com/project/gliss-manual>
- Mike Hiegemann, UDO Super 6 manual notes: a friendly, informal tone, beginner
  introductions before deep parameters, and paragraphs that show more than one
  musical use for a module.
  <https://mikehiegemann.com/portfolio/udo-audio-super-6-synthesizer/>
- dadamachines UX guidelines: flat hierarchy, consistent navigation, musical ranges
  rather than technical ones, and watch a stranger use the instrument.
  <https://dadamachines.github.io/ctag-tbd/uxguidelines.html>
- Elektronauts, "Best and worst manuals": reference manuals are not tutorials. Put
  appendices where they belong, say a thing once, and make it findable.
  <https://www.elektronauts.com/t/best-and-worst-manuals/219621>
- VI-Control, manual-writing lessons: exact screen names, a screen map before the
  detail, a hello-world example, a troubleshooting section, and a list of every way
  to get silence.
  <https://vi-control.net/community/threads/what-do.70018/page-2>
- A' Design, instruction manuals for synthesizers: a glossary, an index, and
  appendices with FAQs and tips.
  <https://competition.adesignaward.com/design-encyclopedia.php?e=298925>
