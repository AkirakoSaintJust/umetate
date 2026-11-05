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

## The panel

The first part of this manual was about the sound. This part is about finding your
way around the instrument. The M-VAVE FM-1's control panel has 27 keys, a
volume pot, three left encoders, four page encoders, the transport buttons, and a
240 by 240 screen. The keys and the `ALGORITHM` encoder are always available.
Everything else is a page you open with a context button.

### The surface

- **27 keys** play notes, F3 to G5. `OCT−` and `OCT+` move the keybed an octave
  down or up, clamped to two octaves either way.
- **MASTER** is the volume pot. It is always volume.
- **ALGORITHM** is the dedicated algorithm encoder. It always edits the active
  part's algorithm. Turning it shows the algorithm graph for about 600 ms after
  you stop.
- **SELECT** is the page encoder. It moves forward and back through the current
  context's pages.
- **PRESETS** opens the preset browser.
- **KNOB 1 to 4** are the page encoders. On a parameter page they edit the
  parameter rows from top to bottom. If a page has fewer than four rows, the extra
  knobs do nothing. Display pages have no assignments.
- **HOME, EDIT, ENV, LFO, FX, GLO** are the six context buttons.
- **SEL** selects the next operator on a single tap. A double tap within about
  300 ms switches the active part. Hold SEL for the chords below. The single tap
  lands after the double-tap window, so there is a short pause.
- **SAVE** opens the save chooser. With SEL it initialises the patch or a part.
- **ARP, SEQ, PLAY, REC** mute operators 1 to 4. With SEL they mute parts.

### How to move

Press a context button to open that context at its first page. Press the same
button again to move to the next page. `SELECT` also pages forward and back. The
pages wrap at the ends. Every context's pages are in the order shown in its table,
so pressing the context button again or turning `SELECT` walks them in that order.

`HOME` pops back to the home context. Press `HOME` again to step through the home
pages.

The header stays at the top. The first line shows the parts, the four operators,
the algorithm, and the context and page. The second line shows the current page
title. The active part and operator are light blue, muted parts and operators are
red, parameter values and the algorithm number are hot pink, and the page
description is bright green.

The footer shows the gesture legend:

| Gesture | Action |
| --- | --- |
| `SEL` (single tap) | Next operator |
| `2x SEL` | Switch part |
| `SEL` + key | Mute the active operator |
| `SEL` + `EDIT` | Copy the current page |
| `SEL` + `SAVE` | Init patch, or init part in GLO |
| `SEL` + `ARP` or `SEL` + `PLAY` | Mute part 1 |
| `SEL` + `SEQ` or `SEL` + `REC` | Mute part 2 |
| `ARP`, `SEQ`, `PLAY`, `REC` | Mute operators 1, 2, 3, 4 |

A popup owns the controls while it is open. It closes on its own after about
three seconds of no input without committing. Press `SAVE` to commit.

### HOME

The home context is the display and performance view. It has eight pages. The four
page knobs have no assignments on any of them. The `ALGORITHM` encoder and the
keys are the live controls.

| Page | What it shows |
| --- | --- |
| ALGORITHM | The current algorithm as four operator blocks and a routing string. Carriers are pink, modulators white. Turn `ALGORITHM` to change it. |
| A-ENVS | Four amplitude-envelope graph cells. In the current firmware all four draw the selected operator's envelope, so use `SEL` to step through the operators and compare them. |
| SCOPES | Four oscilloscope traces, one per operator of the active part. |
| SPECTROS | Four spectrograms, one per operator of the active part. |
| SCOPES | The two part mixes, one larger scope per part. |
| SPECTROS | The two part mixes, one larger spectrogram per part. |
| POST-FX MULTI-PATCH SCOPE | The final mixed output after both filters and the wavefolder. |
| POST-FX MULTI-PATCH SPECTRO | The final mix as a spectrogram. |

The two pairs of scope pages share a title. The first pair shows four small traces
for the operators. The second pair shows two larger traces for the part mixes. The
post-FX pages say `POST-FX MULTI-PATCH`, so they are easy to tell apart.

The algorithm graph popup appears while you turn the encoder and stays for about
600 ms after you stop.

### EDIT

