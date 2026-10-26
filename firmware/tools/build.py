#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
"""Build RIB app, update loader and installable .fwsc packages.

  tools/build.py [--release X.Y[-suffix]] [--board fm1|smk37] [--model pro|elite|mke]

The default target profile remains the existing -Os build. The opt-in performance profile isolates DSP code in
its own translation unit and places its executable routines in SRAM; it is a code-generation experiment, not
hardware acceptance. The JieLi toolchain is Linux x86-64 only; macOS uses Docker linux/amd64.
"""
import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
FW = SRC
OUT = Path(os.environ.get("UMETATE_OUT", SRC / "build")).resolve()
GEN = OUT / "gen"
LDR = OUT / "loader"
DSP_PROFILE = "baseline"
sys.path.insert(0, str(SRC / "tools"))
import fm1pkg_make  # noqa: E402
import lz4blk  # noqa: E402

APP_XIP = 0x02000120
APP_SLOT = fm1pkg_make.APP_SLOT
LOADER_LOAD = 0x01C0A800
LOADER_NAME = b"usb_hid_ota.bin"
CFLAGS = ["-Os", "-ffunction-sections", "-fno-builtin", "-Wall", "-Wno-unused-function"]  # retain platform/USB -Os
LINE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*\t(.*)$")
SDK_SHA256 = {
    "uboot.boot": "4e3b4c220dc96641cb5a723f41e68ce41d5261ae9434bb33fbd7f2c59976ded4",
    "cfg_tool.bin": "276579954f076886a6a7694f65dc71c034a63a2c204b76749065c0ac7b010d1b",
    "cfg/eq_cfg_hw.bin": "41167491bffed4651750719c973d2758adeb9021a5670d02d6a53c85ed80ea7d",
}
BOARD = "fm1"
BOARD_PREFIX = {"fm1": "FM-1_99", "smk37": "SMK-37 Pro_99"}
BOARD_DEFS = {"fm1": [], "smk37": ["-DBOARD_SMK37=1"]}
MODELS = {"pro": "SMK-37 Pro", "elite": "SMK-37 Elite", "mke": "MKE-P37"}
DATA_FAMILY = "RIB"
SCREEN_NAME = "RIB"
SCREEN_COLOUR = 0xB47F
PRODUCT = "FM-1_990"
VERSION = None


def package_filename(board, model, release=None):
    """Installable package name; the on-device identity stays separate and frozen."""
    stem = f"umetate-{board}-{model}"
    if release:
        stem += f"-{release}"
    return f"{stem}.fwsc"


def toolchain():
    value = os.environ.get("JIELI_TOOLCHAIN")
    if not value or not (Path(value) / "pi32v2" / "bin" / "clang").exists():
        raise SystemExit("JIELI_TOOLCHAIN must point at the JieLi Linux toolchain (pi32v2/ and common/)")
    return Path(value).resolve()


def tc(tool, *args):
    """Run a toolchain binary with cwd SRC (inside the build container)."""
    if tool == "cc":
        tool = "pi32v2/bin/clang"
        args = ("-target", "pi32v2", *args)
    cmd = [str(toolchain() / tool), *[str(a) for a in args]]
    result = subprocess.run(cmd, cwd=SRC, capture_output=True, text=True)
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"build: {tool} failed")
    if result.stderr.strip():
        sys.stderr.write(result.stderr)
    return result.stdout


def tc_all(*commands):
    with ThreadPoolExecutor(len(commands)) as executor:
        return list(executor.map(lambda command: tc(*command), commands))


def crc16(data, crc=0):
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    return crc


def ldr_head(data_crc, address, size, attr, name):
    body = struct.pack("<HIIBBH16s", data_crc, address, size, attr, 0, 0, name)
    return struct.pack("<H", crc16(body)) + body


def ldr_wrap(image):
    """Wrap the RAM loader in the outer JLFS head and 4 KiB LZ4 blocks."""
    blocks = bytearray()
    for offset in range(0, len(image), 4096):
        raw = image[offset:offset + 4096]
        compressed = lz4blk.compress(raw)
        if len(compressed) > 4096 or lz4blk.decompress(compressed) != raw:
            raise SystemExit(f"loader: block {offset // 4096} does not compress below 4096 B")
        blocks += struct.pack("<II", len(compressed), len(raw)) + compressed
    inner = ldr_head(crc16(image), len(image), LOADER_LOAD, 0, LOADER_NAME)
    body = inner + bytes(blocks)
    return ldr_head(crc16(body), 0x20, len(body), 0x41, LOADER_NAME) + body


