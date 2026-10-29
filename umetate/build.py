# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate build` — generate + target compile + package → `.fwsc`.

The target branch only (host/WASM are `deep-check`/`web-build`); `blocked` without
the JieLi toolchain. Wraps the inherited `firmware/tools/cmake_target.py` build
(strangler-fig, not a rewrite). The toolchain/SDK come from `$JIELI_TOOLCHAIN` /
`$AC79_SDK`, the local `.jieli/` checkout, or the `umetate-target` volume.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import runner

_ROOT = Path(__file__).resolve().parents[1]
# container-side paths: the runner mounts the repo at /work, the volume at /opt/jieli
_TC_VOLUME = "/opt/jieli/toolchain"
_SDK_VOLUME = "/opt/jieli/sdk"
_TC_CHECKOUT = "/work/.jieli/jieli-linux-toolchains-20260730.1"
_SDK_CHECKOUT = "/work/.jieli/sdk"


def _volume_populated() -> bool:
    """Does the `umetate-target` volume hold the toolchain + SDK (`setup` ran)?"""
    if not runner.probe().docker:
        return (
            Path(f"{_TC_VOLUME}/pi32v2/bin/clang").is_file()
            and Path(f"{_SDK_VOLUME}/cpu/wl82/tools/uboot.boot").is_file()
        )
    return (
        runner.run(["test", "-x", f"{_TC_VOLUME}/pi32v2/bin/clang"]) == 0
        and runner.run(["test", "-f", f"{_SDK_VOLUME}/cpu/wl82/tools/uboot.boot"]) == 0
    )


def _resolve() -> tuple[str, str] | None:
    """The (toolchain, sdk) container-side paths, or `None` when nothing is set up.

    Precedence: explicit `$JIELI_TOOLCHAIN`/`$AC79_SDK`, then the `umetate-target`
    volume (the canonical `setup` location), then the local `.jieli/` checkout.
    """
    tc_env, sdk_env = os.environ.get("JIELI_TOOLCHAIN"), os.environ.get("AC79_SDK")
    if tc_env and sdk_env:
        return tc_env, sdk_env
    if _volume_populated():
        return _TC_VOLUME, _SDK_VOLUME
    if (_ROOT / ".jieli" / "jieli-linux-toolchains-20260730.1").is_dir():
        return _TC_CHECKOUT, _SDK_CHECKOUT
    return None


def _container_path(path: Path) -> str:
    """`path` as the runner sees it (`/work/...` in the container; a no-op there)."""
    root = str(_ROOT).replace("\\", "/")
    return str(path).replace("\\", "/").replace(root, "/work", 1)


def _run_posix(cmd: list[str], cwd: Path) -> int:
    """Run a POSIX command: in the pinned container when docker is present, else
    directly (the CLI already runs inside the container). `cmd` holds the
    container-relative paths (see `_container_path`)."""
    if runner.probe().docker:
        rel = str(cwd.relative_to(_ROOT)).replace("\\", "/")
        return runner.run(cmd, cwd="/work/" + rel)
    return subprocess.run(cmd, cwd=cwd).returncode