The `EDIT` context is the operator editor. It has four pages. `SEL` chooses the
operator, 1 to 4, and the header shows which one. The first three pages follow the
selected operator. `OP DETUNES` is part-level and shows all four operators.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| OSCILLATOR | RATIO | LEVEL | FEEDBACK | WAVE | A scope of the selected operator. |
| OP DETUNES | OP 1 | OP 2 | OP 3 | OP 4 | The four per-operator detunes for the active part. |
| OP KEY FOLLOW | OP LEVEL KS LO | OP LEVEL KS HI | OP FB KS LO | OP FB KS HI | The selected operator's level and feedback key follow. |
| OP VEL SENS | OP LEVEL VS | OP FB VS | | | The selected operator's level and feedback velocity sensitivity. |

`OP DETUNES` is the only part-level page here. The key-follow and velocity pages
are operator-relative, so they change the operator named in the header.

### ENV

The `ENV` context is the envelope editor. It has six pages. The A-ENV pages edit
the selected operator's amplitude envelope. The P-ENV pages edit the part's pitch
envelope. The last two pages set the key and velocity follow for the envelope
rates.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| A-ENV (rates) | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | RELEASE RATE | The selected operator's A-ENV graph. |
| A-ENV (levels) | LEVEL 1 | LEVEL 2 | SUSTAIN | | The same graph, for the levels. |
| P-ENV (rates) | ON | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | The part pitch-envelope graph. |
| P-ENV (levels) | RELEASE RATE | LEVEL 1 | LEVEL 2 | SUSTAIN | The same graph, for the levels. |
| ENV KEY SCALE | A-ENV RATE KS LO | A-ENV RATE KS HI | P-ENV RATE KS LO | P-ENV RATE KS HI | The rate key-follow amounts. |
| VEL SENS | A-ENV RATE VS | P-ENV RATE VS | | | The rate velocity-follow amounts. |

Both A-ENV pages are titled `A-ENV`, and both P-ENV pages are titled `P-ENV`. The
row labels tell you which half you are on. The A-ENV pages follow the selected
operator. The P-ENV pages are part-level.

### LFO

The `LFO` context has two pages. `A-LFO` is the selected operator's amplitude LFO.
`P-LFO` is the part pitch LFO. This is a separate context from `GLO`.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| A-LFO | RATE | DEPTH | WAVE | | The selected operator's amplitude LFO. |
| P-LFO | RATE | DEPTH | WAVE | | The part pitch LFO. |

The fourth knob is unused on both pages.

### FX

The `FX` context is the output chain. It has eight pages. The signal order is
filter 1, then the wavefolder, then filter 2. Filter 1 has the F-ENV. Filter 2 is
static. The key-follow and velocity pages set how the filters and the F-ENV
respond across the keyboard.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| FILTER | ON | CUTOFF | RES | TYPE | Filter 1. |
| F-ENV (rates) | ATTACK RATE | DECAY 1 RATE | DECAY 2 RATE | RELEASE RATE | The filter-envelope graph. |
| F-ENV (levels) | LEVEL 1 | LEVEL 2 | SUSTAIN | DEPTH | The filter-envelope graph and its depth. |
| WAVEFOLD | ON | AMOUNT | THRESH | FOLDS | The wavefolder. |
| FILTER 2 | ON | CUTOFF | RES | TYPE | Filter 2, after the wavefolder. |
| F1 KEY FOLLOW | F1 CUTOFF KS LO | F1 CUTOFF KS HI | F-ENV RATE KS LO | F-ENV RATE KS HI | Filter 1 and F-ENV key follow. |
| F2 KEY FOLLOW | F2 CUTOFF KS LO | F2 CUTOFF KS HI | | | Filter 2 key follow. |
| FILTER VEL SENS | F1 CUTOFF VS | F2 CUTOFF VS | F-ENV RATE VS | | Filter 1, filter 2, and F-ENV velocity sensitivity. |

Both F-ENV pages are titled `F-ENV`. The rates page has the four stage rates. The
levels page has the three levels and the envelope depth. Filter 2 has no envelope
of its own, so its page is only the filter controls.

### GLO

