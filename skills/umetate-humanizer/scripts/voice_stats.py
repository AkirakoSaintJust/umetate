#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Measure prose rhythm against the umetate voice calibration.

This is the rhythm gate for the humanizer and documentation skills. It reads
Markdown prose paragraphs or multi-sentence code comments, counts the sentence
lengths, and compares the result with the hand-written manual, the K5/K5000
guide, or the reference register.

Usage:
    python skills/umetate-humanizer/scripts/voice_stats.py [paths ...]
        [--kind markdown|comments]
        [--register manual|guide|auto|technical|reference]
        [--json]

With no paths, it measures the tracked Markdown files in the repository,
excluding the hand-written front doors and the generated module library.
The Markdown meter counts prose paragraphs. It skips frontmatter, fenced code,
headings, tables, blockquotes, and list items. Wrapped list continuations are
counted as prose, so a rule-heavy file can read flatter than its paragraphs.
The comment meter counts C block comments, C++/C line comments, Python
docstrings, and Python line comments. It skips structured blocks such as
register maps, tables, and signature lists.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import statistics
import subprocess
import sys
import tokenize
from pathlib import Path

MARKDOWN_EXCLUDE = {
    "README.md",
    "examples/type-p-fm1/publish-readme.md",
    "examples/type-p-fm1/docs/manual.md",
    "docs/module-library.md",
    "skills/umetate-development/references/code-conventions.md",
    "skills/umetate-development/references/platform-facts.md",
    "skills/umetate-safety/references/code-conventions.md",
    "skills/umetate-safety/references/platform-facts.md",
}

COMMENT_EXCLUDE = (
    "build/",
    "vendor/",
    "third-party-licenses/",
    ".jieli/",
    ".tools/",
    "publish/",
    "firmware/gen/",
    "firmware/vendor/",
)

BANDS = {
    "manual": {
        "mean": (14.5, 17.0),
        "median": (12.0, 15.0),
        "stdev": (10.0, 14.5),
    },
    "guide": {
        "mean": (16.0, 19.0),
        "median": (13.0, 16.0),
        "stdev": (10.5, 18.0),
    },
    "auto": {
        "mean": (13.5, 19.0),
        "median": (11.0, 16.0),
        "stdev": (9.5, 18.0),
    },
    "technical": {
        "mean": (13.5, 20.0),
        "median": (10.0, 17.0),
        "stdev": (8.5, 15.0),
    },
    "reference": None,
}


def _tracked(pattern: str) -> list[str]:
    try:
        out = subprocess.check_output(["git", "ls-files", pattern], text=True)
        return out.splitlines()
    except Exception:
        return [
            str(path)
            for path in Path(".").rglob(pattern)
            if ".git" not in path.parts and "build" not in path.parts
        ]


def default_markdown() -> list[str]:
    files = _tracked("*.md")
    return [
        f
        for f in files
        if f not in MARKDOWN_EXCLUDE
        and not any(f.startswith(prefix) for prefix in COMMENT_EXCLUDE)
    ]


def default_comments() -> list[str]:
    files = []
    for pattern in ("*.c", "*.h", "*.cpp", "*.hpp", "*.py"):
        files.extend(_tracked(pattern))
    return [
        f
        for f in files
        if not any(f.startswith(prefix) for prefix in COMMENT_EXCLUDE)
    ]


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)


def prose_blocks(text: str) -> list[str]:
    text = _strip_frontmatter(text)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith("|")
            or stripped.startswith(">")
            or re.match(r"^[-*+]\s", stripped)
            or re.match(r"^\d+[.)]\s", stripped)
        ):
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        blocks.append(" ".join(current))
    return [block for block in blocks if len(block.split()) >= 8]


def _c_blocks(text: str) -> list[str]:
    blocks = []
    for match in re.finditer(r"/\*.*?\*/", text, re.S):
        body = re.sub(r"^\s*/\*+|\*/\s*$", "", match.group(0))
        body = re.sub(r"^\s*\*\s?", "", body, flags=re.M)
        blocks.append(body)
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if re.match(r"^\s*//", lines[index]):
            group = []
            while index < len(lines) and re.match(r"^\s*//", lines[index]):
                group.append(re.sub(r"^\s*//\s?", "", lines[index]))
                index += 1
            blocks.append("\n".join(group))
        else:
            index += 1
    return blocks


def _py_blocks(text: str) -> list[str]:
    blocks = []
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    blocks.append(doc)
    except SyntaxError:
        pass
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if re.match(r"^\s*#", lines[index]):
            group = []
            while index < len(lines) and re.match(r"^\s*#", lines[index]):
                group.append(re.sub(r"^\s*#\s?", "", lines[index]))
                index += 1
            blocks.append("\n".join(group))
        else:
            index += 1
    return blocks


def _looks_structured(block: str) -> bool:
    """True for register maps, tables, signature lists, and other non-prose."""
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return True
    structured = 0
    for line in lines:
        if re.match(
            r"^(#|static|void|int|enum|uint|if|for|while|return|typedef|struct|class)\b",
            line,
        ):
            structured += 1
        elif re.search(r"\s{3,}", line):
            structured += 1
        elif re.search(r"[|+][-=]{2,}", line):
            structured += 1
    return structured / len(lines) > 0.4


