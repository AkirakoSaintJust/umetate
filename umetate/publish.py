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
import contextlib
import hashlib
import io
import json
import os
import platform as _platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

from ._ir import to_c_identifier

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = _ROOT / "examples"
_FW_BUILD = _ROOT / "firmware" / "build"
_WEB_BUILD = _ROOT / "build" / "web"
_EMU_DIR = _ROOT / "firmware" / "web_emu"
_PUBLISH = _ROOT / "publish"

_RELEASE_FILE = "RELEASES.md"
_CHECKSUM_FILE = "SHA256SUMS"
_MANIFEST_FILE = "release.json"


class ReleaseArtifact(TypedDict):
    """One downloadable artifact in the release manifest."""

    path: str
    platform: str
    format: str
    size: int
    sha256: str


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
    "plugin.json",
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
# generator (`umetate/`) regenerates them from `src/patch.json`, and `_bundle_dsp`
# additionally copies the already-generated DSP so the tree also compiles as-is.
_FRAMEWORK_PATHS = (
    "LICENSE",
    "LICENSING.md",
    "pyproject.toml",
    "env.lock",
    "design",
    "firmware",
    "plugin",
    "skills",
    "templates",
    "umetate",
    "modules",
)

# the generated-from-patch files in `firmware/gen/` (gitignored, so `git archive`
# omits them). The per-patch `<cname>_dsp.c` is added separately.
_GENERATED_FILES = (
    "dsp.h",
    "glue.h",
    "cc_map.h",
    "synth_layout.h",
    "panel.h",
    "tables.c",
    "tables.h",
    "params.json",
    "sysex-layout.json",
    "app.c",
)

_README = """# {title}

{title} is a synthesizer for the M-VAVE FM-1, built with umetate. The same engine
runs on the device and in the browser. You can try a patch before you flash
anything.

## Try it in the browser

The web app needs no device and no toolchain. Open the page, drag a knob, and play
the keys with your keyboard or mouse.

[{repo_url}]({repo_url})

The screen is the same 240 by 240 panel you see on the device.

## Install on the FM-1

1. Download `{fwsc}`.
2. Put the FM-1 in update mode and send the firmware with the umetate installer:

   ```sh
   umetate flash {fwsc} --device
   ```

   `umetate flash` checks the package identity and model before it writes. Read
   the umetate documentation for the recovery notes before your first flash.

## Manual

- [User manual](docs/manual.md), the sound, every parameter, and the panel walkthrough.
- [MIDI and SysEx](docs/midi-and-sysex.md), the CC map and the SysEx format.
- [Patch sheet](docs/patch-sheet.md), a printable form for writing patches down.

## Release notes

[CHANGELOG.md](CHANGELOG.md) lists what changed in each version.

## Downloads

[`RELEASES.md`](RELEASES.md) lists the firmware and plugin downloads, their
checksums, and the source locations.
{plugins}
## Licence

{title} is free software under the GPL-3.0-only licence. See [LICENSE](LICENSE) for
the full text and [LICENSING.md](LICENSING.md) for the third-party credits and
attribution.

## Source

The `.fwsc` is the compiled firmware. Its corresponding source is the project
files in [`src/`](src/) (the patch, the panel, and the app glue) and the complete
umetate framework source in [`framework/`](framework/), also GPL-3.0, at
<https://github.com/AkirakoSaintJust/umetate>. The generated DSP is more of an
object code generated from the JSONs, but it's bundled at
framework/firmware/gen/, so the tree builds as-is.

{plugin_source}
"""

_PLUGIN_SOURCE_SECTION = """The optional plugin builds and their source are
described in [`plugins/README.md`](plugins/README.md) and
[`DEPENDENCIES.md`](DEPENDENCIES.md). The plugin source is in
[`framework/plugin/`](framework/plugin/) and [`framework/design/`](framework/design/),
with the exact upstream pins in [`DEPENDENCIES.md`](DEPENDENCIES.md).
"""

_PLUGINS_SECTION = """
## Plugins

Optional VST3 and CLAP builds are in [`plugins/`](plugins/). They are the same
engine as the firmware and the web app. See [`plugins/README.md`](plugins/README.md)
for install steps and the licence note. The plugin source is in
[`framework/plugin/`](framework/plugin/).

"""

