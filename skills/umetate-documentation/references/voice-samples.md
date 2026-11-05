# Voice samples

These are short excerpts from the author's own writing: reviews, forum posts, and
notes. They are here for rhythm, not for content. Read them before a front-door
page, a manual intro, or a guide or study, then read `voice.md` for the rules.

The full corpus is not checked in. It is the author's personal film and music
writing, not part of the framework. The excerpts are enough to hear the rhythm.

The published manual is a restrained version of this. No film opinions, no
swearing. The hand rewrite keeps the digressions, the slang, and the jokes. The
sentence is the same.

## The guide rewrite

These are from the author's rewrite of the first 70 lines of the K5/K5000 guide.
They are the target for a guide or study, not a manual page.

### The plain category opening

> The K5 and K5000 are two additive synths from Kawai. Additive synths are rare, so
> they're an interesting case study.
>
> They came out at different times and the K5's shortcomings probably were part of
> what motivated the K5000's design.

The model draft opened with a balanced thesis. The author cut it for a plain
category, a reason to care, and a causal guess. "Probably" is the right hedge. The
plain version is the target.

### Define the term

> A periodic musical sound is a stack of sine waves at multiples of a fundamental.
> Each of these sines is called a harmonic, and the fundamental determines the
> sound's "pitch".

The guide can explain a term the audience may not know. Do not assume the reader
already knows what a harmonic is.

### The long explanatory sentence

> The upper harmonics can be strong at the attack and vanish in the sustain, and
> then the fundamental can fade in late whilst the even harmonics over from the odd
> ones, or a group of high partials can pulse while the fundamental stays still,
> and so on.

The author wrote one long sentence where the model wrote four short ones. Keep the
long sentence. Fix "over from" to "take over from". Keep "whilst" and "and so on".

### The parenthetical surprise

> ... whilst the K5000 has got one envelope per harmonic (!)

"Has got" and the parenthetical "(!)" are voice. They are not P41 or P14.

### The factual contrast

> A K5 Single patch has two sources, containing a complete voice path, rather than
> just the oscillator.

"Rather than just" is a factual contrast. It names both sides. Do not rewrite it
into a positive-only sentence.

### Scope and audience

> This guide is for players and sound designers. ... it isn't a technical manual,
> so the diagrams are purely explanatory rather than factory schematics.

The scope and the audience are stated early. The slash in "anecdotal/historical
records" is a category label, not prose punctuation.

### Replacing the negation

The author removed nearly every "It's a X, not a Y" and "It's not an X" setup.
The replacements are the lesson.

| Draft | Rewrite |
| --- | --- |
| They are not the same idea at two sizes. | Cut. They came out at different times and the K5's shortcomings probably motivated the K5000. |
| The K5000 isn't a K5 with a bigger harmonic count. It's a different architecture. | Cut. The causal link replaces the contrast. |
| The interesting part is not the list. It is... | The interesting part for sound design is... |
| They aren't arbitrary-partial resynthesizers. | You can't add inharmonic partials... |
| The useful question is not how many harmonics... It is... | The K5 provides four envelopes, whilst the K5000 has one per harmonic. |
| a complete voice path, not a single oscillator | a complete voice path, rather than just the oscillator |
| a documented quirk, not a mistake in your patch | for some quirky reason (but keep "documented") |
| a specialised resource, not an automatic upgrade | more of a specialised tool than an automatic upgrade |