The `GLO` context is the setup and global page. It has ten pages. This is where the
two parts are layered, split, assigned to MIDI channels, and named. It also holds
the voice mode, the mono stack, the backup page, and the credits.

| Page | KNOB 1 | KNOB 2 | KNOB 3 | KNOB 4 | Screen |
| --- | --- | --- | --- | --- | --- |
| SINGLE PART LAYERING | PART 1 LEVEL | PART 1 DELAY | PART 2 LEVEL | PART 2 DELAY | The two part levels and delays. |
| KEY SPLIT | P1 LOW | P1 HIGH | P2 LOW | P2 HIGH | The key ranges for the two parts. |
| MIDI CH | P1 CH | P2 CH | | | The MIDI channel for each part. |
| KEY SCALING | BREAKPOINT | KEY SENS ON | | | The global key-follow breakpoint and switch. The targets are in EDIT, FX, and ENV. |
| VEL SENS | VEL SENS ON | | | | The global velocity-follow switch. The targets are in EDIT, FX, and ENV. |
| VOICE MODE | MODE | PRIORITY | LEGATO | PORTA | The part voice mode. TUNE is shown below PORTA but has no page-knob assignment in this panel. |
| MONO STACK | VOICES | DETUNE | | | The mono stack count and detune. |
| NAMES | PART 1 NAME | PART 2 NAME | MULTI-PATCH NAME | | Open the name editor with the matching knob. |
| BACKUP / LOAD | | | | | Host-side SysEx backup, `umetate preset export/import`, model byte 64. No MIDI channel is needed. |
| VERSION + CREDITS | | | | | The firmware version, the product name, and the typeface credit. |

`KEY SCALING` and `VEL SENS` only hold the breakpoint and the on/off switch. The
per-target amounts live in `EDIT` for operator level and feedback, in `FX` for the
filter cutoffs and the F-ENV rate, and in `ENV` for the A-ENV and P-ENV rates.

`VOICE MODE` has five rows. The four page knobs reach MODE, PRIORITY, LEGATO, and
PORTA. TUNE is visible, but this panel does not assign it to a page knob.

The `NAMES` page opens the name editor from the matching knob. The editor uses
`K1` for the character, `K2` for the cursor, `SEL` to delete, `SAVE` to accept, and
`HOME` to cancel. The editor auto-closes after about three seconds of no input and
restores the old name.

`BACKUP / LOAD` and `VERSION + CREDITS` are read-only pages. The four page knobs do
nothing there.

### Parameter reference

The sound-design chapters above explain the main parameters in depth. This table
is the quick lookup for every page row, including the ones the chapters do not
cover. The ranges are the ones the panel shows.

#### Operator

| Parameter | Range | What it does |
| --- | --- | --- |
| RATIO | 0.50 to 16.00 | The operator's pitch as a multiple of the note. 1.00 is unison, 2.00 an octave up, 0.50 an octave down. Whole-number ratios sound clear, odd ratios reedy, and non-integer ratios clangy. |
| LEVEL | 0 to 99 | The operator's output level. 99 is full, 50 is about 12 dB down, and 0 is silent. On a modulator this is the modulation depth. |
| FEEDBACK | 0 to 100% | The operator's output fed back into its own phase. 0 is clean, higher values roughen the wave, and the top turns to noise. A sine at 25 to 35% becomes a reverse saw. |
| WAVE | 0 to 11 | The operator waveform. 0 to 8 are sine-derived and stay clean high up. 9 is pulse, 10 is square, and 11 is saw, all band-limited with mip maps. |
| OP DETUNE | -50 to +50 cents | A fine offset for one operator. Detuning two operators that would be in unison thickens the sound. Detuning a modulator adds beating. |
| OP LEVEL KS LO/HI | -100 to +100% | How much the operator level follows the keyboard below and above the breakpoint. Positive pushes the level toward its extreme, and negative pushes the other way. |
| OP FB KS LO/HI | -100 to +100% | The same key follow for feedback. |
| OP LEVEL VS | -100 to +100% | How much velocity moves the operator level at maximum velocity. The global `VEL SENS ON` switch must be on. |
| OP FB VS | -100 to +100% | The same velocity follow for feedback. |
| A-ENV RATE 1 to 4 | 0 to 99 | The four stage rates. Higher is faster. Rate 1 is attack, 2 and 3 are decay, and 4 is release. |
| A-ENV LEVEL 1 to 3 | 0 to 99 | The levels the envelope holds after each stage. Level 3 is the sustain. |
| A-ENV RATE KS LO/HI | -100 to +100% | Key follow for the A-ENV rate. |
| A-ENV RATE VS | -100 to +100% | Velocity follow for the A-ENV rate. |
| A-LFO RATE | Hz | The tremolo speed. |
| A-LFO DEPTH | 0 to 100% | The tremolo amount. |
| A-LFO WAVE | 0 to 11 | The tremolo waveform. Sine is the usual choice. |

