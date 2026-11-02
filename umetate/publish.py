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
import json
import shutil
import sys
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
"""


def _name_of(synth_dir: Path) -> str:
    patch = synth_dir / "patch.json"
    if not patch.is_file():
        return synth_dir.name
    data = json.loads(patch.read_text(encoding="utf-8"))
    return str(data.get("name") or synth_dir.name)


def _gather(synth_dir: Path, name: str, cname: str, out: Path) -> list[str]:
    """Copy the docs, web app, and .fwsc into `out`. Return the missing artifacts."""
    missing: list[str] = []

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

    readme = _README.format(title=title, repo_url=args.repo_url, fwsc=f"{name}.fwsc")
    (out / "README.md").write_text(readme, encoding="utf-8")

    print(f"publish: {out}")
    print("  README.md, CHANGELOG.md, docs/, the web app (root), and " + f"{name}.fwsc")
    if missing:
        print("  missing (build first):")
        for m in missing:
            print(f"    - {m}")
    else:
        print("  all artifacts present.")
    print("  next: `git init` here, commit, then push to a GitHub repo with Pages")
    print("  (set the Pages source to the repo root).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
