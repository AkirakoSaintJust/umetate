# Licensing

umetate is **GPL-3.0-only** for project code, documentation, and skills. Third-party
terms are preserved. RIB is a source-owned fork of Dinghy/Felucca. Dinghy is
lineage rather than the product boundary.

The firmware and the CLI are GPL-3.0-only. The VST3, CLAP and standalone plugin
binaries also link **JUCE 8.0.9**, which is dual-licensed under **AGPL-3.0-only**
or a commercial JUCE licence. A distributed plugin binary is therefore conveyed
under the AGPL-3.0-only terms for the JUCE part. The umetate source in the same
binary keeps its GPL-3.0-only terms, and GPLv3 section 13 permits the combination.
Anyone who cannot accept the AGPL terms needs a commercial JUCE licence before
shipping the plugin.

## Dependencies and derivations by licence

| Material | Version | Licence |
| --- | --- | --- |
| Python | ≥ 3.11 | PSF |
| Node | ≥ 20 | MIT |
| Git | ≥ 2.30 | GPL-2.0-only |
| Emscripten | 6.0.13 | MIT / vendor |
| CMake | ≥ 3.20 | BSD-3-Clause |
| Ninja | any | Apache-2.0 |
| cc / gcc / clang | - | GPL / Apache-2.0 / other |
| JieLi pi32v2 toolchain | jieli-linux-toolchains-20260730.1 | vendor terms |
| Pillow | 13.0.0 | HPND |
| jsonschema | 4.26.0 | MIT |
| mido (optional) | 1.3.3 | MIT |
| python-rtmidi (optional) | 1.5.8 | MIT |
| Dinghy app/host/docs | zvenson | GPL-3.0-only |
| Felucca platform (hal/, loader/, crt0.S, app.ld) | @kurogedelic / Hügelton Instruments | GPL-3.0-only |
| Core-1 bring-up (`hal/fm1_cpu1.h`, `hal/fm1_cpu1.S`) | X0X (charlesvestal/fm1-x0x), Melodee (keremimo/melodee), Jangada (zednaked/jangada), via Felucca | GPL-3.0-only |
| SLOOP platform changes | isod89 | GPL-3.0-only |
| FM-1 emu | joakimeriksson | MIT |
| SMK-37 board layer + fm1-to-smk37 port kit | M. Geisler (genkigenki/makkuro) | GPL-3.0-only |
| TRS MIDI IN ring read | Felucca / sloopDX / ChanceTheMaker | GPL-3.0-only |
| Update loader screen | zvenson / illuminus5 (Skiff) | GPL-3.0-only |
| Terminus font 8×16 | Terminus project | SIL OFL 1.1 |
| Digital Desolation Plus (the umetate logo's typeface) | UkiyoMoji Fonts | free, edit/derive/commercial/embed OK, credit requested |
| KISS FFT (`vendor/kiss_fft/`) | Mark Borgerding | BSD-3-Clause |
| JieLi AC79 SDK math (`vendor/jieli/math.h`, `fftvec_math_drv.h`, `flfft_core_pi32v2.c`) | JieLi | Apache-2.0 |
| JieLi AC79 SDK assets (uboot.boot, cfg_tool.bin, eq_cfg_hw.bin) | JieLi | Apache-2.0 |
| JUCE (plugin binary) | 8.0.9 | AGPL-3.0-only or commercial |
| VST3 SDK (bundled by JUCE) | 3.7.x as shipped in JUCE 8.0.9 | GPL-3.0-only or Steinberg VST3 licence |
| CLAP headers (plugin binary) | 1.2.7 | MIT |
| clap-juce-extensions | 7adee3a1bd4684d4caa5601100e364abccff4b4d | MIT |
| DotGothic16 font (plugin editor) | Google Fonts | SIL OFL 1.1 |
| Zen Dots font (plugin editor) | Google Fonts | SIL OFL 1.1 |
| Ardour (test host only, not distributed) | 8.12 | GPL-2.0-or-later |
| Carla (test host only, not distributed) | 2.6.0-alpha1 | GPL-2.0-or-later |
| JACK (test host only, not distributed) | 1.9.22 | LGPL-2.1-or-later |

## Plugin source and binaries

The plugin source is in the `plugin/` folder and is GPL-3.0-only. The build pins JUCE
8.0.9 and `clap-juce-extensions` commit
`7adee3a1bd4684d4caa5601100e364abccff4b4d` in `plugin/juce/CMakeLists.txt` and
fetches both with CMake `FetchContent`. CLAP 1.2.7 is a submodule of the
extension at that commit. The VST3 SDK is the copy bundled with JUCE 8.0.9.

A published plugin binary must travel with its corresponding source. Each plugin
archive also carries its notices in a `licences/` folder: the AGPL text for JUCE,
the MIT texts for CLAP and the wrapper, the OFL texts for the two embedded fonts,
and the project's GPL-3.0 text. The `umetate publish` tool always includes
`framework/plugin/` and `framework/design/` in the published tree, and writes
`DEPENDENCIES.md` with the exact upstream commits. The build fetch instructions
are in `framework/plugin/README.md`. If the AGPL source must be self-contained,
pass `--vendor-deps` with a directory that holds the fetched `_deps` sources, or
point the build at local copies with `-DFETCHCONTENT_SOURCE_DIR_JUCE=...` and
`-DFETCHCONTENT_SOURCE_DIR_CLAP-JUCE-EXTENSIONS=...`. When `--plugins` stages a
binary, the publish output also carries the AGPL, MIT CLAP, MIT wrapper and OFL
texts from `third-party-licenses/`. The release source archive includes
`vendor/deps/`, so the AGPL corresponding source travels in the same release.

The brand font is not bundled and the wordmark falls back to Arial Black when the
system has it. Only the two OFL fonts above travel in the plugin binary.

## Non-redistribution

The JieLi pi32v2 toolchain is **not redistributed**, so the user obtains it and
`umetate setup` installs it into the Docker volume (vendor-terms compliance). The
AC79 SDK is Apache-2.0: its **binary assets** (uboot.boot, cfg_tool.bin,
eq_cfg_hw.bin) and the precompiled FFT library (`libFFT_pi32v2_OnChip.a`) are read
from the user's SDK checkout at build time rather than stored here, whilst the small
**C math source** we compile (kiss_fft under BSD-3, and `fftvec_math_drv.h` +
`flfft_core_pi32v2.c` under Apache-2.0) is vendored under `firmware/vendor/` with
its licences. M-VAVE stock firmware and assets are **not redistributed**. Record
the exact toolchain/SDK commit and asset hashes in `env.lock`.

## Credits

VOPMex is the OPM emulator used as the reference for the comparison in
`docs/opm-to-type-p-fm1.md`. It is by osoumen, a fork of the original VOPM by sam.
The comparison measured its rendered output. VOPMex is not part of this
repository, the build, or any release, and none of its source is redistributed or
compiled into the instrument.

The FM-1 emulator used for the target timing checks is joakimeriksson's fm1-emu.
It is a development tool rather than a release artefact.
