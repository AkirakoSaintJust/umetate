# Type P.fm1 user manual

Type P.fm1 is a two-part x four-operator phase-modulation synthesizer in the tradition of the Yamaha DX/OPwhatever family. Yamaha called it FM because that's what John Chowning's original research did, and the name stuck for historical reasons, but it's phase modulation really.
In each of the two parts, you've got four oscillators, which come together with a dedicated amplitude envelope and a dedicated amplitude LFO in units called operators, and then set them up in one of eight routings, aka algorithms, so that they phase-modulate each other. The combined output of both parts's algorithms plays through two filters and a
wavefolder. As for modulation, besides the per-operator tremolo, you've got one per-part pitch envelope, one per-part pitch LFO, and one global filter envelope. You can also route velocity and key scaling to several parameters within the synth.

I'm a hardcore fan of phase modulation synths, so for the longest time I've kept thinking about things I wanted to change on the Yamahas (and Yamaha emulators) I've been using over the years. That's where Type P.fm1 comes from. Originally, I had a far more complex design incorporating dynamic phase distortion and a kind of phase-indexing granular synthesis, which would have been the "full", "ideal", Type P, but the FM1 is relatively limited both in power and in user interface, plus I wanted to test just how well exactly this framework for making FM1 firmwares works, so I kinda wanted to keep the scope limited.

Anyway, some of the things that have stood out the most to me as a PM synthesis fan are:
1. making patches out of layered partials works especially well with PM.
2. you always need more feedback operators.
3. the extra waveforms on the OPL3 and the TX81z/D11/V50 were actually pretty handy as weird as they are.
4. envelope graphs are essential, especially if you've got rate-level envelopes, because they help massively with the sheer amount of params, and provide an easy overview of what the patch is like at a given moment.
5. oscilloscopes and spectrograms do help a lot.
6. velocity and key scaling are cool but they've got to live in their little corner because there are just so! many! params!
7. being able to copy/paste envelopes or lfos or whole operators or even whole parts makes your life easier.

So that's the concept basically. It's not an emulation of any one Yamaha chip in particular, and the DSP was implemented from scratch, but it **is** a DX-style synth, and it **does** take cues from the way Yamaha emulators are implemented, particularly ymfm and Dexed. There are other things taken specifically from DX synths, like the general character of the envelopes or the fact the knobs have detents at multiples of 1/2, sqrt(2)/2, pi/2 and sqrt(3)/2.

It's two 4-operator parts because that's where I believe the sweet spot lies. There's this massive jump in complexity between editing a DX21 from the panel vs editing a DX7, and I think it's a combination of the DX7's more complex envelopes and key scaling, and the mental overhead of juggling 6 operators. 4-op is more manageable, then you can work on the second part, and the envelope graphs help massively with keeping track of what you're doing. Then you can look into the key scaling and velocity later, although I've got to say they've been greatly simplified here compared to what the DX7 offers.

What I mean is I designed Type P.fm1 as a manageable 10-voice, 8-op synth where you work with partials, but if you want to do key splits or assign each part to a different MIDI channel you can do that as well. I'm more of a sound design gal, I fully sequence my music and I prefer trackers to little boxes for sequences/composition/arrangement, but it should work for those users as well.


## Voice structure

A voice is four operators plus an output path.

- Each operator is an oscillator with its own pitch ratio, waveform, level,
  feedback, and a four-stage rate-level amplitude envelope.
- The algorithm decides which operators are carriers (you hear them) and which
  are modulators (they bend the phase of the next operator).
- The output runs through two multimode filters and a wavefolder, all three
  bypassable.

As I said, the two parts play at once, so you can layer two timbres, or split the keyboard, or send two different sequences over two different MIDI channels.
There's a total of twenty voices, shared between the parts.

## Choosing an algorithm

"Algorithm" just sounds so cool, innit? The `ALGORITHM` knob, 0 to 7, lets you rewire where the output of the four operators goes. Lower numbers are stacked, i.e. one operator modulating the next. Higher numbers are more parallel, so you've got more carriers playing at once. Which on the original DX synths was more of a drawbar organ thing, but since you've got different waveforms and feedback on every operator here, you can do supersaws or epic pads or whatever. Each algorithm has a different character, and the same
four operator settings will sound different on each one.

The screen shows the algorithm number and a small map of the routing.

## Operator settings

Each operator has the following settings. In the operator editor, the `SELECT` knob steps through
the pages and the `SEL` button moves between operators 1 to 4, then wraps around back to 1.

### Ratio

