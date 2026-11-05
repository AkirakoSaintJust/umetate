# P1Onken Type P.fm1

Hey, it's Akirako Saint-Just from the パンク派第１音響合成研究班, or Punk Faction, Sound Synthesis Research Unit Number 1 (P1Onken for short.)
I was a bit anxious about the proliferation of vibecoded firmwares so I wanted to provide a framework that at least provided some rails so that I could maybe help the community create cool synths, avoid slop, and take advantage of the full capabilities of the unit, like the dual-core processor. That framework is called umetate, and I reckon it's pretty advanced, but I still want to work on it a bit before releasing it. I made this synth using umetate to check out whether it works properly, and it looks like it does, so yay. Umetate, by the way, is pronounced oo-meh-tah-teh and means land reclamation, like Odaiba Island in Tokyo for instance. It's also a post-punk song by Zelda about taking a walk around the reclaimed land's industrial landscape every day (please give Zelda's Carnival album a listen if you like post-punk.) I guess it goes with the maritime theme a lot of FM-1 firmwares have, but more industrial and edgy because that's what P1Onken is like.

Anyway, besides being a test, Type P is this synth idea I've had forever, and which I've been thinking of for a long time. It's a 2-part, 4-op phase distortion synth with feedback and a bunch of waveforms on every operator. Broadly it's a Yamaha-style synth, but it's not meant to be an emulation of any of them, mostly because the idea comes from the limits I've encountered using actual Yamaha synths and actual emulators. Besides, the DSP is reimplemented from scratch although ymfm and msfa/Dexed were a reference.

It's got 2x4-op because I feel like it's the best compromise between ease and power. You can do keyboard splits or send two different sequences in over two different MIDI channels, but the main purpose of having two parts is being able to easily compose complex patches out of partials, just like Wendy Carlos taught us. So it's a 20-voice bitimbral synth if you want, and there are no restrictions for that use case, but I was mostly aiming for a 10-voice, 8-operator synth, without the complexity of having 3 million algorithms, and with the ability to design your patches incrementally.

You've got feedback on every operator, which I feel gives a lot of freedom, and all of the waveforms from the OPL3 and the OPZ (DX11, TX81z), although the pulse, square and saw are a bit different to the OPL3 versions to avoid the nasty aliasing the naive, single-table version gave.

Something cool is a sine operator at roughly 30% or 35% feedback will give you a reverse saw, so if you pair that with a saw operator you can do pseudo-PWM tricks if you want.

You've also got two (global) multimode filters and a (global) wavefolder. The first filter has an envelope of its own and is meant to help you shape your timbres, whilst the second filter has no envelope and is meant to sift aliasing or harshness out if you feel like you need it. It's got a key follow param so you can make it clamp harder on brighter notes if you find they get too shrill, for instance. The wavefolder is mostly meant for expression, i.e. if you got a patch that swells up, it might cross the wavefolder's threshold at its peak and give you this nice kind of dynamic "breaking point". You can use that for string bow effects, for instance. Or of course, simply as a source of grime and distortion. 2 or 3 folds add distorted harmonics, 4 folds is noisy, and going beyond that is proper noise. I prioritised those effects over delay, reverb, chorus and so on because I felt they were the most useful for sound design. If the complexity and computing budget won't allow for modulated delay, reverb, etc., I feel like having them on board doesn't make a lot of sense over just using whatever external VST or pedal you like most.

Oh, so this is a sound design-focused synth. I wanted whatever implementation of my dream phase modulation synth the FM1 and umetate allowed for, rather than a groovebox which isn't my thing, so there is no sequencer. You can implement your own if you want though!

Bug reports and any suggestions are welcome.
Phase on, industrial punks!

## Try it online

[https://akirakosaintjust.github.io/type-p-fm1/](https://akirakosaintjust.github.io/type-p-fm1/)

## Install on the FM-1

1. Download `type-p-fm1.fwsc`.
2. Ideally you'd use umetate for flashing, by putting your FM-1 in update mode and then running this:

   ```sh
   umetate flash type-p-fm1.fwsc --device
   ```
   But umetate is not out yet, and to be honest I don't have my physical FM-1 at hand, so I can't offer any guarantee it'll work. I'd hugely appreciate the testing work if you have all the tools needed to debrick your unit or go back to another firmware should things go wrong.

## Manual

- [User manual](docs/manual.md), including the panel reference
- [MIDI and SysEx](docs/midi-and-sysex.md)
- [Patch sheet](docs/patch-sheet.md)

## Downloads

[`RELEASES.md`](RELEASES.md) lists the firmware, the plugin archives, the checksums, and the source locations. The optional VST3 and CLAP builds are in [`plugins/`](plugins/), with install steps in [`plugins/README.md`](plugins/README.md). They use the same engine and the same patch banks as the firmware.

## Releases

[CHANGELOG.md](CHANGELOG.md) lists what changed.

## Licence

GPL-3.0-only licence. See [LICENSE](LICENSE), and [LICENSING.md](LICENSING.md) for the third-party credits and attribution.

## Source

[`src/`](src/) (this project) and [`framework/`](framework/) (the full umetate framework source, also GPL-3.0, at <https://github.com/AkirakoSaintJust/umetate>). The generated DSP is more of an object code generated from the JSONs, but it's bundled at [`framework/firmware/gen/`](framework/firmware/gen/), so the tree builds as-is.