_DEPENDENCIES = """# Build dependencies

The firmware and web app build from the tree in this repository. The optional
plugin fetches two pinned upstream projects with CMake `FetchContent`. The pins
are in `framework/plugin/juce/CMakeLists.txt`, which is the authority.

- **JUCE** 8.0.9, AGPL-3.0-only or commercial.
  <https://github.com/juce-framework/JUCE>
- **clap-juce-extensions** commit
  `7adee3a1bd4684d4caa5601100e364abccff4b4d`, MIT.
  <https://github.com/free-audio/clap-juce-extensions>
- **CLAP headers** 1.2.7, a submodule of the extension, MIT.
  <https://github.com/free-audio/clap>
- **VST3 SDK** the copy bundled in JUCE 8.0.9, GPL-3.0-only or the Steinberg
  licence. <https://github.com/steinbergmedia/vst3sdk>

JUCE 8 is not GPLv3. A distributed plugin binary that links JUCE is conveyed
under the AGPL-3.0-only terms for the JUCE part. The umetate source keeps its
GPL-3.0-only terms and GPLv3 section 13 permits the combination. A commercial
JUCE licence removes the AGPL obligation.

## Build the plugin

```sh
cmake -S framework/plugin -B build/plugin -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON
cmake --build build/plugin
```

The build needs a C++20 compiler, CMake 3.22, Ninja or another generator, and
network access for the two `FetchContent` pins. To build offline, point
`FETCHCONTENT_SOURCE_DIR_JUCE` and
`FETCHCONTENT_SOURCE_DIR_CLAP-JUCE-EXTENSIONS` at local checkouts of the exact
pins above.
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


def _bundle_dsp(framework: Path, cname: str) -> bool:
    """Copy the already-generated DSP from `firmware/gen/` into the snapshot, so the
    published tree compiles as-is (not only via the generator). Returns True when the
    per-patch `<cname>_dsp.c` was found."""
    src_dir = _ROOT / "firmware" / "gen"
    dest_dir = framework / "firmware" / "gen"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dsp = src_dir / f"{cname}_dsp.c"
    if not dsp.is_file():
        return False
    shutil.copy2(dsp, dest_dir / dsp.name)
    for f in _GENERATED_FILES:
        src = src_dir / f
        if src.is_file():
            shutil.copy2(src, dest_dir / f)
    return True


def _snapshot_framework(out: Path, cname: str) -> bool:
    """Snapshot the umetate source (tracked files at HEAD) into `out/framework/`,
    then add the generated DSP so the tree is both regenerable and compilable as-is.

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
    _bundle_dsp(dest, cname)
    return True


def _platform_tag() -> str:
    """A short, file-name-safe tag for the current build host."""
    machine = _platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    else:
        arch = machine or "unknown"
    if sys.platform.startswith("win"):
        return f"windows-{arch}"
    if sys.platform == "darwin":
        return f"macos-{arch}"
    return f"linux-{arch}"


def _safe_name(name: str) -> str:
    keep: list[str] = []
    for ch in name:
        if ch.isalnum() or ch in "._-":
            keep.append(ch)
        elif ch in " +":
            keep.append("-")
    return "".join(keep).strip("-") or "plugin"


