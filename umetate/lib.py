# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate lib` — list the shipped nodes + macros + templates (local, no registry).

`markdown` prints the node library as a Markdown table generated from the
manifests (the authoritative source — `docs/module-library.md` is the checked-in
copy, so the roadmap's node table can never drift from the manifests). `generate`
writes that file; `check` regenerates to memory and diffs (any drift is an error).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._schema import (
    Macro,
    NodeManifest,
    ParamSpec,
    ParamTarget,
    PortDict,
    as_macro,
    as_node_manifest,
)

_ROOT = Path(__file__).resolve().parents[1]
_NODES = _ROOT / "modules" / "nodes"
_MACROS = _ROOT / "modules" / "macros"
_EXAMPLES = _ROOT / "examples"
_MODULE_LIBRARY_DOC = _ROOT / "docs" / "module-library.md"


def _list_nodes() -> list[str]:
    lines: list[str] = []
    for manifest in sorted(_NODES.glob("*/node.json")):
        name = manifest.parent.name
        summary = as_node_manifest(
            json.loads(manifest.read_text(encoding="utf-8"))
        ).get("summary", "")
        lines.append(f"node     {name:<12} {summary}")
    return lines


def _list_macros() -> list[str]:
    lines: list[str] = []
    for manifest in sorted(_MACROS.glob("*/macro.json")):
        name = manifest.parent.name
        summary = as_macro(json.loads(manifest.read_text(encoding="utf-8"))).get(
            "summary", ""
        )
        lines.append(f"macro    {name:<12} {summary}")
    return lines


def _list_templates() -> list[str]:
    lines: list[str] = []
    for template in sorted(p for p in _EXAMPLES.glob("*/") if p.is_dir()):
        lines.append(f"template {template.name}")
    return lines


# ----------------------------------------------------------------- node table ----


def _port(p: str, spec: str | PortDict) -> str:
    """A port as `` `name`(rate) `` (the format/default live in the manifest)."""
    rate = spec if isinstance(spec, str) else spec.get("rate", "")
    return f"`{p}`({rate})"


def _param(p: str, spec: str | ParamSpec) -> str:
    """A param as `` `name`(kind) `` (+ `, modulatable` when paired)."""
    if isinstance(spec, str):
        return f"`{p}`({spec})"
    kind = spec["kind"]
    return (
        f"`{p}`({kind}, modulatable)" if spec.get("modulatable") else f"`{p}`({kind})"
    )


def _join(items: list[str]) -> str:
    return ", ".join(items) if items else "—"


def _row(manifest: NodeManifest) -> str:
    ins = [_port(p, s) for p, s in sorted((manifest.get("ins") or {}).items())]
    outs = [_port(p, s) for p, s in sorted((manifest.get("outs") or {}).items())]
    params = [_param(p, s) for p, s in sorted((manifest.get("params") or {}).items())]
    state = [f"`{f}`({t})" for f, t in sorted((manifest.get("state") or {}).items())]
    return (
        f"| `{manifest['name']}` | {manifest.get('summary', '')} | {_join(ins)} | "
        f"{_join(outs)} | {_join(params)} | {_join(state)} |"
    )


def _macro_param(p: str, spec: str | ParamTarget) -> str:
    """A macro param as `` `name` → `target` `` (+ `, note_derived`)."""
    if isinstance(spec, str):
        return f"`{p}` → `{spec}`"
    target = spec["target"]
    if spec.get("note_derived"):
        return f"`{p}` → `{target}` (note_derived)"
    return f"`{p}` → `{target}`"


def _macro_row(name: str, manifest: Macro) -> str:
    ins = [_port(p, s) for p, s in sorted(manifest["ins"].items())]
    outs = [_port(p, s) for p, s in sorted(manifest["outs"].items())]
    params = [
        _macro_param(p, s) for p, s in sorted((manifest.get("params") or {}).items())
    ]
    return (
        f"| `{name}` | {manifest.get('summary', '')} | {_join(ins)} | "
        f"{_join(outs)} | {_join(params)} |"
    )


def render_markdown() -> str:
    """The generated module-library tables (nodes + macros, from the manifests)."""
    node_rows = [
        _row(as_node_manifest(json.loads(m.read_text(encoding="utf-8"))))
        for m in sorted(_NODES.glob("*/node.json"))
    ]
    macro_rows = [
        _macro_row(m.parent.name, as_macro(json.loads(m.read_text(encoding="utf-8"))))
        for m in sorted(_MACROS.glob("*/macro.json"))
    ]
    return (
        "<!-- GENERATED — do not edit. Source: modules/nodes/*/node.json + "
        "modules/macros/*/macro.json. Regenerate with `umetate lib generate`. -->\n\n"
        "# Module library\n\n"
        "## Nodes\n\n"
        "| Node | Summary | Ins | Outs | Params | State |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(node_rows)
        + "\n\n## Macros\n\n"
        "| Macro | Summary | Ins | Outs | Params |\n"
        "| --- | --- | --- | --- | --- |\n" + "\n".join(macro_rows) + "\n"
    )


def generate() -> None:
    """Write `docs/module-library.md` (bytes, so LF line endings are preserved)."""
    _MODULE_LIBRARY_DOC.write_bytes(render_markdown().encode("utf-8"))


def check() -> list[str]:
    """The module-library drift errors (empty = in sync)."""
    if not _MODULE_LIBRARY_DOC.is_file():
        return ["docs/module-library.md: missing (run `umetate lib generate`)"]
    if _MODULE_LIBRARY_DOC.read_text(encoding="utf-8") != render_markdown():
        return ["docs/module-library.md is out of date (run `umetate lib generate`)"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate lib", description=__doc__)
    parser.add_argument(
        "action",
        choices=("list", "markdown", "generate", "check"),
        default="list",
        nargs="?",
    )
    args = parser.parse_args(argv)

    if args.action == "list":
        for line in _list_nodes():
            print(line)
        for line in _list_macros():
            print(line)
        for line in _list_templates():
            print(line)
    elif args.action == "markdown":
        print(render_markdown(), end="")
    elif args.action == "generate":
        generate()
        print(f"lib: wrote {_MODULE_LIBRARY_DOC}")
    else:
        errors = check()
        if errors:
            for error in errors:
                print(f"lib: {error}", file=sys.stderr)
            return 1
        print("lib: module library in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
