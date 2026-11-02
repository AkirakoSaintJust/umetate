# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate publish` — assemble a distributable firmware repo (docs/roadmap.md §6.14).

Gathers a built synth's user docs, the `.fwsc` firmware artifact, and the browser
web app into a self-contained `publish/<name>/` folder, ready to push to a remote
GitHub repo with GitHub Pages serving the web app. This is the repeatable
publishing loop: edit, `umetate build` + `umetate web-build`, `umetate publish`,
bump the release notes, push.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from ._ir import to_c_identifier

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = _ROOT / "examples"
_FW_BUILD = _ROOT / "firmware" / "build"
_WEB_BUILD = _ROOT / "build" / "web"
_EMU_DIR = _ROOT / "firmware" / "web_emu"
_PUBLISH = _ROOT / "publish"

# the served web app: the emulator page + worklet are source files in
# `firmware/web_emu/`; `firmware.wasm` is the compiled artifact in `build/web/`.
# (Do not take `build/web/index.html` — the parity lab clobbers it.)
_WEB_SOURCES = (
    (_EMU_DIR, "index.html"),
    (_EMU_DIR, "worklet.js"),
    (_WEB_BUILD, "firmware.wasm"),
)

# the corresponding source: the project's declarative synth + app glue + the design
# specs. (The framework, umetate, is GPL-3.0 source in its own repo, linked in the
# README.) The GPL requires the source to travel with the binary.
_SRC_FILES = (
    "patch.json",
    "panel.json",
    "app.c",
    "host-script.txt",
    "synth-brief.md",
    "dsp-algorithm.md",
    "control-map.md",
    "code-structure.md",
)

# the licence + attribution manifest, copied from the umetate root verbatim.
_LICENCE_FILES = ("LICENSE", "LICENSING.md")

# the framework source, snapshotted into the published repo as `framework/` so the
# corresponding source is self-contained (a user does not need the umetate repo to
# rebuild the firmware). `git archive` lists only tracked files, so the gitignored
# build artifacts and the generated-from-patch `firmware/gen/*.c` stay out; the
# generator (`umetate/`) regenerates them from `src/patch.json`.
_FRAMEWORK_PATHS = (
    "LICENSE",
    "LICENSING.md",
    "pyproject.toml",
    "env.lock",
    "firmware",
    "umetate",
    "modules",
    "templates/scaffold",
)

_README = """# {title}

{title} is a four-operator FM synthesizer for the M-VAVE FM-1, built on umetate.

## Try it in the browser

The web app runs the same sound engine in your browser, no device needed.

[{repo_url}]({repo_url})

Drag the knobs, play the keys with your keyboard or mouse, and click the knobs and
buttons to move around the panel. The screen shows what the real device shows.

## Install on the FM-1

1. Download `{fwsc}`.
2. Put the FM-1 in update mode and send the firmware with the umetate installer:

   ```sh
   umetate flash {fwsc} --device
   ```

   `umetate flash` verifies the package identity and model before it writes. See
   the umetate documentation for the full recovery and safety notes.

## The manual

- [User manual](docs/manual.md) — the sound and every parameter.
- [Panel reference](docs/panel.md) — the controls, the pages, and how to save.
- [MIDI and SysEx](docs/midi-and-sysex.md) — the CC map and the SysEx format.
- [Patch sheet](docs/patch-sheet.md) — a printable form for writing patches down.

## Releases

[CHANGELOG.md](CHANGELOG.md) lists what changed in each version.

## Licence

{title} is free software under the GPL-3.0-only licence. See [LICENSE](LICENSE) for
the full text and [LICENSING.md](LICENSING.md) for the third-party credits and
attribution.

## Source

The `.fwsc` is the compiled firmware. Its corresponding source is the project
files in [`src/`](src/) (the patch, the panel, and the app glue) and the complete
umetate framework source in [`framework/`](framework/), also GPL-3.0, at
<https://github.com/CeliaCasanovas/umetate>. The preferred form for modification
is the `src/` files and the umetate generator, not the compiled binary.
"""


def _name_of(synth_dir: Path) -> str:
    patch = synth_dir / "patch.json"
    if not patch.is_file():
        return synth_dir.name
    data = json.loads(patch.read_text(encoding="utf-8"))
    return str(data.get("name") or synth_dir.name)