The pitch of the operator relative to the note, as a multiplier. 1.00 is the base, unmodified pitch.
2.00 is an octave up, 4.00 two octaves up, and so on. 0.50 is an octave down. Whole-number ratios sound clear, odd ratios sound metallic/reedy, and non-integer ratios sound clangy and inharmonic, which can be industrial noise or struck-type sounds like marimbas, vibraphones, weird glassy pads, and the Taco Bell bell (I've never been to a Taco Bell but being terminally online has taught me Americans find this really funny.)

### Level

How loud the operator is inside the voice. 99 is full, 50 is about 12 decibels
quieter, 0 is silent. For a modulator, the level is the modulation depth, so this
is where the timbre is shaped as well as the volume. Extreme modulation levels get noisy, so be careful or take advantage of that.

### Feedback

The operator feeds its own output back into its own phase. Zero is the clean waveform. As you
raise the feedback, the sound roughens, then turns into noise at the top. All operators have feedback, but traditionally it shows up the most on carriers and on the top operator of a stack. That's because of the way Yamaha chips work: the operators were always computed in the same order and the one with feedback was always the first one.

Tip: a sine operator taking no modulation will kinda become a reverse sawtooth at about 25%-35%.
Tip 2: modulators become more intense when they have feedback, so it's kinda like cranking the level up beyond its limit.
Tip 3: A sine modulator at ratio 2.00 and 25%-35% feedback going into a sine operator at ratio 1.00 will give you a square-ish kind of waveform, although you do have actual square waves in Type P.fm1.

### Waveform

Twelve shapes, 0 to 11. The first eight are sine-derived and stay clean up high.
Waves 9 to 11 are band-limited pulse, square, and saw, with the brightness rolled
off automatically as the note rises to stop aliasing. If you find high notes are too harsh, try tweaking the key follow to rein modulator levels in as you go up the keyboard, or use the filters to cut the ghosts out.

### Detune

A fine pitch offset of plus or minus 50 cents. Detuning two operators that would
otherwise be in unison thickens the sound and adds movement. Detuning modulators can add a beating effect, which sometimes comes in handy if you want to keep carriers out of phase.

### Envelope

Four rates and three levels. Rate 1 is the attack, rate 2 and rate 3 are the two
decay stages, rate 4 is the release. Level 1, 2, and 3 set where the envelope
holds after each stage. Higher rates are faster, lower slower. The envelope is per-operator, so
a modulator can fade in and out on its own schedule.

### Tremolo

A per-operator amplitude LFO. Rate sets the speed, depth sets the amount.

### Mute

Turns the operator off entirely. Muting a modulator silences the carrier it
drives. Muting a carrier removes that carrier from the mix. That's useful if you're focusing on a particular operator stack or want to check what a certain operator adds to your patch.

## Poly, mono, and unison

- **Mode** is poly or mono. Mono plays one note at a time.
- **Unison count** stacks that many detuned copies of the note in mono.
- **Unison detune** spreads those copies.
- **Legato** holds the envelope across overlapping mono notes.
- **Portamento** slides the pitch between mono notes. The amount is the slide
  time.
- **Note priority** picks which note wins when more than one is held in mono.

## Filters and wavefolder

Two filters and a wavefolder, in series, then the output.

- **Cutoff** and **resonance** per filter. Cutoff is the frequency the filter
  starts to remove. Resonance is the peak at the cutoff, i.e. it makes the part of your patch that's at the cutoff frequency louder. If you crank it up to the max it self resonates, kinda like guitar squeals or a sine wave with harmonic distortion.
- **Filter type** is low-pass, band-pass, or high-pass.
- **Filter envelope** bends the first filter's cutoff with a four-stage envelope,
  so the sound can open and close in brightness as the note goes on.
- **Wavefolder** folds the signal back on itself past a threshold. Amount sets
  how much of the folded signal is mixed in. At zero it is off. Personally I find it sounds nice when a patch swells up, goes past the threshold for a bit, then comes back under again (that's why I added it).

## Vibrato and pitch envelope

- **Pitch LFO** is a vibrato. Rate sets the speed, depth sets the amount.
- **Pitch envelope** bends the pitch of the whole voice over the course of a
  note, in semitones. It is a four-stage, rate-level, envelope like the operators' amplitude
  one, but it moves pitch instead of volume, and the levels are pitch offsets relative to the base, unmodified, note.

## Key and velocity follow

- **Breakpoint** is the note where the keyboard split sits. Below it, one set of
  amounts applies. Above it, another.
- **Key follow** scales the operator level, feedback, envelope, filter cutoff,
  and/or pitch envelope by the note position, so higher or lower notes can be
  brighter, darker, or quieter.
- **Velocity follow** does the same from how hard you play, and a global on-off
  turns the whole velocity system off.

## What to reach for first

Start on algorithm 7, the additive one. Set the four ratios to 1.00, 2.00, 3.00,
and 4.00, all carriers. You get a drawbar-organ stack. Lower operator 2 a little
and you hear how level shapes the timbre. Then switch to algorithm 0 and the same
four operators become a deep FM bass. Try looking at the operator oscilloscopes to check out how the cascading phase modulation progressively warps each waveform!
