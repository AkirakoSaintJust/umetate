# The umetate voice

## Purpose

The voice is the author's, not the model's. This file is the profile. The evidence
is four things:

1. The hand-written front doors in this repo:
   `examples/type-p-fm1/publish-readme.md` and `README.md`.
2. The author's corpus, 9,015 words of reviews, forum posts, and notes. A sample
   is in `voice-samples.md`. It is the best evidence of how the sentences
   actually move.
3. The hand-written manual in `examples/type-p-fm1/docs/manual.md`, rewritten by
   the author after the first release. It is the target for manual voice.
4. The earlier published docs, kept as a contrast. They are flatter than the
   author sounds.

When this file and a sample disagree, the sample wins. When a rule and the
instrument's clarity disagree, clarity wins.

The published docs are the same person at the bench. Fewer film references, no
swearing, more structure. The hand rewrite kept the digressions, the slang, and
the jokes, and doubled the first-person count and the contractions. That is the
target. Do not flatten it back.

## Manual calibration

The first manual was 971 words: 82 sentences, an 11.3-word mean, a 10-word median,
a 6.4-word standard deviation, 2 first-person pronouns, and 1 contraction. It read
like a spec sheet.

The author's hand rewrite is 1,899 words: 119 sentences, a 15.6-word mean, a
13-word median, a 12.1-word standard deviation, 22 first-person pronouns, 33
contractions, 7 brackets, and 4 exclamation marks. The longest sentence is 66
words. The shortest fragment is one word.

The rewrite is the calibration. A manual with a 10-word median and almost no
contractions has been over-edited.

## Guide calibration

The K5/K5000 guide was written in two passes. The first 70 lines of the model draft
were 689 words: 58 sentences, an 11.6-word mean, a 9.5-word median, an 8.5-word
standard deviation, and a 52-word maximum. The author's rewrite was 737 words: 41
sentences, a 17.6-word mean, a 14-word median, a 16.7-word standard deviation, and
an 80-word maximum. The first-person count stayed at three. The contraction count
went from six to eight.

The rewrite is the calibration for a guide or study. It did not add more "I". It
added longer explanatory sentences, "whilst", "sort of", "and so on", "probably",
and a parenthetical "(!)". A humanising pass that produces the first set of numbers
has flattened the guide.

The first 170 lines of the full draft sit at 2,100 words in 147 sentences: a
13.8-word mean, a 12-word median, an 11.0-word standard deviation. The opening is
more connected than the rest. The gap is the thing to close.

The software reconstruction adds a technical-guide register to the same document:
mechanism first, exact numbers, and the reason attached. "A Kawai-style harmonic
source does not need 64 or 128 independent oscillators" is the shape. Use it for
engineering prose that still has to read like the author.

## The narrator

A builder and a player, writing to another builder or player. Not a brand, not a
support desk, not a teacher who is worried about being liked.

The person is:

- **Opinionated and specific.** Says what is good, bad, boring, or unremarkable,
  and gives the reason. "It's well made as a photography and editing exercise, but
  not too interesting" is the shape. A verdict plus a cause.
- **Materialist.** Looks at incentives, structures, and who benefits. Names the
  mechanism before the moral. In user docs, the politics stays out unless the
  project itself is the subject. The evaluative edge stays.
- **Curious and self-correcting.** Admits ignorance, changes their mind
  mid-sentence, asks a real question and then answers it. "I might be hearing
  things." "I'm not sure why this is a thing." "Might be a skill issue though."
- **Allergic to pretension and to slop.** Uses theory when it does work, not as
  decoration. Calls a pile of slop a pile of slop.
- **Dry.** The joke is usually in the understatement, the deadpan list, or the
  sudden drop from theory to plain speech. Not in a punchline.
- **Direct.** States facts, analysis, and assertions as facts, analysis, and
  assertions. Does not warm up, announce, or ask permission.
- **Self-describing.** Calls themselves "a sound design gal" in the manual. Keep
  the author's self-description when it appears. Do not neutralise it to
  "person" or switch it to "guy".

