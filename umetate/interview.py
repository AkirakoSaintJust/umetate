# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate interview` - the design interview question bank for the docs.

The interview is the raw material for a manual preface or a design note. The
command does not run the conversation. It writes the form, prints the next
unanswered questions, and tells the writer where the gaps are. The questions are
in `templates/design-interview.md`; the protocol is in the documentation skill.

Run: `umetate interview --write`, then `--next 3` after each answer, then `--check`.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = _ROOT / "examples"
_TEMPLATE = _ROOT / "templates" / "design-interview.md"
_FORM = "design-interview.md"


@dataclass(frozen=True)
class Question:
    """One prompt and the answer recorded under it."""

    section: str
    prompt: str
    answer: str

    @property
    def answered(self) -> bool:
        text = re.sub(r"<!--.*?-->", "", self.answer, flags=re.S).strip()
        return bool(text)


def parse_questions(text: str) -> list[Question]:
    """Parse the `## section`, `**Q:**`, `**A:**` form."""
    section = ""
    prompt = ""
    answer: list[str] = []
    in_answer = False
    questions: list[Question] = []

    def flush() -> None:
        nonlocal prompt, answer, in_answer
        if prompt:
            questions.append(Question(section, prompt, "\n".join(answer).strip()))
        prompt = ""
        answer = []
        in_answer = False

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
        elif line.startswith("**Q:**"):
            flush()
            prompt = line[len("**Q:**") :].strip()
        elif line.startswith("**A:**"):
            answer = [line[len("**A:**") :].strip()]
            in_answer = True
        elif prompt and in_answer:
            answer.append(line)
        elif prompt and not in_answer:
            prompt = f"{prompt} {line.strip()}".strip()
    flush()
    return questions


def _notes(synth: Path) -> Path:
    return synth / _FORM


def _questions(synth: Path) -> list[Question] | None:
    path = _notes(synth)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        print(
            f"interview: no notes at {path}; run `umetate interview --write`",
            file=sys.stderr,
        )
        return None
    return parse_questions(text)


def _write(synth: Path, force: bool) -> int:
    target = _notes(synth)
    if target.exists() and not force:
        print(
            f"interview: {target} exists; pass --force to overwrite",
            file=sys.stderr,
        )
        return 1
    if not _TEMPLATE.is_file():
        print(f"interview: no question form at {_TEMPLATE}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_TEMPLATE, target)
    print(f"interview: wrote {target}")
    print("  ask one topic at a time; `umetate interview --next 3` prints the gaps")
    return 0


def _check(synth: Path) -> int:
    questions = _questions(synth)
    if questions is None:
        return 1
    gaps = [question for question in questions if not question.answered]
    if not gaps:
        print(f"interview: all {len(questions)} questions answered")
        return 0
    print(
        f"interview: {len(gaps)} of {len(questions)} questions still open",
        file=sys.stderr,
    )
    for question in gaps:
        print(f"  [{question.section}] {question.prompt}", file=sys.stderr)
    return 1


def _next(synth: Path, count: int) -> int:
    questions = _questions(synth)
    if questions is None:
        return 1
    gaps = [question for question in questions if not question.answered]
    if not gaps:
        print(
            f"interview: all {len(questions)} questions answered; write the design note"
        )
        return 0
    for index, question in enumerate(gaps[: max(1, count)], 1):
        print(f"{index}. [{question.section}] {question.prompt}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="umetate interview",
        description="write and check the design interview form",
    )
    parser.add_argument(
        "--synth",
        type=Path,
        default=_EXAMPLES / "type-p-fm1",
        help="the project dir (default: examples/type-p-fm1)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the question form into the project",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing form",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="list every unanswered question",
    )
    parser.add_argument(
        "--next",
        type=int,
        default=3,
        metavar="N",
        help="print the next N unanswered questions (default: 3)",
    )
    args = parser.parse_args(argv)
    synth = args.synth.resolve()
    if not synth.is_dir():
        print(f"interview: no project at {synth}", file=sys.stderr)
        return 2
    if args.write:
        return _write(synth, args.force)
    if args.check:
        return _check(synth)
    return _next(synth, args.next)


if __name__ == "__main__":
    sys.exit(main())
