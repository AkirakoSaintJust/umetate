# Type P.fm1 patch sheet

Print this and write one patch per page.

```
Patch name: ______________________   Part: __   Date: ________

ALGORITHM: 0 1 2 3 4 5 6 7   (circle one)

OPERATORS                  OP1     OP2     OP3     OP4
  ratio (0.50..16.00)        ____    ____    ____    ____
  level (0..99)              ____    ____    ____    ____
  feedback (0..100%)         ____    ____    ____    ____
  waveform (0..11)           ____    ____    ____    ____
  detune (-50..+50 cents)    ____    ____    ____    ____
  attack (0..99)             ____    ____    ____    ____
  decay 1 (0..99)            ____    ____    ____    ____
  decay 2 (0..99)            ____    ____    ____    ____
  release (0..99)            ____    ____    ____    ____
  level 1 (0..99)            ____    ____    ____    ____
  level 2 (0..99)            ____    ____    ____    ____
  level 3 (0..99)            ____    ____    ____    ____
  trem rate (Hz)             ____    ____    ____    ____
  trem depth (0..100%)       ____    ____    ____    ____
  mute (on/off)              ____    ____    ____    ____

VOICE MODE
  mode (poly/mono)                    ____
  unison count (1..8)                 ____
  unison detune (0..200 cents)        ____
  legato (on/off)                     ____
  portamento (off, 1..5000 ms)        ____
  note priority (last/highest/lowest) ____

FILTER 1
  cutoff (off, 1..100%)       ____
  resonance (0..100%)         ____
  type (lpf/bpf/hpf)          ____
  env depth (0..100%)         ____

FILTER 2
  cutoff (off, 1..100%)       ____
  resonance (0..100%)         ____
  type (lpf/bpf/hpf)          ____

WAVEFOLDER
  amount (0..100%)            ____
  threshold (0..100%)         ____
  folds (1..8)                ____

PITCH LFO                 PITCH ENVELOPE
  rate (Hz)               ____     on (on/off)             ____
  depth (0..100%)         ____     rate 1..4 (0..99)       ____ ____ ____ ____
  wave (0..11)            ____     level 1..3 (semitones)  ____ ____ ____

BREAKPOINT (note)         ____

Notes: __________________________________________________
       __________________________________________________
```

Ratio 1.00 is the unmodified base note frequency.
Ratio runs 0.50 to 16.00, levels and rates run 0 to 99, and feedback, wavefolder amount and depth run from 0 to
100%. Detune and unison detune are in cents.