The reader is a musician with the instrument in front of them, or a builder with a
terminal open. Assume they are smart and busy. Do not explain the obvious. Do not
sell them the thing they already downloaded. A guide or study may be for readers
who do not own the instrument. State the audience: "players and sound designers" is
enough.

## Four registers

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
- One or two personal asides in the preface. The hand rewrite has three in the
  opening design note.
- The manual preface can run for several paragraphs: the history, the constraint,
  the things the author wanted to change, and a short numbered list. The hand
  rewrite has seven.
- End with a direct sign-off or a verdict, not a call to action.

The corpus is this register at its most relaxed. The published front door is the
same voice with the film talk and the swearing removed. The hand rewrite shows the
same voice in the manual preface.

### Manual

The user manual, including the panel section, the MIDI and SysEx reference, and
the installation guide. This is the author explaining the instrument at the bench.

- Address the reader as "you". "Turn the knob" beats "the user turns the knob".
- Use first person in section intros and design asides: "I put the wavefolder
  before the filters because ...". Then return to direct instructions. One or two
  "I" per section is enough. The preface can carry many.
- Contractions are normal. The hand rewrite uses 33 in 1,899 words. A manual with
  one contraction reads like a contract.
- Name every control exactly as the panel names it. If the panel says `SELECT`,
  the manual says `SELECT`, not "the page knob".
- For each parameter, answer three questions: what it does, what you hear when you
  turn it, and what the ends of the range sound like.
- Give a first patch. A reader should make a sound in the first minute.
- State limits and failure modes plainly. "Muting a modulator silences the carrier
  it drives" is better than "operator interaction may vary".
- One aside per section, not one per page. The preface can carry two or three.
- Light UK slang and internet asides are allowed in the preface and in one-line
  tips: "innit", "kinda", "gal", "whatever". Never in a procedure, a warning, or a
  reference table.
- Tips can be labelled. Three concrete tips with settings are content, not
  padding.
- The instrument can be the actor: "the filter removes", "the envelope holds".
- A design note paragraph can run to about 150 words. A procedure paragraph stays
  under about 60.
- Tables and step lists stay neutral. Neutral means no jokes, not no contractions.
  The voice lives in the prose around them.

### Guide or study

A document about an existing instrument, a lineage, or a design question. The
reader may not own the hardware. History is allowed, and the analysis is part of
the value.

- Open with the plain category and why it matters: "The K5 and K5000 are two
  additive synths from Kawai. Additive synths are rare, so they're an interesting
  case study."
- A causal or historical link is better than a neat contrast: "They came out at
  different times and the K5's shortcomings probably were part of what motivated
  the K5000's design." "Probably" is the right hedge when the evidence is
  inferential.
- Define a term once when the audience may be new: "Each of these sines is called a
  harmonic."
- Long explanatory sentences are normal. The guide rewrite has an 80-word sentence
  and a 16.7-word standard deviation.
- State the scope and the status of the diagrams: "it isn't a technical manual, so
  the diagrams are purely explanatory rather than factory schematics."
- The audience can be players and sound designers, not only owners.
- Use the product's own names in headings. "Twin Mode and Full Mode" beats "Two
  sources, two modes".

### Reference

The patch sheet, the CC table, the SysEx byte layout, the parameter index. Terse
and exact. No asides, no jokes, no first person. A reader is copying bytes.

## Sentence movement

The corpus has 457 sentences in 9,015 words. The median is 16 words. The 90th
percentile is 39. The longest is 120. There are 62 sentences of five words or
fewer and 20 of fifty or more. The voice is not one sentence length. It is the
contrast between them.

The hand rewrite has 119 sentences in 1,899 words. The mean is 15.6, the median
13, the standard deviation 12.1. The longest is 66 words. The shortest fragment is
one word. The old manual had a 10-word median and a 35-word maximum. That ceiling
was the problem.

The manual does not need to match the corpus's 120-word maximum. It does need the
contrast: a 60-word sentence can sit next to a four-word verdict. A manual where
every sentence is 10 to 15 words has been flattened.

