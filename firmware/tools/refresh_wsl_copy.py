#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Refresh the Linux-filesystem umetate copy used for WSL builds.

Run from the Windows checkout in WSL with: python3 tools/refresh_wsl_copy.py
The source .git and build/ directories are not copied, whilst ~/umetate/build is
preserved.
"""
from pathlib import Path
import os
import shutil
import sys

MARKER = ".wsl-build-copy"


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def is_executable_shell(path):
    if path.suffix == ".sh":
        return True
    if not path.stat().st_mode & 0o111:
        return False
    with path.open("rb") as script:
        return script.read(2) == b"#!"


def copy_entry(source, destination):
    if source.is_symlink():
        remove(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            remove(destination)
        destination.mkdir(parents=True, exist_ok=True)
    else:
        if destination.is_symlink() or destination.is_dir():
            remove(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if is_executable_shell(destination):
            contents = destination.read_bytes()
            normalized = contents.replace(b"\r\n", b"\n")
            if normalized != contents:
                destination.write_bytes(normalized)
                shutil.copystat(source, destination)


def refresh(source, destination):
    if "microsoft" not in Path("/proc/version").read_text(errors="replace").lower():
        raise RuntimeError("run this helper from a WSL shell")
    source = source.resolve()
    destination = destination.expanduser().absolute()
    if destination.is_symlink():
        raise RuntimeError(f"refusing symlink destination: {destination}")
    if destination == source or destination in source.parents or source in destination.parents:
        raise RuntimeError(f"unsafe destination: {destination}")

    marker = destination / MARKER
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise RuntimeError(f"refusing unexpected marker path: {marker}")
    owned = marker.is_file()
    source_id = f"umetate WSL build copy\nsource={source}\n"
    if owned and marker.read_text() != source_id:
        raise RuntimeError(f"{destination} is marked as a copy of a different checkout")
    if destination.exists() and not owned:
        looks_like_umetate = (
            (destination / "build.sh").is_file()
            and (destination / "src/rib.c").is_file()
        )
        if any(destination.iterdir()) and not looks_like_umetate and not (destination / "build").is_dir():
            raise RuntimeError(f"refusing to overwrite non-umetate directory: {destination}")
        if (destination / ".git").exists():
            raise RuntimeError(f"refusing to sync into a Git checkout: {destination}")

    destination.mkdir(parents=True, exist_ok=True)
    expected_files = set()
    expected_dirs = {Path(".")}
    for root, dirs, files in os.walk(source, followlinks=False):
        root = Path(root)
        relative_root = root.relative_to(source)
        kept_dirs = []
        for name in dirs:
            src_dir = root / name
            if name == ".git" or (relative_root == Path(".") and name == "build"):
                continue
            rel = relative_root / name
            dst_dir = destination / rel
            if src_dir.is_symlink():
                copy_entry(src_dir, dst_dir)
                expected_files.add(rel)
            else:
                copy_entry(src_dir, dst_dir)
                expected_dirs.add(rel)
                kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in files:
            if name == ".git":
                continue
            src_file = root / name
            rel = relative_root / name
            if rel == Path(MARKER):
                continue
            copy_entry(src_file, destination / rel)
            expected_files.add(rel)

    if owned:
        expected = expected_files | expected_dirs | {Path(MARKER)}
        for root, dirs, files in os.walk(destination, topdown=False, followlinks=False):
            root = Path(root)
            relative_root = root.relative_to(destination)
            for name in files:
                rel = relative_root / name
                if rel not in expected and not (relative_root == Path("build") or relative_root.is_relative_to("build")):
                    remove(root / name)
            for name in dirs:
                rel = relative_root / name
                if name != ".git" and rel not in expected and not (rel == Path("build") or rel.is_relative_to("build")):
                    remove(root / name)

    marker.write_text(source_id)
    print(f"WSL source copy refreshed: {destination}")
    print("Preserved WSL build outputs: " + str(destination / "build"))
    if not owned:
        print("Initial sync: existing files were left in place unless replaced by checkout files.")


def main():
    if len(sys.argv) != 1:
        raise SystemExit("usage: python3 tools/refresh_wsl_copy.py")
    source = Path(__file__).resolve().parent.parent
    try:
        refresh(source, Path.home() / "umetate")
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"refresh_wsl_copy: {error}")


if __name__ == "__main__":
    main()
