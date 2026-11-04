# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate interview` - the synth-specific design interview for the docs.

The interview is the raw material for a manual preface or a design note. The
command reads the project's `patch.json`, `panel.json`, `synth-brief.md`, and
`plugin.json`, then renders the generic question form with questions in the
synth's own vocabulary. It does not assume FM, operators, or Type P.fm1.

The command does not run the conversation. It writes the form, prints the next
unanswered questions, and tells the writer where the gaps are. The protocol is in
the documentation skill.

Run: `umetate interview --write`, then `--next 3` after each answer, then `--check`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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


@dataclass(frozen=True)
class ProjectFacts:
    """The pieces of a project the interview generator reads."""

    name: str
    patch_name: str
    parts: int
    voices: int
    params: int
    voice_nodes: tuple[str, ...]
    global_nodes: tuple[str, ...]
    pages: tuple[str, ...]
    home_pages: tuple[str, ...]
    tables: tuple[str, ...]
    taps: tuple[str, ...]
    brief: dict[str, str]


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


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return cast(dict[str, object], raw) if isinstance(raw, dict) else None


def _brief_items(text: str) -> dict[str, str]:
    """Read the `- **Key:** value` bullets from a synth brief."""
    items: dict[str, str] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        match = re.match(r"^\s*-\s+\*\*([^*]+):\*\*\s*(.*)$", line)
        if match:
            current = match.group(1).strip()
            items[current] = match.group(2).strip()
        elif current and line.startswith((" ", "\t")) and line.strip():
            items[current] = f"{items[current]} {line.strip()}"
        elif line.startswith("#") or line.startswith("- "):
            current = None
    return items


def _item(brief: dict[str, str], *prefixes: str) -> str:
    for key, value in brief.items():
        low = key.lower()
        if any(low.startswith(prefix) for prefix in prefixes):
            return value
    return ""


def _clip(value: str, limit: int = 240) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def _counts(nodes: tuple[str, ...]) -> str:
    order: list[str] = []
    counts: dict[str, int] = {}
    for node in nodes:
        if node not in counts:
            order.append(node)
            counts[node] = 0
        counts[node] += 1
    return ", ".join(
        name if counts[name] == 1 else f"{name} x{counts[name]}" for name in order
    )


def _page_title(page: dict[str, object]) -> str:
    widgets = page.get("widgets")
    if isinstance(widgets, list):
        for widget in widgets:
            if not isinstance(widget, dict):
                continue
            if widget.get("type") == "subheader" and isinstance(
                widget.get("text"), str
            ):
                return cast(str, widget["text"])
    for key in ("title", "id"):
        value = page.get(key)
        if isinstance(value, str) and value:
            return value
    return "page"