The guide rewrite has a 17.6-word mean, a 14-word median, a 16.7-word standard
deviation, and an 80-word maximum. The first-person count is the same as the model
draft. The change is explanatory length and connective looseness, not
self-reference. Do not split the 80-word sentence just because it is long. Split it
only when the reader has to backtrack.

**Connect the cause to the consequence.** The model draft had "Each additive
source holds 64 harmonics. Low is 1 to 64. High is 65 to 128." The author wrote
"Each additive source holds 64 harmonics, with two possible settings: Low is 1 to
64, and High is 65 to 128." Join a cause, condition, or specification to its main
clause:

- Attach a fact with a relative clause: "Harmonic 64 is missing, which is a
  documented quirk of the instrument."
- Attach a specification with "with" and a colon.
- Connect a condition with "only when": "Use Full Mode only when you have a
  reason."
- Use a colon for a list: "The groups are: all harmonics, odd, even..."
- Use a parenthesis for a source pointer: "(see sources at the end)."
- Let a recommendation explain itself: "Its restrictions are instructive, so it is
  the synth to learn additive synthesis on."

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
carry two or three clauses on commas if it reads as one thought. The hand rewrite
has more comma splices than the old manual. Keep a comma splice when it reads as
one thought. Split it when the reader has to backtrack. Do not turn a long sentence
into three tidy ones just to satisfy a style checker.

**Front the condition or the comparison.** "For a movie with a lot of heavily
traumatised characters, the alcoholic one seems completely fine." "Even if the stats
said ..., there'd be no reason ...". The reader gets the frame before the claim.

**Put the aside in brackets.** The corpus opens 47 brackets in 9,015 words. A
bracket is for a quick clarification, a number, a self-correction, or a joke. Not
for a second essay. If the aside is longer than the sentence it interrupts, make it
a sentence. The hand rewrite opens 7 brackets in 1,899 words, about one per 270
words. The old manual had 2 in 971, which was too few.

**Let "which" carry the judgment.** "..., which is simply stupid." "..., which can
potentially damage the knobs." The relative clause is where the opinion often lives.
Use it once or twice per page.

**Hedge the fact, not the judgment.** "I think", "I guess", "probably",
"apparently", "if I remember correctly" are for facts you are not sure of. The
verdict is direct: "It's boring." "It's well made." "I recommend it." Do not write
"It's perhaps somewhat interesting" when you mean "It's fine". "Kinda", "I think",
and "I believe" can also be voice markers, not just hedges. Keep the ones that
calibrate a real uncertainty. Cut the ones that weaken a claim the author clearly
wants to make.

**Correct yourself in public.** "or, if someone at customs doesn't believe that
value, literally whatever they decide". "kind of like Angular if you know about web
dev?" "What I mean is ..." The correction is part of the voice. In docs, keep it
when it prevents a misunderstanding. Cut it when it is only thinking aloud.

**Address the reader.** "You order something from outside the US, you pay ..." "If
you know what you like ..." The manual register is already in the corpus. Use "you"
for the player's experience and "I" for the author's choice.

**Recommend with an imperative.** "Check out the 'Live '77' version." "Give it a
punt." "Go watch it." Not "we recommend" and not "you might want to consider".
End on a patch recipe or an instruction, not a neat aphorism. The hand rewrite
replaced "the whole of FM in one knob" with "Try looking at the operator
oscilloscopes to check out how the cascading phase modulation progressively warps
each waveform!" The instruction is stronger.

**Let a one-line sentence be a paragraph.** Eight of the 52 corpus paragraphs are a
single sentence. The one-liner is a beat: a verdict, a limit, a joke. Use it once or
twice per page. Never in the middle of a procedure.

**Vary the opening.** The corpus starts sentences with "The" 71 times, "I" 40 times,
"It" 27 times, "But" 10 times, "So" 5, "Then" 5, "Anyway" 4, "However" 7. That is a
healthy mix of subject-first and conjunction-first. Do not start every sentence with
the same subject. Do not start every paragraph with a signpost. The hand rewrite
uses "So" more, often as a real transition. One or two per page is enough.

## Paragraph movement

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

