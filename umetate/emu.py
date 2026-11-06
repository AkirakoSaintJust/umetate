# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate emu`: run the firmware in fm1-emu.

The default GUI runs `fm1-live --fwsc <built .fwsc>` in an emulated FM-1 window.
Play with the computer keyboard, the mouse, or a MIDI keyboard, and hear the
audio on the default device. `--persist` keeps the flash chip between runs.

`--check` is headless: `fm1-live --shot` boots the package, holds a chord, and
writes the panel and the audio peak, which is the model-layer regression. The
`fm1-emu` batch interpreter is built too, for deeper WAV and histogram runs.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import _emu

_ROOT = Path(__file__).resolve().parents[1]
_BUILD = _ROOT / "firmware" / "build"


def _default_fwsc(board: str, build: Path | None = None) -> Path:
    """The built package to boot: the newest composed synth package (the product
    firmware, `umetate build --synth` names it with the synth's stem), else the
    demo package."""
    build = build or _BUILD
    synth = sorted(
        build.glob(f"umetate-{board}-pro-*.fwsc"),
        key=lambda p: p.stat().st_mtime,
    )
    if synth:
        return synth[-1]
    return build / f"umetate-{board}-pro.fwsc"


def _flash(args: argparse.Namespace) -> str:
    return str(_emu.EMU_DIR / f"flash-{args.board}.bin")


def _gui(args: argparse.Namespace, fwsc: Path) -> int:
    cmd = [str(_emu.LIVE_BIN), "--fwsc", str(fwsc)]
    if args.persist:
        cmd += ["--flash", _flash(args)]
    if args.midi:
        cmd += ["--midi", str(args.midi)]
    if args.mhz:
        cmd += ["--mhz", str(args.mhz)]
    print(f"emu: {_emu.LIVE_BIN.name} --fwsc {fwsc}")
    return subprocess.run(cmd, cwd=_emu.EMU_DIR).returncode