#### Pitch envelope and pitch LFO

| Parameter | Range | What it does |
| --- | --- | --- |
| P-ENV ON | on/off | Turns the part pitch envelope on. |
| P-ENV RATE 1 to 4 | 0 to 99 | The four pitch-envelope rates. Higher is faster. |
| P-ENV LEVEL 1 to 3 | semitone offsets | The pitch offset at each stage, relative to the note. |
| P-ENV RATE KS LO/HI | -100 to +100% | Key follow for the P-ENV rate. |
| P-ENV RATE VS | -100 to +100% | Velocity follow for the P-ENV rate. |
| P-LFO RATE | Hz | The vibrato speed. |
| P-LFO DEPTH | amount | The vibrato amount. |
| P-LFO WAVE | 0 to 11 | The vibrato waveform. |

#### Filter and wavefolder

| Parameter | Range | What it does |
| --- | --- | --- |
| FILTER ON | on/off | Bypasses or enables filter 1. |
| CUTOFF | frequency | Where filter 1 starts to remove. Turn it down to darken the sound and up to open it. |
| RES | resonance | The peak at the cutoff. At the top it self-oscillates. |
| TYPE | LPF, BPF, HPF | The filter response. |
| F-ENV RATE 1 to 4 | 0 to 99 | The four filter-envelope rates. Higher is faster. |
| F-ENV LEVEL 1 to 3 | 0 to 99 | The levels the filter envelope holds. Level 3 is the sustain. |
| F-ENV DEPTH | 0 to 100% | How far the filter envelope moves the cutoff. |
| F1 CUTOFF KS LO/HI | -100 to +100% | Key follow for filter 1 cutoff. |
| F-ENV RATE KS LO/HI | -100 to +100% | Key follow for the F-ENV rate. |
| F1 CUTOFF VS | -100 to +100% | Velocity follow for filter 1 cutoff. |
| WAVEFOLD ON | on/off | Bypasses or enables the wavefolder. |
| AMOUNT | 0 to 100% | How much folded signal is mixed in. 0 is off. |
| THRESH | 0 to 100% | The level where folding starts. A lower threshold folds earlier. |
| FOLDS | 1 to 8 | The number of fold stages. More folds add harsher harmonics. |
| FILTER 2 ON | on/off | Bypasses or enables filter 2. |
| FILTER 2 CUTOFF | frequency | Where filter 2 starts to remove. |
| FILTER 2 RES | resonance | The peak at filter 2's cutoff. |
| FILTER 2 TYPE | LPF, BPF, HPF | The filter 2 response. |
| F2 CUTOFF KS LO/HI | -100 to +100% | Key follow for filter 2 cutoff. |
| F2 CUTOFF VS | -100 to +100% | Velocity follow for filter 2 cutoff. |
| F-ENV RATE VS | -100 to +100% | Velocity follow for the F-ENV rate. |

#### Global

