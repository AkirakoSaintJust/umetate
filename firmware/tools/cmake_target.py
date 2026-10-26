#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CMake adapter for RIB's checked JieLi app/loader/package build."""
import argparse
import hashlib
import os
import re
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("build", "check"))
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--board", choices=("fm1", "smk37"), required=True)
    parser.add_argument("--model", choices=("pro", "elite", "mke"), default="pro")
    parser.add_argument("--profile", choices=("baseline", "performance"), default="baseline")
    parser.add_argument("--release")
    parser.add_argument("--defs", default="")
    parser.add_argument("--docker", action="store_true")
    parser.add_argument("--docker-image", default="umetate-host-build:latest")
    parser.add_argument("--sdk-assets", type=Path,
                        help="directory containing uboot.boot, cfg_tool.bin, cfg/eq_cfg_hw.bin")
    args = parser.parse_args()
    if args.model != "pro" and args.board != "smk37":
        parser.error("non-pro models require --board smk37")

    root = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    sdk_assets = (args.sdk_assets or args.sdk / "cpu" / "wl82" / "tools").resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "UMETATE_OUT": str(out), "UMETATE_PROFILE": args.profile,
        "JIELI_TOOLCHAIN": str(args.toolchain.resolve()), "AC79_SDK": str(args.sdk.resolve()),
        "JIELI_DOCKER": "1" if args.docker else "0", "JIELI_DOCKER_IMAGE": args.docker_image,
    })
    if args.defs:
        os.environ["UMETATE_DEFS"] = args.defs
    else:
        os.environ.pop("UMETATE_DEFS", None)

    sys.path.insert(0, str(root / "tools"))
    import build as build_module

    build_module.OUT = out
    build_module.GEN = out / "gen"
    build_module.LDR = out / "loader"
    build_module.BOARD = args.board
    build_module.APP_SLOT = build_module.fm1pkg_make.BOARDS[args.board][1]
    build_module.DSP_PROFILE = args.profile
    build_module.fm1pkg_make.SDK = args.sdk.resolve()
    build_module.fm1pkg_make.sdk_file = lambda relative: (sdk_assets / relative).read_bytes()
    build_module.fm1pkg_make.set_board(args.board)
    if args.model != "pro" and args.board != "smk37":
        parser.error("non-pro models require --board smk37")
    if args.model != "pro":
        model_name = build_module.MODELS[args.model]
        build_module.BOARD_PREFIX[args.board] = "SMK-37 Elite_99" if args.model == "elite" else "MKE-P37_99"
        build_module.BOARD_DEFS[args.board] = ["-DBOARD_SMK37=1", f'-DSMK_MODEL="{model_name}"']
    if args.release:
        match = re.fullmatch(r"(\d)\.(\d)(\.\d)?(-[A-Za-z0-9]+)?", args.release)
        if not match:
            parser.error("--release: use X.Y, X.Y.Z or X.Y-suffix, one digit each")
        build_module.PRODUCT = build_module.BOARD_PREFIX[args.board] + match[2]
        build_module.VERSION = match[1] + "." + match[2] + (match[3] or "")
    else:
        build_module.PRODUCT = build_module.BOARD_PREFIX[args.board] + "0"
    package_name = build_module.package_filename(args.board, args.model, args.release)
    flags = [*build_module.CFLAGS, "-O3"]
    if args.profile == "performance":
        flags.extend(("-mcpu=r3", "-mfprev1", "-DUMETATE_TARGET_DSP=1"))
    print(f"profile={args.profile}; board={args.board}; model={args.model}; target=-target pi32v2")
    print("platform/USB/app flags: " + " ".join(build_module.CFLAGS))
    print("DSP flags: " + ("-Os baseline" if args.profile == "baseline" else " ".join(flags)))
    print("CPU clock inherited from the bootloader (240/320/360 MHz by revision); voltage changes and two-core execution are not configured or hardware-verified")
    for relative, expected in build_module.SDK_SHA256.items():
        actual = hashlib.sha256(build_module.fm1pkg_make.sdk_file(relative)).hexdigest()
        status = "ok" if actual == expected else "warning: differs from AC79NN_SDK_V1.2.1"
        print(f"SDK SHA-256 {status}: {relative} {actual}")

    if args.action == "build":
        loader = build_module.build_loader()
        app, symbols, disassembly, ram_disassembly = build_module.build_app()
        errors, notes = build_module.check(app, symbols, disassembly, ram_disassembly)
        errors.extend(build_module.mmio_check())
        for note in notes:
            print(f"ok {note}")
        if errors:
            for error in errors:
                print(f"FAIL {error}", file=sys.stderr)
            raise SystemExit("build: checks failed")
        package = build_module.fm1pkg_make.ufw(
            build_module.fm1pkg_make.flash_image(app, build_module.fm1pkg_make.KEY), loader,
            build_module.PRODUCT)
        package_path = out / package_name
        package_path.write_bytes(package)
        (out / "target-config.txt").write_text(
            f"board={args.board}\nmodel={args.model}\nprofile={args.profile}\n"
            f"identity={build_module.PRODUCT}\nrelease={args.release or 'development'}\n"
            f"toolchain={args.toolchain.resolve()}\nsdk={args.sdk.resolve()}\nsdk_assets={sdk_assets}\n"
            f"app={out / 'rib.bin'}\nloader={out / 'loader/ota.bin'}\npackage={package_path}\n"
            f"DSP flags={' '.join(flags) if args.profile == 'performance' else '-Os'}\n"
            f"DSP section={'.dsp_text SRAM' if args.profile == 'performance' else 'XIP baseline'}\n"
            f"platform flags={' '.join(build_module.CFLAGS)}\n"
            "clock_voltage=unconfigured; hardware acceptance blocked pending authoritative per-board evidence\n"
            "cores=unconfigured; RIB core topology/ownership not established\n")
        print(f"app {out / 'rib.bin'} {len(app)} B")
        print(f"loader {out / 'loader/ota.bin'} {len(loader)} B")
        print(f"package {package_path} {len(package)} B identity={build_module.PRODUCT}")
        print(f"map {out / 'rib.map'}")
        print(f"configuration {out / 'target-config.txt'}")
        return 0

    package_path = out / package_name
    required = (out / "rib.bin", out / "rib.elf", out / "symbols.txt", out / "rib.dis", out / "ramtext.dis",
                out / "rib.map", out / "rib.link.map", out / "loader/ota.bin",
                out / "loader/loader.elf", out / "loader/loader.bin", out / "loader/loader.dis",
                package_path, out / "target-config.txt")
    missing = [path for path in required if not path.is_file()]
    if missing:
        for path in missing:
            print(f"FAIL missing target artifact: {path}", file=sys.stderr)
        return 1
    empty = [path for path in required if path.stat().st_size == 0]
    if empty:
        for path in empty:
            print(f"FAIL empty target artifact: {path}", file=sys.stderr)
        return 1
    errors, notes = build_module.check((out / "rib.bin").read_bytes(), (out / "symbols.txt").read_text(),
                                       (out / "rib.dis").read_text(), (out / "ramtext.dis").read_text())
    errors.extend(build_module.mmio_check())
    config = (out / "target-config.txt").read_text().splitlines()
    expected = (f"board={args.board}", f"model={args.model}", f"profile={args.profile}",
                f"identity={build_module.PRODUCT}", f"release={args.release or 'development'}",
                f"sdk_assets={sdk_assets}")
    errors.extend(f"configuration mismatch: expected {line!r}" for line in expected if line not in config)
    dsp_binary = out / "dsp.bin"
    if args.profile == "performance":
        if "DSP section=.dsp_text SRAM" not in config:
            errors.append("configuration mismatch: performance profile lacks the SRAM DSP placement flag")
        if not dsp_binary.is_file() or dsp_binary.stat().st_size == 0:
            errors.append(f"FAIL missing or empty target artifact: {dsp_binary}")
    elif "DSP section=XIP baseline" not in config:
        errors.append("configuration mismatch: baseline profile does not record XIP placement")
    for artifact in (out / "rib.elf", out / "loader/loader.elf", out / "loader/loader.bin",
                     out / "loader/loader.dis", out / "loader/ota.bin", out / "rib.link.map"):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            errors.append(f"FAIL missing or empty target artifact: {artifact}")
    sys.path.insert(0, str(root / "tools"))
    import fm1_install

    package = package_path.read_bytes()
    try:
        actual_product = fm1_install.product_of(package)
        logical_package, _ = fm1_install.deinterleave(package)
        damage = fm1_install.package_damage(logical_package)
    except (ValueError, IndexError, struct.error, fm1_install.InstallError) as error:
        errors.append(f"package identity/integrity check failed: {error}")
    else:
        if actual_product != build_module.PRODUCT:
            errors.append(f"package identity mismatch: expected {build_module.PRODUCT!r}, got {actual_product!r}")
        if damage:
            errors.append(f"package integrity check failed: {damage}")
    for note in notes:
        print(f"ok {note}")
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"ok package {package_path}")
    print(f"ok map {out / 'rib.map'}")
    print(f"ok configuration {out / 'target-config.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
