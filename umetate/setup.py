# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate setup`: the full bootstrap, with the target toolchain, the SDK, and
fm1-emu.

1. The JieLi toolchain and SDK go into the `/opt/jieli` volume. The fetch needs
   opt-in consent and is SHA-256-verified against `env.lock`. It runs in a
   throwaway container with `umetate-target` mounted read-write, the only
   legitimate volume writer.
2. Rust (rustup) and fm1-emu go on the host. The clone is
   `joakimeriksson/fm1-emu` at the pinned commit, then `cargo build --release -p
   fm1-emu -p fm1-live` builds the batch runner and the GUI.

`--no-emulator` skips step 2, `--dry-run` changes nothing, and each step is
idempotent.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

from . import _emu, runner
from ._schema import Lock, as_lock

_ROOT = Path(__file__).resolve().parents[1]
_ENV_LOCK = _ROOT / "env.lock"
_LOCAL_ENV = _ROOT / ".local-env"

_VOLUME = "/opt/jieli"
_TC_DIR = f"{_VOLUME}/toolchain"
_SDK_DIR = f"{_VOLUME}/sdk"


def _lock() -> Lock:
    return as_lock(json.loads(_ENV_LOCK.read_text(encoding="utf-8")))


def _plan(args: argparse.Namespace, lock: Lock) -> list[str]:
    """The actions `setup` will take (for `--dry-run` and the consent prompt)."""
    tc = lock["jieli_toolchain"]
    sdk = lock["ac79_sdk"]
    steps = [
        f"fetch {tc['linux']} from {tc['download']}"
        if args.toolchain == "auto"
        else f"use toolchain tarball {args.toolchain}",
        f"verify {tc['linux']} SHA-256, extract to {_TC_DIR}",
        "smoke-test the toolchain (clang --version)",
        f"git clone {sdk['tag']} from {sdk['source']}"
        if args.sdk == "auto"
        else f"use SDK checkout {args.sdk}",
    ]
    steps.extend(f"verify SDK asset {name} SHA-256" for name in sdk["assets"])
    if not args.no_emulator:
        steps.extend(_emulator_steps(lock))
    steps.append(f"record --clock {args.clock} to .local-env")
    return steps


def _emulator_steps(lock: Lock) -> list[str]:
    """The fm1-emu (host) actions, for the plan."""
    commit = lock["fm1_emu"]["commit"][:12]
    return [
        "install Rust (rustup) if `cargo` is missing",
        f"clone fm1-emu @ {commit} into .tools/fm1-emu",
        "cargo build --release -p fm1-emu -p fm1-live",
    ]


def _script(args: argparse.Namespace, lock: Lock) -> str:
    """The POSIX script the writable container runs (fetch + verify + install)."""
    tc = lock["jieli_toolchain"]
    sdk = lock["ac79_sdk"]
    verify = not args.force
    clang = f"{_TC_DIR}/pi32v2/bin/clang"
    lines = ["set -e"]

    # ---- toolchain ----
    lines.append(f"mkdir -p {shlex.quote(_TC_DIR)}")
    if args.toolchain == "auto":
        tarball = "/tmp/tc.tar.xz"
        lines.append(f"curl -fsSL {shlex.quote(tc['download'])} -o {tarball}")
    else:
        tarball = str(args.toolchain)
    pinned = tc.get("linux_sha256", "")
    if verify and pinned and not pinned.startswith("TBD"):
        lines.append(
            f"echo {shlex.quote(pinned)} {shlex.quote(tarball)} | sha256sum -c -"
        )
    tar = f"tar -xJf {shlex.quote(tarball)} -C {shlex.quote(_TC_DIR)}"
    lines.append(f"{tar} --strip-components=1")
    lines.append(f"{shlex.quote(clang)} --version >/dev/null")
    lines.append(f"echo 'toolchain ok:' $({shlex.quote(clang)} --version | head -1)")

    # ---- sdk ----
    if args.sdk == "auto":
        lines.append(
            f"[ -d {shlex.quote(_SDK_DIR)} ] && rm -rf {shlex.quote(_SDK_DIR)}"
        )
        clone = (
            f"git clone --depth 1 --branch {shlex.quote(sdk['tag'])} "
            f"{shlex.quote(sdk['source'])} {shlex.quote(_SDK_DIR)}"
        )
        lines.append(clone)
    else:
        lines.append(f"cp -a {shlex.quote(str(args.sdk))} {shlex.quote(_SDK_DIR)}")
    assets = f"{_SDK_DIR}/cpu/wl82/tools"
    for name, expected in sdk["assets"].items():
        path = f"{assets}/{name}"
        if verify:
            lines.append(
                f"echo {shlex.quote(expected)} {shlex.quote(path)} | sha256sum -c -"
            )
        else:
            lines.append(f"test -f {shlex.quote(path)}")

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------- emulator (host) ----