def build_loader():
    LDR.mkdir(parents=True, exist_ok=True)
    source = FW / "loader"
    flags = [*CFLAGS, *BOARD_DEFS[BOARD], "-Ihal", "-Isrc", f'-DLDR_NAME="{SCREEN_NAME}"',
             f"-DLDR_COLOUR={SCREEN_COLOUR:#x}u"]
    tc_all(("cc", "-c", source / "crt0_ldr.S", "-o", LDR / "crt0_ldr.o"),
           ("cc", *flags, "-c", source / "loader.c", "-o", LDR / "loader.o"))
    elf = LDR / "loader.elf"
    tc("pi32v2/bin/ld", "--gc-sections", "-e", "_start", "-T", source / "loader.ld",
       LDR / "crt0_ldr.o", LDR / "loader.o", "-o", elf)
    _, disassembly, headers, symbols = tc_all(
        ("common/bin/objcopy", "-O", "binary", "-j", ".text", elf, LDR / "loader.bin"),
        ("common/bin/objdump", "-d", elf), ("common/bin/objdump", "-h", elf), ("common/bin/objdump", "-t", elf))
    (LDR / "loader.dis").write_text(disassembly)
    for line in headers.splitlines():
        fields = line.split()
        if len(fields) > 4 and fields[1].startswith(".") and int(fields[3], 16) >= 0x02000000 and int(fields[2], 16):
            raise SystemExit(f"loader: section {fields[1]} at {fields[3]} is outside RAM")
    image = (LDR / "loader.bin").read_bytes()
    if not image or len(image) > 0x14000:
        raise SystemExit("loader: image empty or too big")
    ota = ldr_wrap(image)
    (LDR / "ota.bin").write_bytes(ota)
    bss = [int(line.split()[0], 16) for line in symbols.splitlines() if line.rstrip().endswith("_bss_end")]
    print(f"loader: image {len(image)} B at {LOADER_LOAD:#x}" + (f", bss end {bss[0]:#x}" if bss else ""))
    print(f"loader: ota.bin {len(ota)} B")
    return ota