def _panel_pages(panel: dict[str, object]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    contexts = panel.get("contexts")
    if not isinstance(contexts, dict):
        return (), ()
    pages: list[str] = []
    home_pages: list[str] = []
    home = panel.get("home")
    for context_name, context in cast(dict[str, object], contexts).items():
        if not isinstance(context, dict):
            continue
        raw_pages = context.get("pages")
        if not isinstance(raw_pages, list):
            continue
        titles: list[str] = []
        for page in raw_pages:
            if not isinstance(page, dict):
                continue
            title = _page_title(cast(dict[str, object], page))
            titles.append(title)
            if title not in pages:
                pages.append(title)
        if context_name == home:
            home_pages = titles
    return tuple(pages), tuple(home_pages)


def load_facts(synth: Path) -> ProjectFacts:
    """Read the project into the pieces the form generator uses."""
    patch = _read_json(synth / "patch.json") or {}
    panel = _read_json(synth / "panel.json") or {}
    plugin = _read_json(synth / "plugin.json") or {}
    brief_path = synth / "synth-brief.md"
    brief = (
        _brief_items(brief_path.read_text(encoding="utf-8"))
        if brief_path.is_file()
        else {}
    )

    patch_name = patch.get("name")
    patch_name = patch_name if isinstance(patch_name, str) else ""
    product = plugin.get("product_name")
    product_name = product if isinstance(product, str) and product else ""
    working = _item(brief, "working name")
    working = working.split(" (", 1)[0].strip() if working else ""
    name = product_name or patch_name or working or synth.name

    parts = 1
    raw_parts = patch.get("parts")
    if isinstance(raw_parts, dict):
        count = cast(dict[str, object], raw_parts).get("count")
        if isinstance(count, int) and count > 0:
            parts = count

    voices = patch.get("voices")
    voices = voices if isinstance(voices, int) and voices > 0 else 0

    params = patch.get("params")
    param_count = len(params) if isinstance(params, dict) else 0

    def node_types(zone: object) -> tuple[str, ...]:
        if not isinstance(zone, dict):
            return ()
        nodes = cast(dict[str, object], zone).get("nodes")
        if not isinstance(nodes, list):
            return ()
        types: list[str] = []
        for node in nodes:
            if isinstance(node, dict) and isinstance(node.get("type"), str):
                types.append(cast(str, node["type"]))
        return tuple(types)

    voice_nodes = node_types(patch.get("voice"))
    global_nodes = node_types(patch.get("global"))

    tables = patch.get("tables")
    table_names = (
        tuple(cast(dict[str, object], tables).keys())
        if isinstance(tables, dict)
        else ()
    )
    taps = patch.get("taps")
    tap_names = (
        tuple(item for item in taps if isinstance(item, str))
        if isinstance(taps, list)
        else ()
    )

    pages, home_pages = _panel_pages(panel)
    return ProjectFacts(
        name=name,
        patch_name=patch_name,
        parts=parts,
        voices=voices,
        params=param_count,
        voice_nodes=voice_nodes,
        global_nodes=global_nodes,
        pages=pages,
        home_pages=home_pages,
        tables=table_names,
        taps=tap_names,
        brief=brief,
    )


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _summary(facts: ProjectFacts) -> str:
    bits: list[str] = []
    bits.append(f"The project is **{facts.name}**")
    if facts.patch_name and facts.patch_name != facts.name:
        bits[-1] += f" (patch `{facts.patch_name}`)"
    counts: list[str] = []
    if facts.parts > 1:
        counts.append(_plural(facts.parts, "part"))
    if facts.voices:
        counts.append(_plural(facts.voices, "voice"))
    if facts.params:
        counts.append(_plural(facts.params, "parameter"))
    if counts:
        bits.append("It has " + ", ".join(counts) + ".")
    if facts.voice_nodes:
        bits.append("The voice zone uses " + _counts(facts.voice_nodes) + ".")
    if facts.global_nodes:
        bits.append("The global zone uses " + _counts(facts.global_nodes) + ".")
    if facts.pages:
        bits.append("The panel has these pages: " + ", ".join(facts.pages) + ".")
    synthesis = _item(facts.brief, "synthesis method")
    if synthesis:
        bits.append("The brief says the synthesis method is " + _clip(synthesis) + ".")
    if len(bits) == 1:
        bits.append(
            "No patch.json, panel.json, or synth-brief.md yet. The form uses the "
            "generic questions."
        )
    return " ".join(bits)


def _bq(question: str) -> str:
    lines = textwrap.wrap(question, width=76) or [question]
    return "**Q:** " + lines[0] + "\n" + "\n".join(lines[1:]) + "\n**A:**"


def _block(questions: list[str]) -> str:
    return "\n\n".join(_bq(question) for question in questions)


def _extras(facts: ProjectFacts) -> dict[str, str]:
    brief = facts.brief
    references = _item(
        brief, "three reference sounds", "reference sounds", "references"
    )
    synthesis = _item(brief, "synthesis method")
    effects = _item(brief, "effects and output", "effects")
    controls = _item(brief, "keys, buttons", "control surface", "controls")
    feel = _item(brief, "what should it feel like")
    who = _item(brief, "who plays it")
    non_goals = _item(brief, "explicit non-goals", "non-goals")

    lineage: list[str] = []
    if references:
        lineage.append(
            f"The brief lists these references: {_clip(references)}. "
            "What did you take from each?"
        )
    if synthesis:
        lineage.append(
            f"The brief describes the synthesis method as: {_clip(synthesis)}. "
            "Why this method?"
        )
    if facts.voice_nodes:
        lineage.append(
            f"The voice zone uses {_counts(facts.voice_nodes)}. "
            "Which of those carries the character?"
        )

    architecture: list[str] = []
    if facts.voice_nodes:
        architecture.append(
            f"The voice zone uses {_counts(facts.voice_nodes)}. Why this chain?"
        )
    feedback = sum(
        1 for node in facts.voice_nodes if node.startswith(("delay", "comb"))
    )
    if feedback:
        architecture.append(
            f"The voice zone has {_plural(feedback, 'feedback path')}. "
            "What does feedback make possible?"
        )
    if facts.params:
        architecture.append(
            f"The patch exposes {_plural(facts.params, 'parameter')}. "
            "Which ones matter most to the sound, and which are deliberately hidden?"
        )
    if facts.tables:
        architecture.append(
            "The patch uses tables: " + ", ".join(facts.tables) + ". What are they for?"
        )
    if facts.taps:
        architecture.append(
            f"The patch exposes taps: {', '.join(facts.taps)}. "
            "What do you use them for?"
        )

    output: list[str] = []
    if facts.global_nodes:
        output.append(
            f"The global zone uses {_counts(facts.global_nodes)}. "
            "Why this chain, and what did you try before it?"
        )
    if effects:
        output.append(
            f"The brief describes the output stage as: {_clip(effects)}. "
            "Why this choice?"
        )

    interface: list[str] = []
    if facts.pages:
        interface.append(
            f"The panel has these pages: {', '.join(facts.pages)}. Why these pages?"
        )
    if facts.home_pages:
        interface.append(
            "The home page shows " + ", ".join(facts.home_pages) + ". Why these first?"
        )
    if controls:
        interface.append(
            f"The brief describes the control surface as: {_clip(controls)}. "
            "Why this layout?"
        )

    tradeoff: list[str] = []
    if non_goals:
        tradeoff.append(f"The brief's non-goals are: {_clip(non_goals)}. Why those?")
    polyphony = _item(brief, "polyphony")
    if polyphony:
        tradeoff.append(
            f"The brief sets the polyphony at {_clip(polyphony)}. "
            "What did that budget force?"
        )

    sound: list[str] = []
    if feel:
        sound.append(
            f"The brief says it should feel: {_clip(feel)}. "
            "What did you do to make it feel that way?"
        )
    if who:
        sound.append(
            f"The brief says it is for: {_clip(who)}. "
            "What should that player hear first?"
        )

    return {
        "lineage_extra": _block(lineage),
        "architecture_extra": _block(architecture),
        "output_extra": _block(output),
        "interface_extra": _block(interface),
        "tradeoff_extra": _block(tradeoff),
        "sound_extra": _block(sound),
    }


def generate_form(synth: Path) -> str:
    """Render the generic form with the project's own facts and questions."""
    facts = load_facts(synth)
    template = _TEMPLATE.read_text(encoding="utf-8")
    values = {"name": facts.name, "summary": _summary(facts), **_extras(facts)}
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


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
    try:
        text = generate_form(synth)
    except OSError as exc:
        print(f"interview: cannot generate the form: {exc}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
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
        description="generate and check the synth-specific design interview",
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
        help="generate the question form from the project",
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
