# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The offline skill bundles' generated `references/` (roadmap §6.2/§6.3, P5).

`references/` are byte-for-byte copies of the canonical docs (with a `GENERATED`
banner where the format allows), so a skill is self-contained without becoming a
second source of truth. `generate` writes them; `check` regenerates to memory and
diffs — any drift is an error, never silently accepted.

Run `python -m umetate._skill generate` to (re)write the bundles after editing a
canonical source.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"

# (skill, generated path) -> (canonical source, banner?)
# Markdown sources get a `GENERATED` banner; JSON schemas are copied byte-for-byte
# (JSON has no comments, so no banner is possible there).
_SOURCES: dict[tuple[str, str], tuple[str, bool]] = {
    (
        "umetate-development",
        "references/platform-facts.md",
    ): ("docs/platform-facts.md", True),
    (
        "umetate-development",
        "references/code-conventions.md",
    ): ("firmware/README.md", True),
    (
        "umetate-development",
        "references/schemas/node.schema.json",
    ): ("templates/scaffold/node.schema.json", False),
    (
        "umetate-development",
        "references/schemas/patch.schema.json",
    ): ("templates/scaffold/patch.schema.json", False),
    (
        "umetate-development",
        "references/schemas/params.schema.json",
    ): ("templates/scaffold/params.schema.json", False),
    (
        "umetate-development",
        "references/schemas/panel.schema.json",
    ): ("templates/scaffold/panel.schema.json", False),
    (
        "umetate-safety",
        "references/platform-facts.md",
    ): ("docs/platform-facts.md", True),
    (
        "umetate-safety",
        "references/code-conventions.md",
    ): ("firmware/README.md", True),
}


def _banner(source: str) -> str:
    return (
        f"<!-- GENERATED - do not edit. Source: {source}. "
        "Regenerate with `python -m umetate._skill generate`. -->\n\n"
    )


def render(skill: str, rel: str) -> str:
    """The exact text the generated file at `skill`/`rel` must contain."""
    source, banner = _SOURCES[(skill, rel)]
    text = (_ROOT / source).read_text(encoding="utf-8")
    return (_banner(source) + text) if banner else text


def generate() -> None:
    """(Re)write every generated `references/` file from its canonical source.

    Writes bytes (not `write_text`), so the canonical sources' LF line endings are
    preserved verbatim — on Windows, `write_text` would re-translate `\n` to `\r\n`
    and every regeneration would churn the committed copies.
    """
    for (skill, rel), _ in _SOURCES.items():
        dest = _SKILLS / skill / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(render(skill, rel).encode("utf-8"))


@dataclass
class Drift:
    skill: str
    rel: str
    source: str

    def message(self) -> str:
        return (
            f"skills/{self.skill}/{self.rel} is out of date\n"
            f"  source: {self.source}\n"
            f"  fix:    python -m umetate._skill generate"
        )


def check() -> list[str]:
    """Return the list of drift/missing/`SKILL.md` errors (empty = clean)."""
    errors: list[str] = []
    for (skill, rel), (source, _) in _SOURCES.items():
        dest = _SKILLS / skill / rel
        if not dest.is_file():
            errors.append(f"skills/{skill}/{rel}: missing")
            continue
        if dest.read_text(encoding="utf-8") != render(skill, rel):
            errors.append(Drift(skill, rel, source).message())
    for skill in (
        "umetate-development",
        "umetate-safety",
        "umetate-documentation",
        "umetate-humanizer",
    ):
        errors.extend(_check_skill_manifest(skill))
    return errors


_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _check_skill_manifest(skill: str) -> list[str]:
    """A skill must exist with a `name` + `description` frontmatter."""
    errors: list[str] = []
    path = _SKILLS / skill / "SKILL.md"
    if not path.is_file():
        return [f"skills/{skill}/SKILL.md: missing"]
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER.match(text)
    if m is None:
        return [f"skills/{skill}/SKILL.md: missing `---` frontmatter"]
    for key in ("name", "description"):
        if not re.search(rf"^{key}:\s*\S", m.group(1), re.MULTILINE):
            errors.append(f"skills/{skill}/SKILL.md: missing `{key}:`")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate._skill", description=__doc__)
    parser.add_argument("action", choices=("generate", "check"))
    args = parser.parse_args(argv)
    if args.action == "generate":
        generate()
        print("_skill: regenerated the skill references/ bundles")
        return 0
    errors = check()
    if errors:
        for error in errors:
            print(f"_skill: {error}", file=sys.stderr)
        return 1
    print("_skill: bundles in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
