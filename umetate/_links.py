# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The docs' cross-reference check (roadmap §12.8, P6-1).

Scans the canonical docs for Markdown link/image destinations and verifies each
relative target resolves to a file. Scope: file paths only — `#anchor` suffixes
are stripped and `http(s)://`/`mailto:` are ignored (no heading-slug validation).

Run standalone: `python -m umetate._links check`, or via `umetate deep-check --links`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# the canonical docs (relative to the repo root), each scanned for links
_DOCS: tuple[Path, ...] = (
    _ROOT / "README.md",
    _ROOT / "LICENSING.md",
    _ROOT / "firmware" / "README.md",
    *(_ROOT / "docs").glob("*.md"),
)

# `[text](dest)` / `![alt](dest)`, with an optional `"title"` after the destination.
_LINK = re.compile(r"!?\[([^\]\n]*)\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")


def _targets(doc: Path) -> list[tuple[str, str]]:
    """Return `(destination, display)` for every Markdown link/image in `doc`."""
    text = doc.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for match in _LINK.finditer(text):
        label, dest = match.group(1), match.group(2)
        # skip task-list checkboxes rendered as `[ ]`/`[x]`
        if re.fullmatch(r"\s*[xX]?\s*", label):
            continue
        out.append((dest, label))
    return out


def _check_dest(doc: Path, dest: str) -> str | None:
    """Return an error string if `dest` is a dead relative link, else `None`."""
    if not dest or dest.startswith(("#", "http://", "https://", "mailto:", "<")):
        return None
    path = dest.split("#", 1)[0]
    resolved = (doc.parent / path).resolve()
    if resolved.is_file():
        return None
    return f"{doc.relative_to(_ROOT)}: dead link -> {dest!r}"


def check() -> list[str]:
    """Return the list of dead-link errors across the canonical docs (empty = ok)."""
    errors: list[str] = []
    for doc in sorted(_DOCS):
        for dest, _label in _targets(doc):
            error = _check_dest(doc, dest)
            if error:
                errors.append(error)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate._links", description=__doc__)
    parser.add_argument("action", choices=("check",), nargs="?", default="check")
    parser.parse_args(argv)

    errors = check()
    if errors:
        for error in errors:
            print(f"_links: {error}", file=sys.stderr)
        return 1
    print("_links: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
