<!-- GENERATED - do not edit. Source: docs/platform-facts.md. Regenerate with `python -m umetate._skill generate`. -->

# FM-1 / SMK-37 platform facts

These are the canonical, evidence-tagged hardware and platform facts used by the
roadmap, the tutorial, and the release checklist. Treat this as a reference:
[`roadmap.md`](roadmap.md) is the only status authority.

Confidence tags: `vendor` (JieLi AC79 docs), `stock-code` (stock FW/disassembly),
`source` (this repo), `community-measured` (one-unit record), `unverified` (no
primary source). A lower-confidence tag never overrides a higher one.

## 1. SoC, clock, FPU, cores

- **SoC:** JieLi AC791N / WL82, dual-core pi32v2 DSP, family max **320 MHz**.
  **single-precision float only** (no `double`, literals `1.0f`, else software
  double), hardware **FFT/IFFT + matrix**, AES/SHA/CRC16/random, **578 KB SRAM**
  (+ optional SDRAM). USB1.1/2.0. DAC/IIS/PDM/SPDIF audio. `vendor`
- **Clock is bootloader-dependent.** V13 app 240 MHz. V15 bootloader 360 MHz. V16
  bootloader 320 MHz. Setup offers **240 / 320** only: 320 is the rated max and
  passed a two-core 30-minute soak, 360 failed under load on one V15 unit, **396
  has no FM-1 evidence**. A soft reset keeps the PLL, power-cycle returns to the
  bootloader clock. `community-measured`
- **Dual-core split (AC79 §7.40, SDK-OS model, a vendor fact only):** `CPU_CORE_NUM 1`
  + single-core `system.a` + explicit `irq_info_table`. CPU1 runs `cpu1_main`, may
  not call OS APIs, `spin_lock` for exclusion, flash write suspends CPU1 unless its
  code is in RAM/SDRAM. **RIB does not use this**, it is bare-metal (links no
  `system.a`): core 1 runs `fm1_c1_main` via the Felucca `fm1_cpu1.h` raw-register
  start. `vendor`
- **FPU (AC79 §7.22):** single-precision hardware only. FM-1 enable/ABI/context is
  `not-run` until the target probe (P2-4). `vendor`

## 2. Build / toolchain

- Linux toolchain → **`/opt/jieli`** (contains `/opt/jieli/common/bin/clang`),
  `ulimit -n ≥ 8096`, `make`. Linux *compiles*, flashing needs `init_env.sh` +
  `download_linux.c`. `vendor`
- FM1 Open (flag authority): JieLi **Windows toolchain 2.5.3** (pi32v2 **clang
  4.0.1**, `-mcpu=r3 -mfprev1`, `-flto`). WASI SDK 27 for the web build. `stock-code`
- Flash line: `isd_download.exe isd_config.ini -tonorflash -dev wl82 -boot 0x1c02000
  … -uboot uboot.boot -app app.bin cfg_tool.bin …`. **SFC addresses only 16 MB.** `vendor`

## 3. Math / acceleration (AC79 §7.16)

- Hardware FFT: `jl_fft.c` (hw) / `kiss_fft.c` (sw) / `flfft_core_pi32v2.c` (float).
  Vector DSP: `nn_function_vec.c` (saturating, `q`-shift) and `jl_math.c`
  (`ASM_ENABLE` 1=sw/2=asm/3=hw). Trig: `driver/cpu/wl82/math/math.c`. `vendor`

## 4. Update, identity, recovery

- `.fwsc` carries a 27-byte zero-padded identity, parsed `([^_]+)_(\d+)`.
  `same_keyboard` + model check on **install and resume**, wrong model exits 6.
- Updates are **CRC-16 integrity, not authenticity**, no signature.
- USB update mode enumerates as **`WL82 UBOOT1.00 USB Device`**, `WL80UBOOT`/
  `4C4A:8057` also observed.
- **Recovery is a taxonomy**, not one button:
  | Route | Prerequisite | Status |
  | --- | --- | --- |
  | App-level USB rescue | app startup + RAM flash driver + USB stack | source, device `blocked` |
  | Automatic boot guard | boot guard intact | source, device `blocked` |
  | Boot-time `OCT−` | held at power-on | source, did not fire on MD-One's unit |
  | Running `OCT−`+`OCT+` held 5 s | running firmware servicing `platform_poll()` | source + host test, device `blocked` |
  | Update loader (`ota-<identity>`) | app accepted package, record written | resumes interrupted write |
  | Mask-ROM UBOOT / USB_KEY dongle | USB enumeration / RP2040 dongle | community-reported, last resort |
- **No full-flash backup** is a documented FM-1 capability, rollback = verified
  stock `.fwsc` + the applicable route. **No "three short flashes."**

## 5. Boot & flash

```text
Power on → Mask ROM → UBOOT ("uboot.boot", single-bank-OTA) → app (0x2000120, XIP)
                                     └→ update record set → ota loader ("ota-<identity>")
```

- **UBOOT variant is load-bearing:** `uboot.boot` is single-bank-OTA-capable.
  `uboot_no_ota.boot` is not. Keep `uboot.boot` byte-identical to the pinned SDK.
- **Memory:** XIP `0x02000000+`, internal RAM `0x1c00000` (CPU1 DSP), cache RAM
  `0x1f28000`. FM-1 flash is **1 MiB** (board map in `hal/fm1_flash_map.h`).
- **Flash mechanisms:**
  | Path | Format | Runs |
  | --- | --- | --- |
  | Update (primary) | `.fwsc` (CRC-16 + identity/model) | host-side Python installer over **USB-MIDI SysEx** (mido + python-rtmidi) |
  | Raw NOR (last resort) | `uboot.boot` + `app.bin` + `cfg_tool.bin` | `isd_download` / `jl-uboot-tool`, via the **USB_KEY dongle** |

## 6. Evidence vocabulary (defined once)

`pass` / `fail` / `blocked` / `not-applicable` / `not-run`. Layers: source/static,
host, browser/WASM, target package, emulator, physical timing, device acceptance,
release provenance. **A lower layer never proves a higher one.** The emulator is a
model layer (1.92× optimistic, cannot prove recovery/FPU/core-1/electrical).