def _synth_main(args: argparse.Namespace) -> int:
    """`umetate build --synth <dir>` — compose a synth project into a firmware
    (roadmap §6.11.4, F7): generate the engine/panel/CC/layout files into
    `firmware/gen/`, host-build the composition and run the project's script, then
    hand the target build to the toolchain (blocked without it)."""
    import json

    from ._ir import GenError, to_c_identifier
    from ._panel import generate_panel
    from ._schema import as_panel, as_patch
    from .generate import (
        generate,
        generate_cc_header,
        generate_dsp_header,
        generate_params,
        generate_synth_header,
        generate_sysex_layout,
        generate_tables,
        param_ids,
        param_meta,
    )

    synth = args.synth.resolve()
    try:
        patch = as_patch(json.loads((synth / "patch.json").read_text(encoding="utf-8")))
        panel = as_panel(json.loads((synth / "panel.json").read_text(encoding="utf-8")))
        app_c = (synth / "app.c").read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(
            f"build --synth: cannot read the project in {synth}: {exc}", file=sys.stderr
        )
        return 1

    model = patch.get("model", 0)
    if not 0 <= model <= 0x7F:
        print(
            f"build --synth: the patch's model byte must be 0..127 (got {model!r})",
            file=sys.stderr,
        )
        return 1

    gen_dir = Path(os.environ.get("UMETATE_GEN", str(_ROOT / "firmware" / "gen")))
    gen_dir.mkdir(parents=True, exist_ok=True)
    try:
        name = to_c_identifier(patch["name"])
        tables_h, tables_c = generate_tables(patch)
        ids = param_ids(patch)
        meta = param_meta(patch)
        outputs: dict[str, str] = {
            f"{name}_dsp.c": generate(patch),
            "dsp.h": generate_dsp_header(patch),
            "tables.h": tables_h,
            "tables.c": tables_c,
            "panel.h": generate_panel(panel, ids, meta),
            "cc_map.h": generate_cc_header(patch),
            "synth_layout.h": generate_synth_header(patch),
            "params.json": json.dumps(generate_params(patch), indent=2) + "\n",
            "sysex-layout.json": json.dumps(generate_sysex_layout(patch), indent=2)
            + "\n",
            "app.c": app_c,
        }
    except GenError as exc:
        print(f"build --synth: {exc}", file=sys.stderr)
        return 1
    for filename, content in outputs.items():
        (gen_dir / filename).write_text(content, encoding="utf-8")
        print(f"gen      {gen_dir / filename}")

    # the host leg: compile the composition (the framework + the app + the engine)
    # and run the project's script — WAV + screen shots prove it works on a computer.
    firmware = _ROOT / "firmware"
    host_out = firmware / "build" / "host"
    host_out.mkdir(parents=True, exist_ok=True)
    binary = host_out / name
    cc_cmd = [
        "cc",
        "-O2",
        "-Wall",
        "-Wno-unused-function",
        "-DUMETATE_HOST",
        "-DUMETATE_SYNTH_APP=1",
        '-DAPP_VER="dev"',
        f"-I{_container_path(firmware / 'hal')}",
        f"-I{_container_path(firmware / 'src')}",
        f"-I{_container_path(gen_dir)}",
        "-o",
        _container_path(binary),
        _container_path(firmware / "src" / "rib.c"),
        _container_path(gen_dir / f"{name}_dsp.c"),
        _container_path(gen_dir / "tables.c"),
    ]
    if _run_posix(cc_cmd, firmware) != 0:
        print("build --synth: the host composition does not compile", file=sys.stderr)
        return 1
    script = synth / "host-script.txt"
    run_cmd = [_container_path(binary), _container_path(binary)]
    if script.is_file():
        run_cmd.append(_container_path(script))
    if _run_posix(run_cmd, firmware) != 0:
        print("build --synth: the host run failed", file=sys.stderr)
        return 1
    print(f"host     {binary}")

    # the target leg: the same composition through the JieLi toolchain.
    resolved = _resolve()
    if resolved is None:
        print(
            "build --synth: target package blocked — JieLi toolchain not set up "
            "(`umetate setup`); the host leg is complete.",
            file=sys.stderr,
        )
        return 0
    toolchain, sdk = resolved
    profile = "performance" if args.profile == "perf" else str(args.profile)
    tcmd: list[str] = [
        "python3",
        "tools/cmake_target.py",
        "build",
        "--toolchain",
        toolchain,
        "--sdk",
        sdk,
        "--sdk-assets",
        f"{sdk}/cpu/wl82/tools",
        "--out",
        "/work/firmware/build",
        "--board",
        str(args.board),
        "--model",
        str(args.model),
        "--profile",
        profile,
        "--defs=-DUMETATE_SYNTH_APP=1",
        "--dsp-tus",
        f"gen/{name}_dsp.c",
        "gen/tables.c",
        "--synth",
        name,
    ]
    if runner.probe().docker:
        return runner.run(tcmd, cwd="/work/firmware")
    return subprocess.run(tcmd, cwd=_ROOT / "firmware").returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate build", description=__doc__)
    parser.add_argument("--board", choices=("fm1", "smk37"), default="fm1")
    parser.add_argument("--model", choices=("pro", "elite", "mke"), default="pro")
    parser.add_argument("--dsp", choices=("integer", "float"), default="integer")
    parser.add_argument(
        "--clock",
        type=int,
        choices=(240, 320),
        default=320,
        help="360 and 396 have no FM-1 evidence and are rejected",
    )
    parser.add_argument("--profile", choices=("baseline", "perf"), default="perf")
    parser.add_argument(
        "--synth",
        type=Path,
        help="compose a synth project (patch.json + panel.json + app.c) instead of "
        "the demo app",
    )
    args = parser.parse_args(argv)

    if args.synth is not None:
        return _synth_main(args)

    if args.model != "pro" and args.board != "smk37":
        parser.error("non-pro models require --board smk37")

    resolved = _resolve()
    if resolved is None:
        print(
            "build: blocked — JieLi toolchain not set up (`umetate setup`)",
            file=sys.stderr,
        )
        return 1
    toolchain, sdk = resolved
    profile = "performance" if args.profile == "perf" else str(args.profile)
    cmd: list[str] = [
        "python3",
        "tools/cmake_target.py",
        "build",
        "--toolchain",
        toolchain,
        "--sdk",
        sdk,
        "--sdk-assets",
        f"{sdk}/cpu/wl82/tools",
        "--out",
        "/work/firmware/build",
        "--board",
        str(args.board),
        "--model",
        str(args.model),
        "--profile",
        profile,
    ]
    if runner.probe().docker:
        return runner.run(cmd, cwd="/work/firmware")
    # no docker: a POSIX host with the toolchain (e.g. the dev container)
    return subprocess.run(cmd, cwd=_ROOT / "firmware").returncode


if __name__ == "__main__":
    sys.exit(main())