def _gather(synth_dir: Path, name: str, cname: str, out: Path) -> list[str]:
    """Copy the docs, web app, .fwsc, licence, and source into `out`."""
    missing: list[str] = []

    # the licence + attribution manifest (GPL compliance: the source travels with
    # the binary).
    for f in _LICENCE_FILES:
        src = _ROOT / f
        if src.is_file():
            shutil.copy2(src, out / f)
        else:
            missing.append(f"{f} (missing at the repo root)")

    # the project source (the preferred form for modification).
    (out / "src").mkdir(parents=True, exist_ok=True)
    for f in _SRC_FILES:
        src = synth_dir / f
        if src.is_file():
            shutil.copy2(src, out / "src" / f)

    docs = synth_dir / "docs"
    if docs.is_dir():
        (out / "docs").mkdir(parents=True, exist_ok=True)
        for doc in sorted(docs.glob("*.md")):
            shutil.copy2(doc, out / "docs" / doc.name)
        rel_notes = out / "docs" / "release-notes.md"
        if rel_notes.is_file():
            shutil.copy2(rel_notes, out / "CHANGELOG.md")
    else:
        missing.append(f"docs (no {docs})")

    fwsc = _FW_BUILD / f"umetate-fm1-pro-{cname}.fwsc"
    if fwsc.is_file():
        shutil.copy2(fwsc, out / f"{name}.fwsc")
    else:
        missing.append(f".fwsc (no {fwsc}; run `umetate build --synth {synth_dir}`)")

    web_out = out  # the web app is the repo root, so GitHub Pages serves it directly
    got = 0
    for src_dir, f in _WEB_SOURCES:
        src = src_dir / f
        if src.is_file():
            shutil.copy2(src, web_out / f)
            got += 1
    if got < len(_WEB_SOURCES):
        missing.append("web app (run `umetate web-build` first)")

    return missing


def _snapshot_framework(out: Path) -> bool:
    """Snapshot the umetate source (tracked files at HEAD) into `out/framework/`.

    Returns True on success. Falls back to False (the README still links the umetate
    repo) when `git archive` is unavailable or there is no commit to snapshot.
    """
    proc = subprocess.run(
        ["git", "archive", "HEAD", *_FRAMEWORK_PATHS],
        cwd=_ROOT,
        capture_output=True,
    )
    if proc.returncode != 0:
        return False
    dest = out / "framework"
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:") as tf:
        try:
            tf.extractall(dest, filter="data")
        except TypeError:  # Python < 3.12 has no `filter=` argument
            tf.extractall(dest)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="umetate publish", description="assemble a distributable firmware repo"
    )
    parser.add_argument(
        "synth_dir",
        nargs="?",
        type=Path,
        default=_EXAMPLES / "type-p-fm1",
        help="the project dir (default: examples/type-p-fm1)",
    )
    parser.add_argument("--out", type=Path, help="output dir (default: publish/<name>)")
    parser.add_argument(
        "--title", help="the display name for the README (default: Type P.fm1)"
    )
    parser.add_argument(
        "--repo-url",
        default="https://USERNAME.github.io/REPO/",
        help="the GitHub Pages URL the README links to",
    )
    args = parser.parse_args(argv)

    synth_dir: Path = args.synth_dir
    if not (synth_dir / "patch.json").is_file():
        print(f"publish: {synth_dir / 'patch.json'} not found", file=sys.stderr)
        return 2
    name = _name_of(synth_dir)
    cname = to_c_identifier(name)
    out = args.out or _PUBLISH / name
    title = args.title or "Type P.fm1"

    out.mkdir(parents=True, exist_ok=True)
    missing = _gather(synth_dir, name, cname, out)
    bundled = _snapshot_framework(out)

    # the project's own README wins over the generated template, so a human-written
    # front door is preserved verbatim (not overwritten by the loop).
    user_readme = synth_dir / "publish-readme.md"
    if user_readme.is_file():
        shutil.copy2(user_readme, out / "README.md")
    else:
        readme = _README.format(
            title=title, repo_url=args.repo_url, fwsc=f"{name}.fwsc"
        )
        (out / "README.md").write_text(readme, encoding="utf-8")

    print(f"publish: {out}")
    print(
        "  README.md, CHANGELOG.md, LICENSE, LICENSING.md, src/, docs/, "
        "framework/, the web app (root), and " + f"{name}.fwsc"
    )
    if missing:
        print("  missing (build first):")
        for m in missing:
            print(f"    - {m}")
    else:
        print("  all artifacts present.")
    if not bundled:
        print("  note: could not snapshot the framework source (no git/HEAD);")
        print("        the README still links the umetate repo for it.")
    print("  next: `git init` here, commit, then push to a GitHub repo with Pages")
    print("  (set the Pages source to the repo root).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
