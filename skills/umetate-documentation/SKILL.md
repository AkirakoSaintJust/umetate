---
name: umetate-documentation
description: Write thorough, readable, human documentation for end users of a synthesizer built on umetate. Covers the user manual, panel reference, MIDI and SysEx reference, patch sheet, installation guide, and release notes. Rewrites are synchronic (current state, not history), written from the instrument's point of view, and humanised so they read like a careful human wrote them. Never uses em dashes or semi-colons, never loses information.
version: 1.0.0
license: GPL-3.0-only
compatibility: OpenCode and Agent Skills-compatible loaders
allowed-tools: read, grep, glob, edit, write, shell, websearch, webfetch
---

# umetate documentation

Write the papers a musician actually reads: the manual, the panel walkthrough, the
MIDI sheet, the patch sheet, the install guide, and the release notes. The reader
is a person with the synthesizer in front of them, not a developer. Your job is to
help them get a sound and understand why.

## The six rules

These are the whole skill. Read them before writing a word.

1. **Synchronic, not historical.** Describe the instrument as it is right now.
   Do not narrate how it got here. Release notes are the one exception, they are a
   version history by nature. Every other page says "here is how it works", never
   "we changed X to Y".
2. **From the instrument, not the code.** The reader sees a knob and hears a sound.
   Describe what the knob does and what the sound does. Do not mention nodes, macros,
   buffers, or the generator. If the code has a "phasor" and a "tl" stage, the
   manual says "pitch" and "level".
3. **The author's voice, not the model's.** When two wordings are both correct,
   pick the one the author would write. The reference samples are
   `examples/type-p-fm1/publish-readme.md` and the root `README.md`. The full
   profile is in `references/voice.md`. See the writing craft below.
4. **No information loss.** Humanising is allowed to cut, sharpen, and reorder, but
   not to drop a fact. Compare every edited paragraph to the original and put back
   anything that went missing.
5. **No em dashes, no semi-colons.** Full stop. Rewrite around them.
6. **Radical rewrites are fine.** The goal is prose quality, not minimal diffs.

## The voice

Read `references/voice.md` before the first paragraph. It defines three
registers:

- **Front door:** the README, release notes, and manual preface. The author is
  present, in first person, with a specific story, a concrete comparison, and a
  plain statement of what the instrument is not.
- **Manual:** the manual, panel reference, MIDI reference, and install guide.
  Warm technical prose. Address the reader as "you", use first person in section
  intros and design asides, and keep procedures neutral.
- **Reference:** the patch sheet and byte-level tables. Terse and exact.

The samples use British spelling in prose, contractions, and dry humour. They do
not use em dashes, semicolons, marketing adjectives, or three-item padding. Copy
the habits, not the catchphrases. One personal aside per page is enough.


## The document set

A synthesizer project ships these user-facing documents. Each one has a job.

| Document | Job |
| --- | --- |
| README | The front door. What it is, one sentence. The web app link. How to install. |
| User manual | Architecture and sound design, from the player's chair. |
| Panel reference | Every control, menu, key combination, and how to save. |
| MIDI and SysEx reference | The CC map, the note routing, the SysEx message format. |
| Patch sheet | A blank form a user can print and write a patch on. |
| Installation | How to flash the firmware and how to run the web app. |
| Release notes | What changed in each version, for the person updating. |

The manual and the panel reference are the two most read. Spend the most care there.

## The user manual

Open with the sound, not the spec. Tell the player what kind of instrument this is
and what it is good at. Then walk the signal, from the keys to the output, in the
order a player thinks about it.

Fetch real manuals as style and content references before you write. Good anchors:
the Yamaha DX7 owner's manual and the Reface DX, the Korg opsix and Volca FM, the
Roland System-8 or JU-06, the Sonicware Liven series, and the Mutable Instruments
Plaits and Braids manuals. Read how they describe a parameter: one short sentence
for what it is, one for what you hear when you turn it. Copy that shape, never
their prose or their brand voice. Consult, do not derive.

For every parameter, answer three questions in plain words:

1. What it does.
2. What you hear when you change it.
3. What the ends of the range sound like.

Example of the shape, from an FM level parameter: "Operator level. This sets how
loud operator 1 is inside the voice. At 99 it rings clearly, at 50 it is about 12
decibels quieter, at 0 it is silent." Two sentences, concrete, no theory.