def build_app():
    flags = [*CFLAGS, *BOARD_DEFS[BOARD], "-DFM1_CPU1_USED=1", "-Ihal", "-Isrc", "-Igen", "-Ivendor",
             f'-DFELUCCA_ID="{PRODUCT}"', f'-DAPP_VER="{VERSION or "0.0"}"']
    if BOARD == "smk37":
        if not re.fullmatch(r"[A-Z0-9]{1,7}", DATA_FAMILY):
            raise SystemExit("DATA_FAMILY: 1..7 of A-Z 0-9")
        flags.append(f'-DDATA_FAMILY="{DATA_FAMILY}"')
    flags += os.environ.get("UMETATE_DEFS", "").split()
    commands = [("cc", "-c", FW / "crt0.S", "-o", OUT / "crt0.o"),
                ("cc", "-c", FW / "hal" / "fm1_vec.S", "-o", OUT / "fm1_vec.o"),
                ("cc", "-c", FW / "hal" / "fm1_isr.S", "-o", OUT / "fm1_isr.o"),
                ("cc", "-c", FW / "hal" / "fm1_cpu1.S", "-o", OUT / "fm1_cpu1.o"),
                ("cc", *flags, "-c", FW / "src" / "rib.c", "-o", OUT / "rib.o")]
    if DSP_PROFILE == "performance":
        dsp_flags = [*flags, "-O3", "-mcpu=r3", "-mfprev1", "-DUMETATE_TARGET_DSP=1",
                     "-c", FW / "src" / "rib_dsp.c", "-o", OUT / "rib_dsp.o"]
    else:
        dsp_flags = [*flags, "-c", FW / "src" / "rib_dsp.c", "-o", OUT / "rib_dsp.o"]
    commands.append(("cc", *dsp_flags))
    tc_all(*commands)

    elf = OUT / "rib.elf"
    linker = FW / "app.ld"
    if APP_SLOT != 0x8DFBC:
        text = linker.read_text()
        if text.count("LENGTH = 0x8DFBC") != 1:
            raise SystemExit("app.ld: the XIP LENGTH line was not found")
        linker = OUT / "app.ld"
        linker.write_text(text.replace("LENGTH = 0x8DFBC", f"LENGTH = {APP_SLOT:#x}"))
    tc("pi32v2/bin/ld", "--Map", OUT / "rib.link.map", "--gc-sections", "-e", "_start", "-T", linker,
       OUT / "crt0.o", OUT / "fm1_vec.o", OUT / "fm1_isr.o", OUT / "fm1_cpu1.o", OUT / "rib.o", OUT / "rib_dsp.o", "-o", elf)
    for section in ("text.bin", "data.bin", "ramtext.bin", "c1.bin", "dsp.bin"):
        (OUT / section).unlink(missing_ok=True)
    *_, symbols, disassembly, ram_disassembly = tc_all(
        ("common/bin/objcopy", "-O", "binary", "-j", ".text", elf, OUT / "text.bin"),
        ("common/bin/objcopy", "-O", "binary", "-j", ".data", elf, OUT / "data.bin"),
        ("common/bin/objcopy", "-O", "binary", "-j", ".ram_text", elf, OUT / "ramtext.bin"),
        ("common/bin/objcopy", "-O", "binary", "-j", ".c1_text", elf, OUT / "c1.bin"),
        ("common/bin/objcopy", "-O", "binary", "-j", ".dsp_text", elf, OUT / "dsp.bin"),
        ("common/bin/objdump", "-t", elf), ("common/bin/objdump", "-d", elf),
        ("common/bin/objdump", "-d", "-j", ".ram_text", elf))
    (OUT / "rib.dis").write_text(disassembly)
    (OUT / "symbols.txt").write_text(symbols)
    (OUT / "ramtext.dis").write_text(ram_disassembly)
    (OUT / "rib.map").write_text("\n".join([
        f"board={BOARD}", f"profile={DSP_PROFILE}", f"linker_script={linker}", f"app_xip={APP_XIP:#010x}",
        f"app_slot={APP_SLOT:#x}", f"toolchain={toolchain()}", "target=-target pi32v2", "",
        "--- linker map ---", (OUT / "rib.link.map").read_text(), "--- linker symbols ---", symbols,
        "--- section headers ---", tc("common/bin/objdump", "-h", elf)
    ]))

    def symbol_value(name):
        match = re.search(r"^([0-9a-f]+) .*\s" + name + r"$", symbols, re.M)
        if not match:
            raise SystemExit(f"linker symbol {name} is missing")
        return int(match.group(1), 16)

    image = bytearray((OUT / "text.bin").read_bytes())
    for section, load_symbol in (("ramtext.bin", "_rt_load"), ("c1.bin", "_c1_load"), ("dsp.bin", "_dsp_load"), ("data.bin", "_data_load")):
        load = symbol_value(load_symbol)
        if load % 4:
            raise SystemExit(f"{load_symbol} {load:#x} is not word aligned")
        blob = (OUT / section).read_bytes() if (OUT / section).exists() else b""
        if blob:
            expected = APP_XIP + len(image)
            if load != expected:
                raise SystemExit(f"{load_symbol} {load:#x} is not contiguous with prior load image at {expected:#x}")
            image += blob
    image += b"\xff" * (-len(image) % 4)
    (OUT / "rib.bin").write_bytes(image)
    return bytes(image), symbols, disassembly, ram_disassembly


