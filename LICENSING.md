# Licensing

umetate is **GPL-3.0-only** for project code, documentation, and skills. Third-party
terms are preserved. RIB is a source-owned fork of Dinghy/Felucca; Dinghy is
lineage, not the product boundary.

## Dependencies and derivations by licence

| Material | Version | Licence |
| --- | --- | --- |
| Python | ≥ 3.11 | PSF |
| Node | ≥ 20 | MIT |
| Git | ≥ 2.30 | GPL-2.0-only |
| Emscripten | 6.0.13 | MIT / vendor |
| CMake | ≥ 3.20 | BSD-3-Clause |
| Ninja | any | Apache-2.0 |
| cc / gcc / clang | — | GPL / Apache-2.0 / other |
| JieLi pi32v2 toolchain | jieli-linux-toolchains-20260730.1 | vendor terms |
| Pillow | 13.0.0 | HPND |
| jsonschema | 4.26.0 | MIT |
| mido (optional) | 1.3.3 | MIT |
| python-rtmidi (optional) | 1.5.8 | MIT |
| Dinghy app/host/docs | zvenson | GPL-3.0-only |
| Felucca platform (hal/, loader/, crt0.S, app.ld) | @kurogedelic / Hügelton Instruments | GPL-3.0-only |
| Core-1 bring-up (`hal/fm1_cpu1.h`, `hal/fm1_cpu1.S`) | X0X (charlesvestal/fm1-x0x), Melodee (keremimo/melodee), Jangada (zednaked/jangada), via Felucca | GPL-3.0-only |
| SLOOP platform changes | isod89 | GPL-3.0-only |
| FM-1 emu | joakimeriksson | GPL-3.0-only |
| SMK-37 board layer + fm1-to-smk37 port kit | M. Geisler (genkigenki/makkuro) | GPL-3.0-only |
| TRS MIDI IN ring read | Felucca / sloopDX / ChanceTheMaker | GPL-3.0-only |
| Update loader screen | zvenson / illuminus5 (Skiff) | GPL-3.0-only |
| Terminus font 8×16 | Terminus project | SIL OFL 1.1 |
| KISS FFT (`vendor/kiss_fft/`) | Mark Borgerding | BSD-3-Clause |
| JieLi AC79 SDK math (`vendor/jieli/fftvec_math_drv.h`, `flfft_core_pi32v2.c`) | JieLi | Apache-2.0 |
| JieLi AC79 SDK assets (uboot.boot, cfg_tool.bin, eq_cfg_hw.bin) | JieLi | Apache-2.0 |

## Non-redistribution

The JieLi pi32v2 toolchain is **not redistributed** — the user obtains it and
`umetate setup` installs it into the Docker volume (vendor-terms compliance). The
AC79 SDK is Apache-2.0: its **binary assets** (uboot.boot, cfg_tool.bin,
eq_cfg_hw.bin) and the precompiled FFT library (`libFFT_pi32v2_OnChip.a`) are read
from the user's SDK checkout at build time, not stored here; the small **C math
source** we compile (kiss_fft under BSD-3, and `fftvec_math_drv.h` +
`flfft_core_pi32v2.c` under Apache-2.0) is vendored under `firmware/vendor/` with
its licences. M-VAVE stock firmware and assets are **not redistributed**. Record
the exact toolchain/SDK commit and asset hashes in `env.lock`.
