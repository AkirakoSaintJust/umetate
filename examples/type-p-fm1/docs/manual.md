# Type P.fm1 user manual

Type P.fm1 is a four-operator FM synthesizer in the tradition of the Yamaha DX
family. Four oscillators, called operators, can frequency-modulate each other in
one of eight routings. That routing is the algorithm. The operators play through
two filters and a wavefolder, with a pitch envelope, a vibrato, and per-operator
tremolo.

## How the voice is built

A voice is four operators plus an output path.

- Each operator is an oscillator with its own pitch ratio, waveform, level,
  feedback, and a four-stage amplitude envelope.
- The algorithm decides which operators are carriers (you hear them) and which
  are modulators (they bend the pitch of the next operator).
- The output runs through two multimode filters and a wavefolder, all three
  bypassable.

Two parts play at once, so you can layer two timbres or split the keyboard.
Twenty voices are shared between the parts.

## The algorithm

The algorithm knob, 0 to 7, rewires the four operators. Lower numbers are
stacked, one operator modulating the next. Higher numbers are more parallel, more
carriers sounding at once. Each algorithm has a different character, and the same
four operator settings sound different on each one.

The screen shows the algorithm number and a small map of the routing.

## The operators

Each operator has these settings. In the operator editor, `SELECT` steps through
the pages and `SEL` moves between operators 1 to 4.

### Ratio

The pitch of the operator relative to the note, as a multiplier. 1.00 is unison.
2.00 is an octave up. 0.50 is an octave down. Whole-number ratios sound clear and
bell-like. Odd ratios sound metallic. Non-integer ratios sound clangy and
inharmonic.

### Level

How loud the operator is inside the voice. 99 is full, 50 is about 12 decibels
quieter, 0 is silent. For a modulator, the level is the modulation depth, so this
is where the timbre is shaped, not just the volume.

### Feedback

The operator feeds its own output back into its own pitch. Zero is clean. As you
raise it, the sound roughens, then turns into noise at the top. Feedback works on
any operator, but it shows up most on carriers and on the top operator of a stack.

### Waveform

Twelve shapes, 0 to 11. The first eight are sine-derived and stay clean up high.
Waves 9 to 11 are band-limited pulse, square, and saw, with the brightness rolled
off automatically as the note rises to stop aliasing.

### Detune

A fine pitch offset of plus or minus 50 cents. Detuning two operators that would
otherwise be in unison thickens the sound and adds movement.

### Envelope

Four rates and three levels. Rate 1 is the attack, rate 2 and rate 3 are the two
decay stages, rate 4 is the release. Level 1, 2, and 3 set where the envelope
holds after each stage. Higher rates are faster. The envelope is per-operator, so
a modulator can fade in and out on its own schedule.

### Tremolo

A per-operator amplitude LFO. Rate sets the speed, depth sets the amount.

### Mute

Turns the operator off entirely. Muting a modulator silences the carrier it
drives. Muting a carrier removes that carrier from the mix.

## The voice modes

- **Mode** is poly or mono. Mono plays one note at a time.
- **Unison count** stacks that many detuned copies of the note in mono.
- **Unison detune** spreads those copies.
- **Legato** holds the envelope across overlapping mono notes.
- **Portamento** slides the pitch between mono notes. The amount is the slide
  time.
- **Note priority** picks which note wins when more than one is held in mono.

## The output chain

Two filters and a wavefolder, in series, then the output.

- **Cutoff** and **resonance** per filter. Cutoff is the frequency the filter
  starts to remove. Resonance is the peak at the cutoff.
- **Filter type** is low-pass, band-pass, or high-pass.
- **Filter envelope** bends the first filter's cutoff with a four-stage envelope,
  so the sound can open and close with the note.
- **Wavefolder** folds the signal back on itself past a threshold. Amount sets
  how much of the folded signal is mixed in. At zero it is off.

## The global modulation

- **Pitch LFO** is a vibrato. Rate sets the speed, depth sets the amount.
- **Pitch envelope** bends the pitch of the whole voice over the course of a
  note, in semitones. It is a four-stage envelope like the operators' amplitude
  one, but it moves pitch instead of level.

## Key and velocity follow

- **Breakpoint** is the note where the keyboard split sits. Below it, one set of
  amounts applies. Above it, another.
- **Key follow** scales the operator level, feedback, envelope, filter cutoff,
  and pitch envelope by the note position, so higher or lower notes can be
  brighter, darker, or quieter.
- **Velocity follow** does the same from how hard you play, and a global on-off
  turns the whole velocity system off.

## What to reach for first

Start on algorithm 7, the additive one. Set the four ratios to 1.00, 2.00, 3.00,
and 4.00, all carriers. You get a drawbar-organ stack. Lower operator 2 a little
and you hear how level shapes the timbre. Then switch to algorithm 0 and the same
four operators become a deep FM bass. The same settings, two very different
instruments, is the whole of FM in one knob.