def check(image, symbols, disassembly, ram_disassembly):
    errors, notes = [], []
    start = re.search(r"^([0-9a-f]+) .*\s_start$", symbols, re.M)
    if not start or int(start.group(1), 16) != APP_XIP:
        errors.append(f"_start is not at {APP_XIP:#x}")
    if image[:4] != bytes.fromhex("04818000"):
        errors.append(f"image starts with {image[:4].hex()}, not the entry stub")
    ram_calls = [line for line in ram_disassembly.splitlines() if re.search(r"\bcall\b", line)]
    if ram_calls:
        errors.append(f".ram_text contains calls: {ram_calls[:3]}")
    else:
        notes.append(f".ram_text: {len([line for line in ram_disassembly.splitlines() if LINE.match(line)])} insns, no calls")
    for line in disassembly.splitlines():
        match = LINE.match(line)
        if not match:
            continue
        for value in re.findall(r"= (-?\d+) <|call -?\d+ <[^:>]*: ([0-9a-f]+) >", match.group(3)):
            address = (int(value[0]) & 0xFFFFFFFF) if value[0] else int(value[1], 16) & 0xFFFFFFFF
            if 0xFFC00000 <= address < 0xFFD00000:
                errors.append(f"reference to ROM address {address:#010x}")
    if len(image) > APP_SLOT:
        errors.append(f"image {len(image)} B exceeds the app slot")

    def symbol(name):
        match = re.search(r"^([0-9a-f]+) .*\s" + name + r"$", symbols, re.M)
        return int(match.group(1), 16) if match else 0

    ram_end, pool_end = symbol("_bss_end"), symbol("_pool_end")
    ram, pool = ram_end - 0x01C08000, pool_end - 0x01C20000
    dsp_start, dsp_end = symbol("_dsp_start"), symbol("_dsp_end")
    dsp_size = dsp_end - dsp_start
    notes.append(f"profile={DSP_PROFILE}; image {len(image)} B of {APP_SLOT}; RAM through .bss {ram} B of 98304; pool {pool} B of 344064; .dsp_text {dsp_size} B in SRAM")
    if ram_end and not 0x01C08000 <= ram_end <= 0x01C20000:
        errors.append(f"RAM through .bss ends at {ram_end:#x}, outside app RAM")
    if ram > 96 * 1024:
        errors.append(f"RAM through .bss {ram} B > 96 KiB")
    if DSP_PROFILE == "performance" and dsp_size <= 0:
        errors.append("performance profile: .dsp_text is empty")
    if dsp_size > 0 and not (0x01C08000 <= dsp_start < dsp_end <= 0x01C20000):
        errors.append(f".dsp_text [{dsp_start:#x}, {dsp_end:#x}) is outside app RAM")
    if pool_end and not 0x01C20000 <= pool_end <= 0x01C74000:
        errors.append(f"pool ends at {pool_end:#x}, outside pool region")
    if pool > 344 * 1024:
        errors.append(f"pool {pool} B > 336 KiB")
    if DSP_PROFILE == "performance":
        dsp_calls = []
        for line in disassembly.splitlines():
            match = LINE.match(line)
            if not match or not dsp_start <= int(match.group(1), 16) < dsp_end:
                continue
            if not re.search(r"\b(?:call|goto)\b", match.group(3)):
                continue
            targets = re.findall(r"(?:call|goto)\s+(-?\d+)\s+<", match.group(3))
            if any(not dsp_start <= (int(target) & 0xFFFFFFFF) < dsp_end for target in targets):
                dsp_calls.append(line)
            elif not targets and re.search(r"\bcall\b", match.group(3)):
                dsp_calls.append(line)
        if dsp_calls:
            errors.append(f".dsp_text calls/branches outside SRAM DSP section: {dsp_calls[:3]}")
        data_load = symbol("_data_load")
        data_start = symbol("_data_start")
        data_end = symbol("_data_end")
        if data_end > data_start and APP_XIP <= data_load < APP_XIP + len(image):
            notes.append("DSP profile: inspect map/disassembly for XIP literal references before device acceptance")
        if re.search(r"<[^>]*>:\\s*\\n(?:[0-9a-f]+:.*\\n)*?\\s*(?:call|goto).*?(?:0x)?0*20[0-9a-f]{5}",
                     disassembly, re.S | re.I):
            errors.append("DSP profile disassembly references XIP from executable code; inspect instruction and data reachability")
    return errors, notes


MMIO_LIT = re.compile(r"\b0x0*(1[0-3][0-9a-f]{3}|4[0-3][0-9a-f]{3}|5[01][0-9a-f]{3}|1ee[0-9a-f]{4}|1c7f[0-9a-f]{3}|20[0-9a-f]{5})u?l?\b", re.I)
MMIO_CAST = re.compile(r"\(\s*(?:const\s+)?volatile\b[^()]*\*\s*\)(?!\s*&)")
MMIO_ASM = re.compile(r"\b(?:__asm__|asm)\b(?!\s+volatile\s*\(\s*\"\"\s*:::\s*\"memory\"\s*\))")


def mmio_check():
    def strip_comments(text):
        text = re.sub(r"/\*.*?\*/", lambda match: "\n" * match.group(0).count("\n"), text, flags=re.S)
        return re.sub(r"//[^\n]*", "", text)

    definitions = {}
    for header in sorted((FW / "hal").glob("*.h")):
        for match in re.finditer(r"^#define\s+(\w+)(?:\([^)]*\))?\s+(.*)$", strip_comments(header.read_text()), re.M):
            definitions[match.group(1)] = match.group(2)
    registers = {name for name, body in definitions.items() if re.search(r"\bvolatile\b", body)}
    while True:
        more = {name for name, body in definitions.items() if name not in registers and set(re.findall(r"\w+", body)) & registers}
        if not more:
            break
        registers |= more
    errors = []
    source_files = [*(FW / "src").glob("*.[ch]"), *(FW / "loader").glob("*.c")]
    for source in sorted(source_files):
        for number, line in enumerate(strip_comments(source.read_text()).splitlines(), 1):
            location = f"{source.relative_to(FW)}:{number}"
            for regex, kind in ((MMIO_LIT, "register/window address"), (MMIO_CAST, "volatile pointer cast"),
                                (MMIO_ASM, "inline asm")):
                match = regex.search(line)
                if match:
                    errors.append(f"{location}: {kind} outside hal/ ({match.group(0).strip()}); add a hal/ helper")
            used = set(re.findall(r"\b[A-Z_][A-Z0-9_]*\b", line)) & registers
            if used:
                errors.append(f"{location}: HAL register macro {sorted(used)[0]} outside hal/; use a hal/ helper")
    return errors