def _ensure_rust() -> None:
    """Install Rust (rustup) if `cargo` is not already reachable."""
    if _emu.find_cargo() is not None:
        print("setup: rust: cargo present")
        return
    _emu.EMU_DIR.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        init = _emu.EMU_DIR.parent / "rustup-init.exe"
        subprocess.run(
            ["curl", "-fsSL", "https://win.rustup.rs/x86_64", "-o", str(init)],
            check=True,
        )
        subprocess.run(
            [str(init), "-y", "--default-toolchain", "stable", "--profile", "minimal"],
            check=True,
        )
    else:
        subprocess.run(
            [
                "sh",
                "-c",
                "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | "
                "sh -s -- -y --default-toolchain stable --profile minimal",
            ],
            check=True,
        )
    if _emu.find_cargo() is None:
        raise SystemExit("setup: rust installed but cargo not found")


def _ensure_checkout(lock: Lock) -> None:
    """Clone fm1-emu at the pinned commit (recurse submodules) into .tools/fm1-emu."""
    source = lock["fm1_emu"]["source"]
    commit = lock["fm1_emu"]["commit"]
    _emu.EMU_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not _emu.EMU_DIR.is_dir():
        subprocess.run(
            ["git", "clone", "--recurse-submodules", source, str(_emu.EMU_DIR)],
            check=True,
        )
    subprocess.run(
        ["git", "-C", str(_emu.EMU_DIR), "checkout", "--quiet", commit], check=True
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(_emu.EMU_DIR),
            "submodule",
            "update",
            "--init",
            "--recursive",
        ],
        check=True,
    )


def _build_emulator(lock: Lock) -> None:
    """`cargo build --release -p fm1-emu -p fm1-live` (the batch runner + the GUI)."""
    cargo = _emu.find_cargo()
    if cargo is None:
        raise SystemExit("setup: cargo not found")
    cmd = [str(cargo), "build", "--release"]
    for package in lock["fm1_emu"]["packages"]:
        cmd += ["-p", package]
    print(f"setup: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=_emu.EMU_DIR, check=True)


def _run_emulator(lock: Lock) -> None:
    """Install Rust, fetch + build fm1-emu (idempotent)."""
    _ensure_rust()
    _ensure_checkout(lock)
    _build_emulator(lock)
    if not _emu.emulator_built():
        raise SystemExit("setup: fm1-emu build finished without its binaries")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate setup", description=__doc__)
    parser.add_argument("--toolchain", default="auto", metavar="auto|PATH")
    parser.add_argument("--sdk", default="auto", metavar="auto|PATH")
    parser.add_argument("--clock", type=int, choices=(240, 320), default=320)
    parser.add_argument(
        "--no-emulator", action="store_true", help="skip the Rust + fm1-emu step"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the plan, change nothing"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--yes", action="store_true", help="skip the consent prompt")
    parser.add_argument("--force", action="store_true", help="accept a hash mismatch")
    args = parser.parse_args(argv)

    if not _ENV_LOCK.exists():
        print("setup: env.lock not found", file=sys.stderr)
        return 1
    lock = _lock()

    if args.dry_run:
        if args.json:
            print(json.dumps({"steps": _plan(args, lock)}))
        else:
            for step in _plan(args, lock):
                print(f"  - {step}")
        return 0

    if not args.yes:
        print("umetate setup downloads the JieLi toolchain + SDK from their vendors,")
        print("and (unless --no-emulator) installs Rust + builds fm1-emu from GitHub.")
        print("None are redistributed by umetate. See LICENSING.md.")
        print("Continue? [y/N] ", end="")
        if input().strip().lower() != "y":
            return 1

    rc = runner.run_writable(["sh", "-ec", _script(args, lock)])
    if rc != 0:
        print(
            "setup: blocked, the container install failed (see output above)",
            file=sys.stderr,
        )
        return 1

    if not args.no_emulator:
        try:
            _run_emulator(lock)
        except (subprocess.SubprocessError, OSError, SystemExit) as exc:
            print(
                f"setup: blocked, the emulator install failed: {exc}",
                file=sys.stderr,
            )
            return 1

    _LOCAL_ENV.write_text(f"clock={args.clock}\n", encoding="utf-8")
    print(f"setup: done (toolchain + SDK in {_VOLUME}, clock={args.clock})")
    if not args.no_emulator:
        print(
            "setup: fm1-emu ready. `umetate emu` opens the GUI, "
            "`--check` runs headless."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
