# Type P.fm1 patch sheet

Print this and write one patch per page.

```
Patch name: ______________________   Part: __   Date: ________

ALGORITHM: 0 1 2 3 4 5 6 7   (circle one)

OPERATORS               OP1     OP2     OP3     OP4
  ratio  (1.00 = unison) ____    ____    ____    ____
  level  (0..99)          ____    ____    ____    ____
  feedback (0..32767)     ____    ____    ____    ____
  waveform (0..11)        ____    ____    ____    ____
  detune  (-50..+50)      ____    ____    ____    ____
  attack  (rate 1)        ____    ____    ____    ____
  decay 1 (rate 2)        ____    ____    ____    ____
  decay 2 (rate 3)        ____    ____    ____    ____
  release (rate 4)        ____    ____    ____    ____
  level 1                 ____    ____    ____    ____
  level 2                 ____    ____    ____    ____
  level 3                 ____    ____    ____    ____
  trem rate               ____    ____    ____    ____
  trem depth              ____    ____    ____    ____
  mute (on/off)           ____    ____    ____    ____

VOICE MODE
  mode (poly/mono)        ____
  unison count (1..8)     ____
  unison detune           ____
  legato (on/off)         ____
  portamento              ____
  note priority           ____

FILTER 1                 FILTER 2
  cutoff                  ____     cutoff                  ____
  resonance               ____     resonance               ____
  type (LP/BP/HP)         ____     type (LP/BP/HP)         ____
  env depth               ____

WAVEFOLDER
  amount                  ____
  threshold               ____
  folds (1..8)            ____

PITCH LFO                 PITCH ENVELOPE
  rate                    ____     on (on/off)             ____
  depth                   ____     rate 1..4               ____ ____ ____ ____
  wave                    ____     level 1..3              ____ ____ ____

BREAKPOINT (note)         ____

Notes: __________________________________________________
       __________________________________________________
```

A ratio of 1.00 is written 65536 in the panel's raw value. Levels and rates are
0 to 99. Feedback, wavefolder amount, and depth values are 0 to 32767, where the
middle is half. Detune is cents.