def main():
    global PRODUCT, VERSION, BOARD, APP_SLOT, DSP_PROFILE
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", metavar="X.Y", help="release build: identity FM-1_99Y, version string X.Y")
    parser.add_argument("--board", choices=sorted(BOARD_PREFIX), default=None)
    parser.add_argument("--model", choices=sorted(MODELS), default=None)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--profile", choices=("baseline", "performance"), default=os.environ.get("UMETATE_PROFILE", "baseline"))
    parser.add_argument("--report-config", action="store_true")
    args = parser.parse_args()
    BOARD = (args.board or os.environ.get("BOARD") or "fm1").lower().replace("-", "")
    if BOARD not in BOARD_PREFIX:
        raise SystemExit(f"BOARD={BOARD}: use fm1 or smk37")
    model = (args.model or os.environ.get("MODEL") or "pro").lower()
    if model not in MODELS or (model != "pro" and BOARD != "smk37"):
        raise SystemExit(f"MODEL={model}: pro, elite or mke, with BOARD=smk37")
    fm1pkg_make.set_board(BOARD)
    APP_SLOT = fm1pkg_make.APP_SLOT
    if model != "pro":
        BOARD_DEFS[BOARD] = [*BOARD_DEFS[BOARD], f'-DSMK_MODEL="{MODELS[model]}"']
        BOARD_PREFIX[BOARD] = BOARD_PREFIX[BOARD].replace("SMK-37 Pro", MODELS[model])
    PRODUCT = BOARD_PREFIX[BOARD] + "0"
    VERSION = None
    package_file = package_filename(BOARD, model)
    if args.release:
        release = re.fullmatch(r"(\d)\.(\d)(\.\d)?(-[A-Za-z0-9]+)?", args.release)
        if not release:
            raise SystemExit(f"--release {args.release}: use X.Y, X.Y.Z or X.Y-suffix, one digit each")
        PRODUCT = BOARD_PREFIX[BOARD] + release[2]
        VERSION = release[1] + "." + release[2] + (release[3] or "")
        package_file = package_filename(BOARD, model, args.release)
    fm1pkg_make.SDK = args.sdk
    DSP_PROFILE = args.profile
    if args.report_config:
        print(f"profile={DSP_PROFILE}; board={BOARD}; model={model}; target=-target pi32v2")
        print("app/platform/USB: " + " ".join(CFLAGS))
        print("DSP: " + ("-Os baseline" if DSP_PROFILE == "baseline" else "-O3 -mcpu=r3 -mfprev1 with SRAM .dsp_text placement"))
        print("CPU clock inherited from the bootloader (240/320/360 MHz by revision); voltage changes and two-core execution are unconfigured and device-unverified")
        return 0
    for relative, expected in SDK_SHA256.items():
        actual = hashlib.sha256(fm1pkg_make.sdk_file(relative)).hexdigest()
        status = "ok" if actual == expected else "warning: differs from AC79NN_SDK_V1.2.1"
        print(f"SDK SHA-256 {status}: {relative} {actual}")
    OUT.mkdir(parents=True, exist_ok=True)
    loader = build_loader()
    image, symbols, disassembly, ram_disassembly = build_app()
    errors, notes = check(image, symbols, disassembly, ram_disassembly)
    errors.extend(mmio_check())
    for note in notes:
        print("  ok   ", note)
    for error in errors:
        print("  FAIL ", error)
    if errors:
        raise SystemExit("build: checks failed")
    package = fm1pkg_make.ufw(fm1pkg_make.flash_image(image, fm1pkg_make.KEY), loader, PRODUCT)
    (OUT / package_file).write_bytes(package)
    print(f"app      {OUT / 'rib.bin'}  {len(image)} B")
    print(f"loader   {LDR / 'ota.bin'}  {len(loader)} B")
    print(f"package  {OUT / package_file}  {len(package)} B identity {PRODUCT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
