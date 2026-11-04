# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""Render a synth project into the generated C files.

One shared step behind `umetate build --synth` and `umetate plugin-generate`, so
the firmware and the plugin cannot drift apart. `generate_project` only reads the
project and returns a filename-to-text map. `write_project` writes it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ._ir import GenError, to_c_identifier
from ._panel import generate_panel
from ._schema import PanelManifest, Patch, as_panel, as_patch
from .generate import (
    generate,
    generate_cc_header,
    generate_dsp_header,
    generate_glue,
    generate_params,
    generate_synth_header,
    generate_sysex_layout,
    generate_tables,
    param_ids,
    param_meta,
)


@dataclass(frozen=True)
class GeneratedProject:
    """A rendered project: the C name plus every generated file's contents."""

    name: str
    patch: Patch
    panel: PanelManifest
    outputs: dict[str, str]


def generate_project(synth: Path) -> GeneratedProject:
    """Read `patch.json`, `panel.json` and `app.c`, then render every generated file.

    Raises `GenError` for an unreadable project or a generation error, never a
    silent fallback.
    """
    try:
        patch = as_patch(json.loads((synth / "patch.json").read_text(encoding="utf-8")))
        panel = as_panel(json.loads((synth / "panel.json").read_text(encoding="utf-8")))
        app_c = (synth / "app.c").read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise GenError(f"cannot read the project in {synth}: {exc}") from exc

    try:
        name = to_c_identifier(patch["name"])
        tables_h, tables_c = generate_tables(patch)
        ids = param_ids(patch)
        meta = param_meta(patch)
        outputs: dict[str, str] = {
            f"{name}_dsp.c": generate(patch),
            "dsp.h": generate_dsp_header(patch),
            "glue.h": generate_glue(patch),
            "tables.h": tables_h,
            "tables.c": tables_c,
            "panel.h": generate_panel(panel, ids, meta),
            "cc_map.h": generate_cc_header(patch),
            "synth_layout.h": generate_synth_header(patch),
            "params.json": json.dumps(generate_params(patch), indent=2) + "\n",
            "sysex-layout.json": json.dumps(generate_sysex_layout(patch), indent=2)
            + "\n",
            "app.c": app_c,
        }
    except GenError as exc:
        raise GenError(f"{synth}: {exc}") from exc

    return GeneratedProject(name=name, patch=patch, panel=panel, outputs=outputs)


def write_project(project: GeneratedProject, out_dir: Path) -> list[Path]:
    """Write every generated file into `out_dir` and return the paths in order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, content in project.outputs.items():
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
