from pathlib import Path
import os
import tempfile
import sys

sys.path.insert(0, str(Path("tools").resolve()))
import cmake_target


class Args:
    action = "build"
    toolchain = Path(os.environ.get("JIELI_TOOLCHAIN", Path.home() / ".jieli" / "toolchain"))
    sdk = Path(os.environ.get("AC79_SDK", "/opt/jieli/sdk"))
    out = Path(tempfile.mkdtemp(prefix="umetate-"))
    board = "fm1"
    model = "pro"
    profile = "baseline"
    release = None
    defs = ""
    docker = False
    docker_image = "umetate-host-build:latest"
    sdk_assets_root = Path(os.environ.get("AC79_SDK_ASSETS", sdk / "cpu" / "wl82" / "tools"))
    sdk_assets = sdk_assets_root if sdk_assets_root.is_dir() else None


def run(args):
    sys.argv = ["cmake_target.py", args.action,
                "--toolchain", str(args.toolchain),
                "--sdk", str(args.sdk),
                "--out", str(args.out),
                "--board", args.board,
                "--model", args.model,
                "--profile", args.profile,
    ]
    if args.defs:
        sys.argv.append("--defs")
        sys.argv.append(args.defs)
    if args.docker:
        sys.argv.append("--docker")
    if args.docker_image:
        sys.argv.append("--docker-image")
        sys.argv.append(args.docker_image)
    if args.sdk_assets:
        sys.argv.extend(("--sdk-assets", str(args.sdk_assets)))
    if args.release:
        sys.argv.append("--release")
        sys.argv.append(args.release)
    try:
        cmake_target.main()
    except SystemExit as exc:
        return exc.code
    return 0