def _check(args: argparse.Namespace, fwsc: Path) -> int:
    out = _ROOT / "build" / "emu"
    out.mkdir(parents=True, exist_ok=True)
    panel = out / f"{args.board}.ppm"
    cmd = [str(_emu.LIVE_BIN), "--shot", str(args.ms), "--fwsc", str(fwsc)]
    if args.mhz:
        cmd += ["--mhz", str(args.mhz)]
    if args.persist:
        cmd += ["--flash", _flash(args)]
    env = dict(os.environ)
    if args.keys:
        env["FM1_BENCH_KEYS"] = str(args.keys)
    print(f"emu: {_emu.LIVE_BIN.name} --shot {args.ms} --fwsc {fwsc}")
    proc = subprocess.run(
        cmd, cwd=_emu.EMU_DIR, env=env, capture_output=True, text=True
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    shot = _emu.EMU_DIR / "work" / "panel.ppm"
    if shot.is_file():
        shutil.copyfile(shot, panel)
        print(f"emu: panel -> {panel}")
    if "halt:" in proc.stdout or "halt:" in proc.stderr:
        print("emu: the firmware halted in the emulator", file=sys.stderr)
        return 1
    return 0


def _memory_check(fwsc: Path, ms: int = 3000, mhz: int = 240) -> int:
    """Boot the package on the emulator with FM1_STRICT (the hardware guard and the
    misaligned 16-/32-bit RAM-access fault are both enforced) and hold a chord. A
    memory-safety bug raises the CPU exception, which stops the audio, whilst a
    clean render fills the buffer. Returns 0 = clean, 1 = the firmware faulted.

    This is a host-side check, so it runs the host-built `fm1-live` rather than the
    container."""
    env = dict(os.environ)
    env["FM1_STRICT"] = "1"
    cmd = [str(_emu.LIVE_BIN), "--shot", str(ms), "--fwsc", str(fwsc)]
    if mhz:
        cmd += ["--mhz", str(mhz)]
    proc = subprocess.run(
        cmd, cwd=_emu.EMU_DIR, env=env, capture_output=True, text=True
    )
    peak = re.search(
        r"audio peak over the last 0\.5 s: (\d+)", proc.stdout + proc.stderr
    )
    if peak and int(peak.group(1)) == 0:
        print(
            "memory check: no audio - the firmware raised the CPU exception "
            "(a guard or a misaligned access)",
            file=sys.stderr,
        )
        return 1
    if "halt:" in proc.stdout or "halt:" in proc.stderr:
        print("memory check: the firmware halted", file=sys.stderr)
        return 1
    peak_s = peak.group(1) if peak else "n/a"
    print(f"memory check: ok ({mhz} MHz, {ms} ms, audio peak {peak_s})")
    return 0


def _wav(args: argparse.Namespace, fwsc: Path) -> int:
    """The batch interpreter (`fm1-emu`, not the GUI) writes the I2S output to a WAV
    (44.1 kHz stereo 16-bit) and/or dumps memory, the target bit-exactness gate."""
    out = args.wav.resolve() if args.wav is not None else None
    cmd = [str(_emu.EMU_BIN), "--fwsc", str(fwsc)]
    if out is not None:
        cmd += ["--wav", str(out)]
    if args.dump is not None:
        cmd += ["--dump", str(args.dump[0]), str(args.dump[1])]
    if args.ms:
        cmd += ["--ms", str(args.ms)]
    if args.keys:
        cmd += ["--keys", str(args.keys)]
    if args.ram:
        cmd += ["--ram", str(args.ram)]
    label = f"--wav {out}" if out is not None else "--dump"
    print(f"emu: {_emu.EMU_BIN.name} --fwsc {fwsc} {label}")
    proc = subprocess.run(cmd, cwd=_emu.EMU_DIR, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if out is not None and not out.is_file():
        print(f"emu: no WAV written to {out}", file=sys.stderr)
        return 1
    if "halt:" in proc.stdout or "halt:" in proc.stderr:
        print("emu: the firmware halted in the emulator", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate emu", description=__doc__)
    parser.add_argument("--board", choices=("fm1", "smk37"), default="fm1")
    parser.add_argument("--fwsc", type=Path, help="a .fwsc (default: the built one)")
    parser.add_argument(
        "--persist", action="store_true", help="keep the flash chip between runs"
    )
    parser.add_argument("--midi", help="MIDI input filter (all|none|NAME)")
    parser.add_argument("--mhz", type=int, help="emulated clock (default 240)")
    parser.add_argument(
        "--check", action="store_true", help="headless regression, not the GUI"
    )
    parser.add_argument(
        "--memory",
        action="store_true",
        help="memory-safety gate: FM1_STRICT on, fail on a CPU exception",
    )
    parser.add_argument(
        "--wav",
        type=Path,
        help="run fm1-emu (the batch interpreter) and write the I2S output here",
    )
    parser.add_argument(
        "--dump",
        nargs=2,
        metavar=("ADDR", "N"),
        help="fm1-emu --dump ADDR N: dump N words at ADDR at the end (e.g. the "
        "test-dump gate: --dump 0x1c19400 512)",
    )
    parser.add_argument(
        "--ms", type=int, default=5000, help="--check/--wav: emulated ms"
    )
    parser.add_argument(
        "--keys",
        help="--check: panel script (FM1_BENCH_KEYS). --wav: fm1-emu keys script.",
    )
    parser.add_argument(
        "--ram", type=int, help="--wav: emulated RAM bytes (fm1-emu --ram)"
    )
    args = parser.parse_args(argv)

    if not _emu.emulator_built():
        print("emu: fm1-emu is not built. Run `umetate setup` first.", file=sys.stderr)
        return 1

    fwsc: Path = args.fwsc or _default_fwsc(str(args.board))
    if not fwsc.is_file():
        print(f"emu: {fwsc} is not built. Run `umetate build` first.", file=sys.stderr)
        return 1
    fwsc = fwsc.resolve()  # fm1-live runs in a different cwd: absolute path

    if args.wav is not None or args.dump is not None:
        return _wav(args, fwsc)
    if args.memory:
        return _memory_check(fwsc, ms=args.ms, mhz=args.mhz or 240)
    return _check(args, fwsc) if args.check else _gui(args, fwsc)


if __name__ == "__main__":
    sys.exit(main())