def _zip_artifact(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.make_archive(
            str(destination.with_suffix("")),
            "zip",
            root_dir=source.parent,
            base_dir=source.name,
        )
        return
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(source, arcname=source.name)


def _is_plugin_artifact(build_dir: Path, path: Path) -> bool:
    """Is this path a real artefact, not a test copy or a hidden folder?"""
    relative = path.relative_to(build_dir)
    return (
        "_deps" not in relative.parts
        and "linux-daws" not in relative.parts
        and not any(part.startswith(".") for part in relative.parts)
    )


def _find_plugin_artifacts(build_dir: Path) -> tuple[list[Path], list[Path]]:
    """Return the VST3 bundles and CLAP binaries under a JUCE build tree."""
    if not build_dir.is_dir():
        return [], []
    vst3 = sorted(
        path
        for path in build_dir.rglob("*.vst3")
        if path.is_dir() and _is_plugin_artifact(build_dir, path)
    )
    clap = sorted(
        path
        for path in build_dir.rglob("*.clap")
        if path.is_file() and _is_plugin_artifact(build_dir, path)
    )
    return vst3, clap


def _default_plugin_build() -> Path:
    """The first build tree with a plugin artefact, preferring the plain build."""
    candidates = [
        _ROOT / "build" / "plugin-juce",
        *sorted((_ROOT / "build" / "plugin").glob("*/build")),
    ]
    for candidate in candidates:
        vst3, clap = _find_plugin_artifacts(candidate)
        if vst3 or clap:
            return candidate
    return candidates[0]


def _project_title(synth_dir: Path, name: str) -> str:
    """The plugin's display name from `plugin.json`, else the project name."""
    path = synth_dir / "plugin.json"
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return name
        if isinstance(raw, dict):
            product = cast(dict[str, object], raw).get("product_name")
            if isinstance(product, str) and product:
                return product
    return name


def _stage_plugins(
    out: Path, build_dir: Path, platform: str, product_name: str = "Type P.fm1"
) -> list[str]:
    """Zip the built VST3 and CLAP artefacts into `out/plugins/<platform>/`."""
    vst3, clap = _find_plugin_artifacts(build_dir)
    if not vst3 and not clap:
        return []

    target = out / "plugins" / platform
    target.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    for source in vst3:
        name = f"{_safe_name(source.stem)}-VST3-{platform}.zip"
        _zip_artifact(source, target / name)
        staged.append(name)
    for source in clap:
        name = f"{_safe_name(source.stem)}-CLAP-{platform}.zip"
        _zip_artifact(source, target / name)
        staged.append(name)

    lines = [
        "# Plugins",
        "",
        "Optional VST3 and CLAP builds. They use the same engine as the firmware",
        "and the web app, with the designed editor and the saved banks.",
        "",
        "## Install",
        "",
        "- **VST3:** unzip the archive into your VST3 folder. On Linux that is",
        "  `~/.vst3/`, on Windows `C:\\Program Files\\Common Files\\VST3`.",
        "- **CLAP:** unzip the archive into your CLAP folder. On Linux that is",
        "  `~/.clap/`, on Windows `C:\\Program Files\\Common Files\\CLAP`.",
        "- Rescan plugins in your DAW. The plugin name is `P1Onken: "
        + product_name
        + "`.",
        "",
        "## Licence",
        "",
        "The plugin source is GPL-3.0-only. The binary links JUCE 8.0.9, which is",
        "AGPL-3.0-only or commercial, so the binary is conveyed under the",
        "AGPL-3.0-only terms for the JUCE part. The corresponding source is in",
        "`../framework/plugin/` and `../framework/design/`, with the exact upstream",
        "pins and build steps in `../DEPENDENCIES.md`. The licence texts are in",
        "`../third-party-licenses/`.",
        "",
        "## Builds",
        "",
    ]
    for path in sorted((out / "plugins").glob("*/*.zip")):
        relative = path.relative_to(out / "plugins").as_posix()
        lines.append(f"- `{relative}`")
    lines.append("")
    (out / "plugins" / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return staged


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_of(synth_dir: Path) -> str:
    """The newest `## x.y.z` heading in the release notes."""
    notes = synth_dir / "docs" / "release-notes.md"
    try:
        text = notes.read_text(encoding="utf-8")
    except OSError:
        return "unreleased"
    match = re.search(r"^##\s+v?([0-9]+\.[0-9]+\.[0-9]+)\s*$", text, re.MULTILINE)
    return match.group(1) if match else "unreleased"


def _source_commit() -> str:
    """The short commit the published source came from, when git is available."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _release_artifacts(out: Path, name: str) -> list[ReleaseArtifact]:
    """The firmware and every staged plugin archive, with sizes and hashes."""
    artifacts: list[ReleaseArtifact] = []
    firmware = out / f"{name}.fwsc"
    if firmware.is_file():
        artifacts.append(
            {
                "path": firmware.name,
                "platform": "M-VAVE FM-1",
                "format": "firmware",
                "size": firmware.stat().st_size,
                "sha256": _sha256(firmware),
            }
        )
    for path in sorted((out / "plugins").glob("*/*.zip")):
        upper = path.name.upper()
        fmt = "VST3" if "VST3" in upper else "CLAP" if "CLAP" in upper else "plugin"
        artifacts.append(
            {
                "path": path.relative_to(out).as_posix(),
                "platform": path.parent.name,
                "format": fmt,
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return artifacts


def _human_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} kB"
    return f"{size} B"


def _write_release(
    out: Path,
    title: str,
    version: str,
    commit: str,
    artifacts: list[ReleaseArtifact],
    released: str | None = None,
) -> None:
    """Write `RELEASES.md`, `SHA256SUMS`, and `release.json` for the downloads."""
    released = released or datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [
        f"# {title} {version}",
        "",
        f"Released {released} from source `{commit}`.",
        "",
        "## Downloads",
        "",
        "| File | Platform | Format | Size | SHA-256 |",
        "| --- | --- | --- | --- | --- |",
    ]
    sums: list[str] = []
    for artifact in artifacts:
        path = artifact["path"]
        digest = artifact["sha256"]
        lines.append(
            f"| [`{Path(path).name}`]({path}) | {artifact['platform']} | "
            f"{artifact['format']} | {_human_size(artifact['size'])} | `{digest}` |"
        )
        sums.append(f"{digest}  {path}")
    lines += [
        "",
        "The firmware is the device image. Flash it with `umetate flash`.",
    ]
    has_plugins = any(artifact["format"] != "firmware" for artifact in artifacts)
    if has_plugins:
        lines += [
            "The plugin archives are optional and use the same engine as the firmware",
            "and the web app.",
        ]
    lines += [
        "",
        "## Sources",
        "",
        "- `src/` is the project: the patch, the panel, the app glue, and the plugin",
        "  identity.",
        "- `framework/` is the complete umetate source, including the generator, the",
        "  plugin, and the tests.",
    ]
    if (out / "vendor" / "deps").is_dir():
        lines.append("- `vendor/deps/` carries the fetched plugin dependency source.")
    lines += [
        "- `LICENSING.md`, `DEPENDENCIES.md`, and `third-party-licenses/` carry the",
        "  notices and the exact upstream pins.",
        "",
        "## Licence",
        "",
        "The firmware and the umetate source are GPL-3.0-only.",
    ]
    if has_plugins:
        lines += [
            "The plugin archives link JUCE 8, which is AGPL-3.0-only or commercial,",
            "so the plugin archives are conveyed under the AGPL-3.0-only terms for",
            "the JUCE part.",
        ]
    lines += [
        "See `LICENSING.md`.",
        "",
        f"`{_CHECKSUM_FILE}` lists every download. Verify with",
        f"`sha256sum -c {_CHECKSUM_FILE}`.",
        "",
    ]
    (out / _RELEASE_FILE).write_text("\n".join(lines), encoding="utf-8")
    (out / _CHECKSUM_FILE).write_text("\n".join(sums) + "\n", encoding="utf-8")
    manifest = {
        "product": title,
        "version": version,
        "commit": commit,
        "date": released,
        "artifacts": artifacts,
    }
    (out / _MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def _remove_tree(path: Path) -> None:
    """Remove a tree even when the copied files are read-only."""
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            with contextlib.suppress(OSError):
                (Path(root) / name).chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    shutil.rmtree(path)


def _copy_vendor(src: Path, dest: Path) -> None:
    """Copy the fetched dependency source, without git histories or build trees."""
    if dest.exists():
        _remove_tree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".git", "*-build", "*-subbuild"),
    )


def _write_dependencies(out: Path, vendored: bool) -> None:
    text = _DEPENDENCIES
    if vendored:
        text += """
## Vendored sources

The fetched sources are copied into `vendor/deps/`. Build against them with:

```sh
cmake -S framework/plugin -B build/plugin -DP1_BUILD_JUCE=ON -DP1_BUILD_CLAP=ON \\
  -DFETCHCONTENT_SOURCE_DIR_JUCE=vendor/deps/juce-src \\
  -DFETCHCONTENT_SOURCE_DIR_CLAP-JUCE-EXTENSIONS=vendor/deps/clap-juce-extensions-src
```
"""
    (out / "DEPENDENCIES.md").write_text(text, encoding="utf-8")


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
        "--title", help="the display name for the README (default: plugin.json)"
    )
    parser.add_argument(
        "--repo-url",
        default="https://USERNAME.github.io/REPO/",
        help="the GitHub Pages URL the README links to",
    )
    parser.add_argument(
        "--plugins",
        action="store_true",
        help="zip the built VST3 and CLAP artefacts into plugins/<platform>/",
    )
    parser.add_argument(
        "--plugin-build",
        type=Path,
        help="a JUCE build tree (default: the first one with artefacts)",
    )
    parser.add_argument(
        "--plugin-platform",
        help="platform tag for the plugin archives (default: the build host)",
    )
    parser.add_argument(
        "--vendor-deps",
        type=Path,
        help="copy fetched plugin dependency sources into vendor/deps/",
    )
    args = parser.parse_args(argv)

    synth_dir: Path = args.synth_dir
    if not (synth_dir / "patch.json").is_file():
        print(f"publish: {synth_dir / 'patch.json'} not found", file=sys.stderr)
        return 2
    name = _name_of(synth_dir)
    cname = to_c_identifier(name)
    out = args.out or _PUBLISH / name
    title = args.title or _project_title(synth_dir, name)

    out.mkdir(parents=True, exist_ok=True)
    missing = _gather(synth_dir, name, cname, out)
    bundled = _snapshot_framework(out, cname)

    platform = args.plugin_platform or _platform_tag()
    plugin_build = args.plugin_build or _default_plugin_build()
    staged: list[str] = []
    if args.plugins:
        staged = _stage_plugins(out, plugin_build, platform, title)
        if not staged:
            missing.append(
                f"plugins (no VST3 or CLAP under {plugin_build}; "
                "build the JUCE targets first)"
            )
        else:
            licence_dir = _ROOT / "third-party-licenses"
            if licence_dir.is_dir():
                shutil.copytree(
                    licence_dir, out / "third-party-licenses", dirs_exist_ok=True
                )
            else:
                missing.append("third-party-licenses (missing at the repo root)")

    vendored = False
    if args.vendor_deps:
        if args.vendor_deps.is_dir():
            _copy_vendor(args.vendor_deps, out / "vendor" / "deps")
            vendored = True
        else:
            missing.append(f"vendor deps (no {args.vendor_deps})")
    _write_dependencies(out, vendored)

    # the project's own README wins over the generated template, so a human-written
    # front door is preserved verbatim (not overwritten by the loop).
    user_readme = synth_dir / "publish-readme.md"
    if user_readme.is_file():
        shutil.copy2(user_readme, out / "README.md")
    else:
        readme = _README.format(
            title=title,
            repo_url=args.repo_url,
            fwsc=f"{name}.fwsc",
            plugins=_PLUGINS_SECTION if staged else "",
            plugin_source=_PLUGIN_SOURCE_SECTION if staged else "",
        )
        (out / "README.md").write_text(readme, encoding="utf-8")

    _write_release(
        out,
        title,
        _version_of(synth_dir),
        _source_commit(),
        _release_artifacts(out, name),
    )

    print(f"publish: {out}")
    print(
        "  RELEASES.md, SHA256SUMS, release.json, README.md, CHANGELOG.md, "
        "LICENSE, LICENSING.md, DEPENDENCIES.md, src/, docs/, framework/, the "
        "web app (root), and " + f"{name}.fwsc"
    )
    if staged:
        print(f"  plugins/{platform}/: " + ", ".join(staged))
        print("  third-party-licenses/: AGPL, MIT CLAP, MIT wrapper, two OFL fonts")
    if missing:
        print("  missing (build first):")
        for m in missing:
            print(f"    - {m}")
    else:
        print("  all artifacts present.")
    if not bundled:
        print("  note: could not snapshot the framework source (no git/HEAD);")
        print("        the README still links the umetate repo for it.")
    if user_readme.is_file() and staged:
        print("  note: README.md is your hand-written file. Add a link to")
        print("        plugins/README.md if you want the builds on the front page.")
    if not staged:
        print("  note: no plugin archives staged. Run with --plugins after a")
        print("        JUCE build to include them.")
    print("  next: `git init` here, commit, then push to a GitHub repo with Pages")
    print("  (set the Pages source to the repo root).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