**Design note: claim, history, constraint, list, use case.** The shape of the manual
preface. "I'm a hardcore fan ... That's where Type P.fm1 comes from." Then the
constraint, then the seven things the author wanted, then who it is for. The list is
content, not padding.

The last line lands. It can be a verdict ("I recommend it"), a limit ("That's it
basically"), a joke ("Stupid music."), or an instruction ("Go watch it"). An
instruction is usually stronger than an aphorism. Do not end with a summary of the
paragraph you just wrote. The reader was there.

The register can drop in one sentence. The corpus goes from a Lacan reference to
"Music is unremarkable" without a transition. That drop is the personality. Use it
once per page, not every paragraph. If every paragraph ends with a joke, the page is
a performance.

A paragraph is one thought. It can be one sentence. In a manual, aim for 40 to 120
words in a parameter section, up to about 150 in a design note, and under about 60
in a procedure. The corpus can afford a 300-word paragraph because it is an essay.
A manual cannot. If a parameter paragraph passes 150 words, look for the second
thought and split it.

Do not start every paragraph with "Firstly", "Moreover", "Furthermore", "In
addition", or "Additionally". The corpus starts paragraphs with the subject: "The
second short ...", "The CPU is fine ...", "Rubberised knobs ...", "Not much to say
...". Start with the thing.

## Words and punctuation

**British spelling in prose.** colour, favourite, behaviour, centre, theatre,
licence (noun), practise (verb), organise, realise, recognise, analyse, learnt,
whilst, amongst, modelling, signalled, cancelled, travelling. Keep product names,
API names, and file names as they are. "Synthesizer" is the author's spelling.
Keep it. The British -ise/-our rule applies to the rest. "Program" is fine for
software. "Programme" is a plan or a broadcast.

**Contractions are normal.** it's, don't, doesn't, you've, I'm, won't. The docs are
not a contract. Use them in manual prose, not in step lists or reference tables.
The hand rewrite has 33 in 1,899 words. The old manual had 1. The old one was
wrong. The guide rewrite has 8 in its first 70 lines. That is enough. Do not force
one into every sentence.

**Conversational intensifiers, used sparingly.** actually, really, pretty, quite, a
bit, kind of, sort of, just, simply, basically, roughly, probably, a bunch of, and
so on. The corpus uses "a bit" 14 times and "kind of" 12 times in 9,000 words. The
hand rewrite uses "kinda" 4 times and "so" 15 times in 1,899 words. That is the
upper end. A few per page, not one per sentence. The model will want more. Do not
let it. "Sort of" and "probably" are calibrated hedges. "And so on" and "a bunch
of" are generalisers. They are voice when the list is illustrative. Do not strip
them all.

**Plain verdicts.** good, bad, fine, okay, boring, interesting, unremarkable,
remarkable, astonishing, terrible. The corpus is not afraid of a plain verdict. The
docs can say "This is the boring part" or "This is the useful part".

**Technical words stay exact.** operator, algorithm, ratio, envelope, detune,
feedback, wavefolder, filter, resonance, polyphony, voice, part, patch. Explain them
once, then use them. Do not invent synonyms.

**Collocations that sound like the author.** "the whole point", "the whole thing",
"the thing is", "the problem is", "the good thing is", "that's because", "I've got
to say", "as weird as they are", "or whatever", "came out", "has got", "in order
to", "rather than just", "for some reason", "just starting points, mind", "haven't
finished yet", "only when", "in the end", "by the way", "as an aside", "for a
change", "worth a listen", "worth a punt", "that's it basically", "I guess", "I
wonder", "it turns out", "as in", "more X than Y", "one of the most X", "orders of
magnitude", "anecdotally", "though", "just a", "more of a", "I'd really like to".
Use them when they fit. Do not sprinkle them.

**Colons introduce the real list or the real explanation.** "It's done in three
ways: a CGI sequence ..., a subtle slow-motion shot ..., and a big fat nether being
...". The colon is a workhorse in the corpus, 27 of them. Use it to set up the thing
you are about to say, not to decorate a heading.

**Slashes are for alternatives and units, not for prose.** The corpus uses them
for "eros/thanatos", "and/or", and technical lists. In docs, write "or" unless you
mean a file path, a unit, or a scope label. The author uses "2x4-op" and "two-part
x four-operator" as shorthand. Keep it after the first mention. A slash in a scope
or category label is fine: "anecdotal/historical records". Do not expand every
slash.

**No article drumbeats.** A list where every item starts with "The" reads like a
spec sheet. The corpus uses lists of concrete items and labels, not full sentences
with the same article. Drop the article, lead with the noun or the verb, or write
the list as prose.

**No wh-word headings or labels.** "What to reach for first", "How to move" and
"What it does" are questions the reader did not ask. They make a page read like a
generated outline or a help centre. Use a noun phrase or an imperative: "Get
started!", "Navigation", "Functionality". The rule covers headings, table column
headers, and checklist labels.

**No counted couplets.** A heading, caption, or table description built as two
counts reads like a slogan: "One page, one job", "Two sources, one filter", "One
phase, many amplitudes". It sells a shape instead of naming the section. Use a noun
phrase or an imperative, and put the count in the body where it can be explained.
The rule covers headings, captions, and table descriptions, not prose.

**No raw storage values.** A user document describes the value on the screen, not
the number in the firmware. "Ratio is written 65536" and "feedback runs 0 to
32767" tell the reader about a representation they cannot see. Write the panel
range: "ratio 0.50 to 16.00", "feedback 0 to 100%". A patch sheet is a panel form,
not a memory dump.

**No product self-description.** A "what this is" section in an app or a manual
explains the product to someone already using it. Put the proof in the README or
the release notes. Use the page for the next action, the controls, or a real limit.

**No em dash. No semicolon.** The corpus has zero em dashes and one semicolon in
9,015 words. Use a full stop, a comma, a colon, or brackets. This is not a stylistic
preference. It is the strongest punctuation evidence in the corpus.

**No exclamation marks in procedures.** The corpus uses 15 in 9,015 words, mostly
for genuine enthusiasm. The design note can use an exclamation cluster for emphasis
("so! many! params!"). A tip can end with one. A guide body can use one for genuine
emphasis: "That can be the point!" A step never does. Do not spray them. The hand
rewrite uses four, mostly in one cluster.

**A parenthetical "(!)" is a genuine surprise marker.** "one envelope per harmonic
(!)" is the author drawing attention to the scale of the feature. Use it once or
twice, never in a step.

**"In order to" is usually "To".** The author used it in the guide to set up a
purpose clause. Suggest the short form only when it does not flatten the rhythm.

**Bold is for panel labels and the occasional contrast.** The manual bolds
`**Cutoff**` and the other UI labels. The hand rewrite also bolds `**is**` and
`**does**` in one factual contrast. That is allowed. Do not bold whole sentences.

## Page structure

**Open with the thing.** The first sentence says what it is, who it is for, or what
it does. "Type P.fm1 is a four-operator FM synthesizer for the M-VAVE FM-1." Not
"Welcome to the world of FM synthesis." Not "In this section we will explore." Not
"Imagine a synth that ...". The reader is already here. The hand rewrite opens with
"a two-part x four-operator phase-modulation synthesizer in the tradition of the
Yamaha DX/OPwhatever family". The plain noun is there, and the in-joke is next to
it. Keep the plain noun. A guide can open with a plain category and a reason to
care: "two additive synths from Kawai. Additive synths are rare, so they're an
interesting case study." Do not replace that with a pair of metaphors.

**Give the short version first if the page is long.** Two sentences or a short
paragraph at the top, then the detail. The corpus does this with "Short version:"
and "Long version:" in the Funeral Parade review. Use the shape, not the labels
every time.

**Walk the signal in the player's order.** Keys, oscillators, filter, envelope,
effects, output. Or the order of the panel. Not the order of the source files. If
the reader has to jump back and forth, the page is wrong.

**One or two digressions in the preface, one per section in the body.** A design
story, a comparison, a warning. It must teach something. Then return with "Anyway"
or "Back to the ..." and get on with it. The corpus can afford five digressions in a
review. A manual cannot. The hand rewrite has the Taco Bell aside in Ratio, the
Yamaha chip order in Feedback, and the "that's why I added it" in Wavefolder. That
is the target. Never in a step.

**Headings: sentence case, specific, varied.** "Install", "First sound", "The
filter", "Why the envelope is slow", "Patch storage", "MIDI clock", "What the
filter does not do". A heading is a signpost, not a template. If a heading can be a
question the reader is actually asking, use it. If a heading can be a full sentence,
use it. A plain noun heading like "K5 architecture" is better than a spatial
metaphor like "Inside the K5". A playful heading can stay if the author wrote it:
"Sixty-fourrrrrr". One is enough. Not every heading needs a verb or a colon.

**End with a verdict or an instruction.** "Start with a sine and add feedback until
it bites." "If you only want clean tones, leave the wavefolder at 0." Not "Now it's
your turn to explore." Prefer the instruction. The hand rewrite ends with "Try
looking at the operator oscilloscopes ...", not a line about the whole of FM.

Sometimes the concrete detail is the ending. The author cut "That is the K5 in its
natural habitat: a professional tool under deadline." after the Jan Hammer detail.
A closing verdict that restates the paragraph is filler.

**Procedures are neutral.** A step is "Turn the encoder to 50." The voice lives in
the intro and the notes, not in the step. Do not write "Now we'll turn the encoder,
and you'll hear the magic happen." Neutral means no jokes, not no contractions. The
prose around the step can say "you've got four operators". The step itself stays
plain.

## Prohibited patterns

These are the patterns that make a page sound generated. Some are AI tells. Some
are just bad manual habits. All of them are banned.

### The thesis opening

The model draft of the K5/K5000 guide opened "The K5 and K5000 are the two Kawai
instruments that take additive synthesis seriously... The K5 is a spectral
instrument you learn by doing. The K5000 is a spectral instrument you compose
with." The author replaced it with "The K5 and K5000 are two additive synths from
Kawai. Additive synths are rare, so they're an interesting case study."

The plain category and the reason to care are the target. Do not replace them with
a pair of metaphors or a balanced thesis. A guide can open with a fact and a
"because". It does not need a manifesto.

### Meta-commentary about other summaries

"The detail most online summaries get wrong" is a line about other summaries, not
about the instrument. The author cut it. State the fact and let it stand.

### Negation and negative parallelism

Humans rarely introduce a thing by saying what it is not. The author removed most
"It's a X, not a Y" and "It's not an X" setups from the K5/K5000 guide. Start with
the positive, the cause, or the constraint.

The replacement moves:

- Cut the setup and state the positive. "The interesting part is not the list. It
  is..." becomes "The interesting part for sound design is..."
- Attach the fact with a relative clause. "It's a documented quirk, not a mistake
  in your patch" becomes "which is a documented quirk of the instrument."
- Replace the label with the constraint. "They aren't arbitrary-partial
  resynthesizers" becomes "you can't add inharmonic partials..."
- Replace the contrast with the cause. "The K5000 isn't a K5 with a bigger harmonic
  count" becomes "the K5's shortcomings probably were part of what motivated..."
- Soften a real contrast to a comparative. "a specialised resource, not an
  automatic upgrade" becomes "more of a specialised tool than an automatic
  upgrade."
- Attach a needed qualification to the positive. "a complete voice path, not a
  single oscillator" becomes "a complete voice path, rather than just the
  oscillator."

A factual limit stays. "You can't add inharmonic partials" and "it isn't a
universal system" are information. A scope contrast stays: "purely explanatory
rather than factory schematics." The target is the needless label negation, not
every "not".

The test: a negation earns its place only when it carries one of these:

- a causal link,
- a factual comparison,
- an explanation of something potentially counterintuitive,
- a real scope or limit,
- a correction of a specific misconception.

If it carries none of those, cut it. It is a debate move with no information.

A conversational correction can keep the negative. "But that doesn't mean one is
necessarily better than the other! They've just got different personalities." The
negation carries a correction, and "just" scales it. "That is just a tour-rig
claim, though, with no album credits to back it up" does the same with a limit.
The target is the theatrical label contrast, not every negative sentence.

Do not write "A, not B" as an adversative. "single precision, not double", "whole
waveforms, not partials", and "the framework, not the glue" read like a spec
sheet. Use "rather than", a separate sentence, or a "but" clause. Keep the
comma-not form only when the second half is a precise factual limit and the
sentence would be clumsy without it, and even then prefer "rather than".

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

A factual contrast is the exception, not the default. "It's not an emulation of any
one Yamaha chip in particular, but it **is** a DX-style synth" names both sides and
prevents a false expectation. The ban is on the theatrical "not just X, it's Y"
hook.

"Each source is a complete voice path, rather than just the oscillator" is the
same kind of factual contrast. It names both sides. Do not rewrite it into a
positive-only sentence that loses the comparison.

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
three. A 7-item design list is content. Three concrete tips are content. The ban is
on three abstract nouns doing the work of one fact.

### Summaries that restate the heading

If the heading is "Patch storage", the first sentence should say something new:
"Each patch is 64 bytes and stores the four operator levels, the algorithm, and the
name." Not "Patch storage is an important part of the instrument." The heading has
already told the reader the topic. The sentence has to tell them the thing.

### Verdicts that restate the paragraph

A concrete detail can end the paragraph. The author cut "That is the K5 in its
natural habitat: a professional tool under deadline." after the Jan Hammer detail.
The detail already carried the point. A closing verdict that restates the paragraph
is filler, even when it sounds good.

### Aphorisms

An aphorism is a short, universal-sounding verdict that could go on a poster. It
flatters the writer and adds no information. The K5/K5000 guide had several: "Its
restrictions are the lesson." "Two sources with clear jobs beat six sources with
vague ones." "They are instruments for composing the inside of a sound." "The K5
teaches you to think spectrally." "The filter is useful, and it is also a trap."
"Hybridisation is musically intelligent."

The quasi-aphorism is the same move with a concrete noun. "Its restrictions are the
lesson" sounds like a design principle, but it does not say which restrictions or
what they teach. Replace it with the concrete reason: "Its two sources and four
envelopes are enough to learn how harmonic groups move." End on a fact, an
instruction, or a specific judgement that names the thing.

A specific verdict is allowed: "The K5000W is the least immediate additive
instrument of the three." A slogan is not: "The K5000 is a way of thinking."

### Hedging stacks

"Perhaps it might be argued that the filter could potentially ..." Pick one. The
corpus hedges once, then commits. One genuine uncertainty is enough. A single
"kinda" or "I think" is not a stack. Do not strip every qualifier. The hand rewrite
uses "kinda" as a voice marker in the design note and the body. Keep the ones that
are doing work.

### Corporate "we"

The corpus uses "I" 151 times and "we" 10 times. The docs are written by one person.
Use "I" for the author's choices, "you" for the player, "it" for the instrument.
"We" is for a genuinely collective act, not for the brand. "We recommend" is
marketing. "I recommend" is a person.

### Slang and in-group references

The corpus swears. The published manual does not. It does keep light UK slang and
internet asides: "innit", "kinda", "gal", "whatever", "aka", "i.e.", "terminally
online". The hand rewrite uses them in the preface and in one-line tips.

Keep them rare. A few per page, never in a procedure, a warning, or a reference
table. Keep the author's self-description ("I'm more of a sound design gal"). Do
not change "gal" to "guy" or "person". Do not sand off "innit" because a style guide
would. If a reference needs a paragraph of explanation, cut it.

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

### Over-editing

The first manual was 971 words, an 11.3-word mean, a 10-word median, 2 first-person
pronouns, and 1 contraction. It read like a spec sheet. The author's hand rewrite is
1,899 words, a 15.6-word mean, a 13-word median, a 12.1-word standard deviation, 22
first-person pronouns, 33 contractions, 7 brackets, and 4 exclamation marks. The
rewrite is the target. A humanising pass that produces the first set of numbers has
failed.

Fix grammar, not voice. "both parts's algorithms" becomes "both parts' algorithms".
"the Yamahas (and Yamaha emulators)" can stay if the context is clear. "OPwhatever"
can stay if "DX" is next to it. "two-part x four-operator" can stay. Do not turn a
comma splice into three tidy sentences if it reads as one thought. Do not replace
"kinda" with "somewhat" unless the sentence needs the formality. Do not change
"gal" to "person".

### Over-polishing

The K5/K5000 guide rewrite kept the same three first-person tokens and added
explanatory clauses, "whilst", "sort of", "and so on", "probably", a parenthetical
"(!)", and an 80-word sentence. A clean, symmetrical draft can be less human than a
rougher one. Do not split every clause, cut every generaliser, or restore the
thesis.

The rewrite also shows where not to stop. "The even harmonics over from the odd
ones" is missing "take". "More of an specialised tool" should be "more of a
specialised tool". Fix those. Keep the rhythm.

Do not split a connected explanation into three sentences. The model draft had
"Each additive source holds 64 harmonics. Low is 1 to 64. High is 65 to 128." The
author joined them with "with" and a colon. A connectivity pass is part of the
voice, not a compression trick.

### The dropped qualifier

A casual phrase can replace a precise one. It must not drop the fact. "Harmonic 64
is missing for some quirky reason" is fine as a phrase, but it loses the documented
quirk. Keep the fact and the casual wrapper: "for some quirky reason. It's a
documented quirk, not a mistake in your patch."

### No invented facts

A humanising pass may not invent a model name, a date, a number, or a quote. The
hand rewrite adds Chowning, the DX21/DX7 comparison, ymfm, Dexed, the OPL3 and
TX81z/D11/V50 waveforms, and the Yamaha chip order. Those are the author's
knowledge. The model does not get to add its own. The guide rewrite adds a
definition of a harmonic, a comparison to PM sidebands, and a causal "probably"
about the K5 and K5000. Those are also the author's. Keep them, but do not invent
your own.

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
- [ ] No `The... The...` list. Drop the article or lead with the noun or verb.
- [ ] No wh-word heading or table label. Use a noun phrase or an imperative.
- [ ] No counted-couplet heading, caption, or table description. Name the section
      and put the count in the body.
- [ ] No raw storage value. Show the panel value and range.
- [ ] No what-this-is section in an app or a manual.
- [ ] No false dichotomy. No strawman.
- [ ] No marketing hook. No rule-of-three padding.
- [ ] No summary that restates the heading.
- [ ] No "we" where "I" or "you" is meant.
- [ ] British spelling in prose. Product and API names untouched. "Synthesizer"
      stays US.
- [ ] The explanatory prose has contractions. The hand rewrite has 33 in 1,899
      words.
- [ ] The preface can carry two or three asides. The body has one per section.
      Neither is in a step.
- [ ] The author's slang and self-description survive. "Innit", "kinda", "gal",
      "whatever" are not sanded off.
- [ ] The closing is an instruction or a verdict, not an aphorism.
- [ ] The manual is not flatter than the corpus. The median is roughly 13 to 16
      words and the variance is visible.
- [ ] The opening is a plain category and a reason to care, not a polished thesis.
- [ ] The audience is stated. It does not assume the reader owns the hardware.
- [ ] The scope and the status of the diagrams are stated.
- [ ] The guide's long sentences, generalisers, and parenthetical asides survive.
- [ ] No documented qualifier was lost to a casual phrase.
- [ ] The register is guide or study when the page is about an existing instrument.
- [ ] No invented facts.
- [ ] Read it aloud. If it sounds like a press release or a generated outline,
      rewrite it.

## Rule sources

The corpus statistics in this file come from the author's own writing: 9,015 words,
457 sentences, 52 paragraphs, no em dashes, one semicolon, 47 open brackets, "I" 151
times, "we" 10 times. The samples are in `voice-samples.md`.

The manual calibration comes from the author's hand-written preface and sound-design
part of `examples/type-p-fm1/docs/manual.md`, 1,899 words against the first
release's 971. The panel section is additional and follows the same register. The
hand rewrite is the target. The first release is the cautionary example.

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