| Parameter | Range | What it does |
| --- | --- | --- |
| PART 1/2 LEVEL | 0 to 99 | The part's output level. 99 is full, 50 is about 12 dB down, and 0 is silent. |
| PART 1/2 DELAY | 0 to 1000 ms | Delays that part against the other. |
| P1/P2 LOW/HIGH | note names | The key range for each part. Notes outside it are ignored by that part. |
| P1/P2 CH | MIDI channel | The channel each part listens to. |
| BREAKPOINT | note name | The note where key follow is neutral. |
| KEY SENS ON | on/off | The global key-follow switch. |
| VEL SENS ON | on/off | The global velocity-follow switch. |
| MODE | poly, mono | Poly plays all notes. Mono plays one note at a time. |
| PRIORITY | last, highest, lowest | Which note wins when several are held in mono. |
| LEGATO | on/off | Holds the envelope across overlapping mono notes. |
| PORTA | 0 to 5000 ms | The one-octave glide time. 0 is off. |
| TUNE | -100 to +100 cents | The part tune. It is shown on `VOICE MODE` but has no page-knob assignment in this panel. |
| VOICES | 1 to 8 | The mono stack size. |
| DETUNE | 0 to 200 cents | The spread between the stacked copies. |

### Saving and loading

`SAVE` opens the save chooser. The chooser has two rows, `single part` and
`multi-patch`, and each row shows the slot number and the stored name. `KNOB 1`
toggles the kind, `KNOB 2` scrolls the slot, `SAVE` commits, and `HOME` cancels.

For a single part, `SAVE` opens the `WHICH SINGLE PART` chooser. `KNOB 1` picks
part 1 or part 2, `SAVE` saves, and `HOME` cancels.

For a multi-patch, `SAVE` opens the save-mode chooser. `KNOB 1` picks the mode,
`SAVE` saves, and `HOME` goes back to the slot chooser. The three modes are:

- **discard edits**: save the composition using the parts' stored single-part
  slots, so the active part's live edits are not written into a part slot.
- **save as new part**: write the active part's live edits to a new empty
  single-part slot, then save the multi-patch referencing it.
- **mutate in place**: write the active part's live edits into its existing
  single-part slot, then save the multi-patch.

The actual bank write waits until the engine is quiet, so a save never clicks.

`PRESETS` opens the preset browser. Outside `GLO` it browses the multi-patches. In
`GLO` it browses the single parts. The popup shows the slot number and the stored
name. Scroll with the encoder, then stop for about two seconds to apply. A
single-part load opens the `WHICH SINGLE PART` chooser first.

`SEL` + `SAVE` outside `GLO` initialises the whole patch. Both parts go to their
init values, part 2 is muted, and the names reset to `INIT PART` and `INIT MULTI`.
Save first if you want to keep the current patch. In `GLO`, `SEL` + `SAVE` opens
the part chooser so you can initialise one part.

`SEL` + `EDIT` copies the current page. On a part-level page the chooser lists the
two parts. On an operator page it lists the eight part and operator targets.
`KNOB 1` picks the target, `SAVE` applies, and `HOME` cancels. On a page with
nothing to copy, the chord opens `EDIT` instead.

### The screen and the LEDs

The screen is 240 by 240. The header and footer stay fixed while the page below
them changes. The header shows the active part and operator, the algorithm, the
context and page, and the page title. The footer carries the gesture legend.

Keys light as they sound. The `OCT−` and `OCT+` buttons light when the keybed is
shifted below or above its base. Muted parts and operators show red in the header.
The parameter values and the algorithm number are hot pink, and the page
description is bright green.

Popups are modal. They cover the page, take every control, and close after about
three seconds of no input without committing. `SAVE` commits the save and name
editors.

### Quick reference

| Context | Pages | What it is |
| --- | --- | --- |
| HOME | 8 | Algorithm graph, envelope graphs, scopes, spectros, post-FX displays. |
| EDIT | 4 | Operator oscillator, detunes, key follow, velocity sensitivity. |
| ENV | 6 | A-ENV, P-ENV, envelope key follow, envelope velocity sensitivity. |
| LFO | 2 | A-LFO and P-LFO. |
| FX | 8 | Filter 1, F-ENV, wavefolder, filter 2, filter follow. |
| GLO | 10 | Parts, split, MIDI channels, voice mode, names, backup, credits. |

With the map in hand, the next section is a first patch to try.

## What to reach for first

Start on algorithm 7, the additive one. Set the four ratios to 1.00, 2.00, 3.00,
and 4.00, all carriers. You get a drawbar-organ stack. Lower operator 2 a little
and you hear how level shapes the timbre. Then switch to algorithm 0 and the same
four operators become a deep FM bass. Try looking at the operator oscilloscopes to check out how the cascading phase modulation progressively warps each waveform!