def comment_blocks(path: Path, text: str) -> list[str]:
    blocks = _py_blocks(text) if path.suffix == ".py" else _c_blocks(text)
    result = []
    for block in blocks:
        words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", block))
        sentences = len(re.findall(r"[.!?](?:\s|$)", block))
        if words >= 30 and sentences >= 2 and not _looks_structured(block):
            result.append(block)
    return result


def sentences(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text)
        if part.strip()
    ]


def measure(texts: list[str]) -> dict[str, float | int]:
    lengths: list[int] = []
    first = contractions = brackets = exclamations = 0
    for text in texts:
        for sentence in sentences(text):
            length = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", sentence))
            if not length:
                continue
            lengths.append(length)
            first += len(
                re.findall(r"\b(?:I|me|my|mine|myself|we|us|our|ours)\b", sentence)
            )
            contractions += len(
                re.findall(
                    r"\b\w+(?:'|’)(?:s|t|re|ve|ll|d|m)\b", sentence, re.I
                )
            )
            brackets += sentence.count("(")
            exclamations += sentence.count("!")
    if not lengths:
        return {
            "words": 0,
            "sentences": 0,
            "mean": 0.0,
            "median": 0.0,
            "stdev": 0.0,
            "max": 0,
            "short5": 0,
            "long50": 0,
            "first": 0,
            "contractions": 0,
            "brackets": 0,
            "exclamations": 0,
        }
    return {
        "words": sum(lengths),
        "sentences": len(lengths),
        "mean": round(statistics.mean(lengths), 1),
        "median": statistics.median(lengths),
        "stdev": round(statistics.pstdev(lengths), 1),
        "max": max(lengths),
        "short5": sum(1 for length in lengths if length <= 5),
        "long50": sum(1 for length in lengths if length >= 50),
        "first": first,
        "contractions": contractions,
        "brackets": brackets,
        "exclamations": exclamations,
    }


def verdict(stats: dict[str, float | int], register: str) -> tuple[bool, list[str]]:
    band = BANDS[register]
    if band is None:
        return True, ["reference register, no rhythm target"]
    notes = []
    passed = True
    for key in ("mean", "median", "stdev"):
        low, high = band[key]
        value = float(stats[key])
        if not low <= value <= high:
            passed = False
            notes.append(f"{key} {value} outside {low} to {high}")
    if int(stats["sentences"]) >= 80 and int(stats["max"]) < 50:
        notes.append("no sentence over 50 words, the page may have no long setup")
    if int(stats["sentences"]) >= 80 and int(stats["short5"]) == 0:
        notes.append("no short sentences, the page may have no landings")
    if passed and not notes:
        notes.append("in band")
    return passed, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voice_stats",
        description="Measure prose rhythm against the umetate voice calibration.",
    )
    parser.add_argument("paths", nargs="*", help="files or directories to measure")
    parser.add_argument(
        "--kind",
        choices=("markdown", "comments"),
        default="markdown",
        help="markdown prose paragraphs or multi-sentence comments",
    )
    parser.add_argument(
        "--register",
        choices=("manual", "guide", "auto", "technical", "reference"),
        default="auto",
        help="calibration band; auto is the repo-wide band",
    )
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    if args.paths:
        files: list[str] = []
        for raw in args.paths:
            path = Path(raw)
            if path.is_dir():
                pattern = "*.md" if args.kind == "markdown" else "*"
                files.extend(str(p) for p in path.rglob(pattern))
            else:
                files.append(str(path))
    else:
        files = default_markdown() if args.kind == "markdown" else default_comments()

    files = sorted(dict.fromkeys(files))
    rows = []
    all_texts: list[str] = []
    for name in files:
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        texts = prose_blocks(text) if args.kind == "markdown" else comment_blocks(path, text)
        if not texts:
            continue
        all_texts.extend(texts)
        stats = measure(texts)
        passed, notes = verdict(stats, args.register)
        rows.append({"file": name, "stats": stats, "pass": passed, "notes": notes})

    total = measure(all_texts)
    total_pass, total_notes = verdict(total, args.register)

    if args.json:
        print(
            json.dumps(
                {
                    "kind": args.kind,
                    "register": args.register,
                    "files": rows,
                    "total": {"stats": total, "pass": total_pass, "notes": total_notes},
                },
                indent=2,
            )
        )
        return 0 if total_pass else 1

    header = (
        f"{'file':58} {'w':>6} {'s':>5} {'mean':>5} {'med':>4} "
        f"{'sd':>5} {'max':>4} {'<=5':>4} {'>=50':>5} {'I':>3} {'contr':>5} "
        f"{'()':>3} {'!':>2}"
    )
    print(header)
    for row in rows:
        stats = row["stats"]
        print(
            f"{row['file']:58} {stats['words']:6} {stats['sentences']:5} "
            f"{stats['mean']:5} {stats['median']:4} {stats['stdev']:5} "
            f"{stats['max']:4} {stats['short5']:4} {stats['long50']:5} "
            f"{stats['first']:3} {stats['contractions']:5} "
            f"{stats['brackets']:3} {stats['exclamations']:2}"
        )
    print()
    print(f"TOTAL {json.dumps(total)}")
    print(f"register: {args.register}")
    print(f"verdict: {'pass' if total_pass else 'fail'}")
    for note in total_notes:
        print(f"  {note}")
    if args.register != "reference":
        print(
            "A pass needs the mean, median, and standard deviation together. "
            "A high median with a low spread means the page is uniformly long. "
            "A low median with a low spread means it is uniformly short."
        )
    return 0 if total_pass else 1


if __name__ == "__main__":
    sys.exit(main())