The author did not remove factual limits ("you can't add...", "it isn't a
universal system") or a scope contrast ("purely explanatory rather than factory
schematics"). The target is the needless label negation, not every "not".

The test: a negation earns its place only when it carries a causal link, a factual
comparison, an explanation of something potentially counterintuitive, a real
limit, or a correction of a misconception. If it carries none of those, cut it.

### The one loss

> Harmonic 64 is missing for some quirky reason.

The casual phrase is fine, but it drops "documented". Keep the fact: "Harmonic 64
is missing for some quirky reason. It's a documented quirk, not a mistake in your
patch."

### The numbers

The first 70 lines moved from 689 words in 58 sentences (mean 11.6, median 9.5,
standard deviation 8.5, longest 52) to 733 words in 41 sentences (mean 17.4,
median 14, standard deviation 16.7, longest 80). The first-person count stayed at
three. The change is sentence structure and explanatory connectives, not
self-reference.

## The hand rewrite

These are from the author's hand rewrite of the Type P.fm1 manual. They are the
target for manual voice. The first release was flatter. Read these before a manual
page.

### The design note

> I'm a hardcore fan of phase modulation synths, so for the longest time I've kept
> thinking about things I wanted to change on the Yamahas (and Yamaha emulators)
> I've been using over the years. That's where Type P.fm1 comes from.

First person, a specific history, a long setup. The next paragraph can start with
"Originally" and carry the constraint. The preface is front-door register, not a
spec sheet.

### The list is content

> 4. envelope graphs are essential, especially if you've got rate-level envelopes,
> because they help massively with the sheer amount of params, and provide an easy
> overview of what the patch is like at a given moment.

The list is the author's seven design observations. It is content, not rule-of-three
padding. The sentence is long and comma-heavy but reads as one thought. A manual can
carry it.

### The exclamation cluster

> 6. velocity and key scaling are cool but they've got to live in their little
> corner because there are just so! many! params!

The three exclamation marks are deliberate. They are in the design note, not a
procedure. Keep the cluster. Do not spray it through the page.

### The factual contrast

> It's not an emulation of any one Yamaha chip in particular, and the DSP was
> implemented from scratch, but it **is** a DX-style synth, and it **does** take
> cues from the way Yamaha emulators are implemented, particularly ymfm and Dexed.

Both sides are real. The bold `is` and `does` are deliberate contrast, not random
inline bold. This is not the "not just X, it's Y" hook.

### The concrete sound, then the aside

> Whole-number ratios sound clear, odd ratios sound metallic/reedy, and non-integer
> ratios sound clangy and inharmonic, which can be industrial noise or struck-type
> sounds like marimbas, vibraphones, weird glassy pads, and the Taco Bell bell (I've
> never been to a Taco Bell but being terminally online has taught me Americans find
> this really funny.)

The aside names the sound and is one sentence. Keep it. The sentence is a run-on; a
manual edit can split it after "inharmonic" without losing the voice. Do not cut the
Taco Bell aside to make the page neutral.

### The mechanism

> All operators have feedback, but traditionally it shows up the most on carriers
> and on the top operator of a stack. That's because of the way Yamaha chips work:
> the operators were always computed in the same order and the one with feedback
> was always the first one.

"That's because" is the teaching voice, not filler. The history explains why the
panel behaves the way it does. Keep it.

### The design aside

> Personally I find it sounds nice when a patch swells up, goes past the threshold
> for a bit, then comes back under again (that's why I added it).

One aside, one design reason. It earns its place. This is the model for a personal
note in a parameter section.

### The self-description

> I'm more of a sound design gal, I fully sequence my music and I prefer trackers to
> little boxes for sequences/composition/arrangement, but it should work for those
> users as well.

Keep "gal". Do not neutralise it. The sentence tells the reader who the author is,
how they work, and who the synth is for.

### End on an instruction

> Try looking at the operator oscilloscopes to check out how the cascading phase
> modulation progressively warps each waveform!

The earlier draft ended on "the whole of FM in one knob". The author replaced the
aphorism with a concrete next action. Do that.

## Long setup, short landing

> The shorts are tied by themes of music or sound, but they engage with it to
> varying degrees and with one of the shorts I don't even see the connection at
> all, other than having been directed by a well-known musician.

The next paragraph begins "The interludes featuring Gwar are mostly terrible." The
long sentence sets up the verdict. Copy the patience, not the length. A manual can
carry a 40-word sentence if the clauses belong together, then land it in five.

## Verdict first

> The interludes featuring Gwar are mostly terrible. They've got some funny,
> campy, practical effects at times, but the script is painful.

The verdict is the first sentence. The second gives the exception without softening
the verdict. This is how to be fair without hedging. "Mostly terrible" is a real
judgment, not a vibe.

## Concede, then return

> It's well made as a photography and editing exercice, but not too interesting.

One concession, one verdict. No "however" stack, no "on the other hand" chain. The
spelling mistake is left in the corpus and corrected in published docs. The shape is
what matters: credit the craft, then say what it does for you.

## Answer the question

> The CPU is fine (two cores that go up to 320MHz), but I don't think there's
> enough memory for a real-time Python interpreter. The good thing is the processor
> can read/execute stuff directly from flash (XIP)!

This is the shape of a manual answer. Direct answer, reason, caveat, good news. The
number is in the bracket. The caveat is plain. The exclamation is genuine, not
decoration.

## Compare with something real

> Negative feedback is, roughly, a lot like an operator (or more, or a stack) at
> ratio 2 into an operator at ratio 1.

"Roughly" signals the approximation. The comparison uses the reader's own vocabulary.
Then the precise version follows. A comparison to "warmth" or "character" would tell
the reader nothing.

## Negate a fact, not a strawman

> It's not exactly the same sound but that's it basically.

This is how the corpus negates. It does not say "it's not just a sound, it's a
texture". It states the limit and stops. If the difference matters, name both sides.
If it does not, do not build a sentence around it.

## Name the structure

> Family, state and class are roasted relentlessly.

A whole analysis in one line. The nouns are the structure, not the mood. Use this
when explaining a design choice: name the constraint, the incentive, or the part
that does the work. Do not name the vibe.

## Bottom line

> Bottom line: the myth that GEMS sounds bad annoys me to no end.

A plain summary marker, then a personal stake. Use it once in a long page. Not every
page, and never as a substitute for the argument.

## Correct yourself

> I've done a bit of audio DSP work with C# and sometimes you get some very dumb
> asm, although I'm guessing the JIT or a good PGO profile would help.

The claim, then the correction. The hedge is on the cause, not on the experience. The
reader trusts the experience because the author does not overclaim the explanation.

## Recommend it

> Check out the "Live '77" version of The Last One for an entry point if you want.

An imperative, a specific record, a condition. No "we recommend", no "you might want
to consider". The reader can take it or leave it.

## One aside

> I'm a bit anxious about showing what I'm doing to anyone because, besides being
> AI-generated code, the scope is now far larger.

One aside, plain, no self-pity. It earns its place because it explains the state of
the project. A manual can carry one of these in the preface. Not one per section.

## Use the reader's world

> kind of like Angular if you know about web dev?

The analogy is specific to the reader's world. The question tag checks whether the
reader is the right reader. In docs, drop the tag if the audience is already clear.
Keep the specificity.

## One line is a paragraph

> Exposition, exposition. Exposition.

The repetition is the joke. A one-line paragraph is a beat. Use it once or twice per
page for a verdict or a limit. Never in the middle of a procedure.

## Understate it

> Not much to say about this one.

A blunt opener that lowers the stakes. The reader knows the review will be short.
The docs can use the same move before a short section: "Not much to say about this
one. The filter has one control."

## Name the machine

> People had Atari STs with patch editor software that allowed for loading patch
> banks into your synth. Atari STs in particular because they came with MIDI ports
> and they ran Cubase, so they were ideal for production.

The specific machine, the specific ports, the specific software. This is how to be
concrete. "Old computers" would be true and useless.

## Ask a real question

> Is The Mystery Man similar to a vampire? He has to be invited in and lurks in
> your house, shooting tapes of you being violent in moments you don't remember,
> alternatively threatening you and helping you kill people.

A genuine question, then the evidence. Not a hook. Use a real question when you are
actually going to answer it. Do not use a question to announce a section.