Name the operators and the parts the way the panel names them. If the panel says
OP1 through OP4, the manual says OP1 through OP4. Do not invent new names.

## The panel reference

A fresh reader must be able to find any function without guessing. For each control
give its kind (knob, button, key, encoder), what it does on each page, and how to
reach every page. State the save flow exactly: which buttons, in what order, what
the screen confirms. Note the key combinations as combos, not as code.

Popups are worth a sentence: they own the controls while open, they close on their
own after about three seconds of no input, and a cancel does not lose work.

## The MIDI and SysEx reference

State the receive channels, the CC to parameter map, sustain, panic, pitch bend,
and program change. Then the SysEx format: the header, the command byte, the data
layout, and the exact bytes of each of the five commands the firmware answers. A
user who wants to back up patches with a SysEx librarian must be able to do it from
this page alone. Use tables for the maps, keep the prose around them short.

## The patch sheet

Fetch a few real patch sheets for comparable instruments (DX7, Volca FM, opsix) to
see how they lay out one patch per page. Then build a blank template for this
project with a row for every parameter, in the same order the panel walks them.
Leave room for a name, the algorithm, and a comment. Make it printable.

## Installation

Two paths, both explained for a non-programmer: flashing the firmware, and opening
the web app. For flashing, give the exact command and the exact recovery step if
something goes wrong. For the web app, give the URL and the one thing to click. Do
not assume the reader knows what a terminal is.

## Release notes

One section per version, newest first, with the version number and a date. Write
for the person updating: what changed, what they will notice, and whether a saved
patch still loads. Keep each entry to a few lines. This is the one place a
"changed from X to Y" sentence is correct, because it is a changelog by definition.

## The writing craft

This is the humanisation part, the anti-slop part. Apply it to every page. It is a
distillation of the humanizer skill's pattern catalogue, aimed at technical prose,
plus what good hardware manuals already do.

**Address the reader as "you".** "Turn the knob" beats "the user turns the knob".
Put the player in the room.

**Active voice, named actors.** "Hold SHIFT and press SAVE" beats "the save
function is triggered by pressing the button". The instrument is the actor where
there is no person, and that is fine, the instrument is the thing the reader owns.

**Concrete over abstract.** "The low end thins out" beats "the timbre becomes
brighter". Give a number where there is a number. A sentence that could describe
any synthesizer describes none.

**One point per sentence.** When a sentence has three clauses, it is two sentences.
Let a short sentence land next to a long one. Vary the length on purpose.

**Plain words over jargon.** The exact term stays where the panel uses it. Do not
invent synonyms for "operator" or "algorithm". Everything else gets the plain word.

**Kill the filler.** Delete "in order to", "it is worth noting", "in the context
of", "utilize". Delete the summary sentence that restates the heading. Delete the
opening that promises what is coming. Start with the content.

**No hedging stacks.** Commit to what you know. One genuine uncertainty is fine,
two qualifiers are slop. This is an instrument manual, not a research paper.

**No rule of three padding.** List the real items, two or four is fine. Three
abstract nouns in a row is a tell.

**No promotion.** "Seamless", "robust", "state of the art", "unleash" have no place
next to a knob. Say what it does, let the player decide if it is good.

**Read it back as speech.** If you cannot imagine a patient teacher saying the
sentence out loud, rewrite it.

## The no information loss check

After you write a page, go back paragraph by paragraph. For each original paragraph,
name its facts and compare them to what you wrote. If a fact did not survive, put it
back, in the new voice. This is not optional. A humanised page that dropped the
SysEx checksum is a broken page.

Checklist for the final pass:

- [ ] Every fact from the source is present or deliberately scoped out with a reason.
- [ ] The page uses the right register from `references/voice.md`.
- [ ] No em dash anywhere. No semi-colon anywhere.
- [ ] Every parameter, control, and command is named exactly as the panel names it.
- [ ] The current state only. Release notes excepted, no "now uses", "was added",
      "previously".
- [ ] A reader who has never seen the code can follow it.

## Credits and licences

When you fetch a real manual or patch sheet, you consult it for shape and approach.
You do not copy its prose or its layout verbatim. If you adapt a specific diagram or
table closely, credit the maker and note the licence in the project's LICENSING file,
the same rule the development skill applies to code. A manual's ideas are generally
facts you restate, not text you reproduce.
