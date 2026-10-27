# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The panel generator (docs/roadmap.md §12.6): panel.json -> the UI tables.

Emits a `panel.h` of `static const` tables (widgets, pages, contexts, bindings, the
`PANEL` struct) that the shipped runtime (`firmware/src/ui.c`) renders. Param names
and source/action/behavior strings are resolved to the fixed numeric ids in `ui.h`;
an unknown name is a GenError, never a silently-wrong table.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._ir import GenError, to_c_identifier

# ---- the fixed input-source vocabulary (ui.h) ----
_SOURCES = {
    "KEY": "UI_SRC_KEY",
    "BTN_OCT_DOWN": "UI_SRC_BTN_OCT_DOWN",
    "BTN_OCT_UP": "UI_SRC_BTN_OCT_UP",
    "ENC_PRESETS": "UI_SRC_ENC_PRESETS",
    "FM1_ADC_MASTER": "UI_SRC_ADC_MASTER",
    "ENC_KNOB1": "UI_SRC_ENC_KNOB1",
    "ENC_KNOB2": "UI_SRC_ENC_KNOB2",
    "ENC_KNOB3": "UI_SRC_ENC_KNOB3",
    "ENC_KNOB4": "UI_SRC_ENC_KNOB4",
    "ENC_KNOB5": "UI_SRC_ENC_KNOB5",
    "ENC_KNOB6": "UI_SRC_ENC_KNOB6",
    "ENC_KNOB7": "UI_SRC_ENC_KNOB7",
    "ENC_SELECT": "UI_SRC_ENC_SELECT",
    "BTN_EDIT": "UI_SRC_BTN_EDIT",
    "BTN_HOME": "UI_SRC_BTN_HOME",
    "BTN_PLAY": "UI_SRC_BTN_PLAY",
    "BTN_STOP": "UI_SRC_BTN_STOP",
    "BTN_REC": "UI_SRC_BTN_REC",
    "BTN_SAVE": "UI_SRC_BTN_SAVE",
    "BTN_SEQ": "UI_SRC_BTN_SEQ",
}
# prefix sources: "cc:123" -> UI_SRC_CC_BASE + 123, etc.
_PREFIX_SOURCES = {
    "cc": "UI_SRC_CC_BASE",
    "note": "UI_SRC_NOTE_BASE",
    "pad": "UI_SRC_PAD_BASE",
    "fader": "UI_SRC_FADER_BASE",
    "wheel": "UI_SRC_WHEEL_BASE",
}

_ACTIONS = {
    "note_on": "UI_ACT_NOTE_ON",
    "note_off": "UI_ACT_NOTE_OFF",
    "set_step": "UI_ACT_SET_STEP",
    "push": "UI_ACT_PUSH",
    "pop": "UI_ACT_POP",
    "pop_home": "UI_ACT_POP_HOME",
    "next_page": "UI_ACT_NEXT_PAGE",
    "prev_page": "UI_ACT_PREV_PAGE",
    "set_page": "UI_ACT_SET_PAGE",
    "bank_next": "UI_ACT_BANK_NEXT",
    "bank_prev": "UI_ACT_BANK_PREV",
    "toggle": "UI_ACT_TOGGLE",
    "latch": "UI_ACT_LATCH",
    "save": "UI_ACT_SAVE",
    "load": "UI_ACT_LOAD",
    "panic": "UI_ACT_PANIC",
    "play": "UI_ACT_PLAY",
    "stop": "UI_ACT_STOP",
}

_BEHAVIORS = {
    "absolute": "UI_ABS",
    "relative": "UI_REL",
    "momentary": "UI_MOMENTARY",
    "latch": "UI_LATCH",
    "toggle": "UI_TOGGLE",
}

_WIDGETS = {
    "label": "UI_LABEL",
    "value": "UI_VALUE",
    "bar": "UI_BAR",
    "param_row": "UI_PARAM_ROW",
    "param_column": "UI_PARAM_COLUMN",
    "list": "UI_LIST",
    "grid": "UI_GRID",
}


def generate_panel(
    panel: Mapping[str, Any], param_ids: Mapping[str, int] | None = None
) -> str:
    """Compile a panel.json dict into the generated `panel.h` C source.

    `param_ids` (optional) maps a param name to its DSP `set_param` id; when given,
    the panel's `P_x` enum shares that id space, so a knob writes the right param.
    """
    name = str(panel["name"])
    contexts = {str(k): v for k, v in dict(panel["contexts"]).items()}
    ctx_names = list(contexts.keys())
    ctx_ids = {n: i for i, n in enumerate(ctx_names)}
    ids = {str(k): int(v) for k, v in dict(param_ids or {}).items()}
    params: dict[str, int] = {}

    def param_id(pname: str) -> int:
        if param_ids is not None:
            if pname not in ids:
                raise GenError(f"unknown param {pname!r}")
            return ids[pname]
        if pname not in params:
            params[pname] = len(params)
        return params[pname]

    def param_sym(pname: str) -> str:
        param_id(pname)
        return f"P_{to_c_identifier(pname)}"

    def source_expr(source: str) -> str:
        if source in _SOURCES:
            return _SOURCES[source]
        for prefix, base in _PREFIX_SOURCES.items():
            if source.startswith(prefix + ":"):
                return f"{base} + {int(source.split(':', 1)[1])}"
        raise GenError(f"unknown source {source!r}")

    def action_expr(action: str) -> str:
        if action in _ACTIONS:
            return _ACTIONS[action]
        raise GenError(f"unknown action {action!r}")

    def arg_expr(arg: str | None, action: str) -> str:
        if arg is None:
            return "0"
        if arg in ctx_ids:
            return str(ctx_ids[arg])
        if action == "set_step" and arg.isdigit():
            return arg
        return "0"

    def cstr(value: str | None) -> str:
        return f'"{value}"' if value else "0"

    def binding_line(b: Mapping[str, Any]) -> str:
        source = source_expr(str(b["source"]))
        behavior = _BEHAVIORS.get(str(b.get("behavior", "absolute")), "UI_ABS")
        if b.get("target"):
            kind, target = "UI_BIND_PARAM", param_sym(str(b["target"]))
            action, arg = "0", "0"
        else:
            kind = "UI_BIND_ACTION"
            target = "0"
            action = action_expr(str(b["action"]))
            arg = arg_expr(
                str(b.get("arg")) if b.get("arg") is not None else None,
                str(b["action"]),
            )
        return f"    {{ {kind}, {source}, {target}, {action}, {arg}, {behavior}, 0 }},"

    def widget_line(w: Mapping[str, Any]) -> str:
        typ = _WIDGETS.get(str(w["type"]))
        if typ is None:
            raise GenError(f"unknown widget type {w['type']!r}")
        row = int(w.get("row", 0))
        col = int(w.get("col", 0))
        span = int(w.get("span", 1))
        param = param_sym(str(w["param"])) if w.get("param") else "UI_NO_PARAM"
        text = cstr(w.get("text"))
        unit = cstr(w.get("unit"))
        fmt = cstr(w.get("fmt"))
        items = [str(i) for i in w.get("items", [])]
        if items:
            items_field = (
                "(const char *const[]){" + ", ".join(f'"{i}"' for i in items) + "}"
            )
        else:
            items_field = "0"
        return (
            f"    {{ {typ}, {row}, {col}, {span}, {param}, {text}, {unit}, "
            f"{fmt}, {items_field}, {len(items)} }},"
        )

    # ---- pre-pass: assign param ids (widgets, then bindings) ----
    for ctx in contexts.values():
        for page in ctx.get("pages", []):
            for w in page.get("widgets", []):
                if w.get("param"):
                    param_id(str(w["param"]))
        for b in ctx.get("bindings", []):
            if b.get("target"):
                param_id(str(b["target"]))
    for b in panel.get("global", []):
        if b.get("target"):
            param_id(str(b["target"]))

    lines = [
        "/* SPDX-License-Identifier: GPL-3.0-only",
        " * Copyright (C) 2026 P1Onken (umetate) */",
        "/* GENERATED by umetate from panel.json — do not edit. */",
        "#pragma once",
        '#include "ui.h"',
        "",
    ]

    if param_ids is not None:
        refs = _referenced_params(panel, contexts)
        names = ", ".join(f"P_{to_c_identifier(n)} = {ids[n]}" for n in refs)
        n_params = max(ids.values()) + 1 if ids else 0
        if names:
            lines.append(f"enum {{ {names}, N_PARAMS = {n_params} }};")
        else:
            lines.append(f"enum {{ N_PARAMS = {n_params} }};")
    elif params:
        names = ", ".join(
            f"P_{to_c_identifier(n)} = {i}"
            for n, i in sorted(params.items(), key=lambda kv: kv[1])
        )
        lines.append(f"enum {{ {names}, N_PARAMS }};")
    else:
        lines.append("enum { N_PARAMS = 0 };")
    lines.append("")

    widget_count = 0
    for ci, ctx in enumerate(ctx_names):
        pages = contexts[ctx].get("pages", [])
        page_decls: list[str] = []
        for pi, page in enumerate(pages):
            wname = f"W_{ci}_{pi}"
            lines.append(f"static const ui_widget {wname}[] = {{")
            lines.extend(widget_line(w) for w in page.get("widgets", []))
            lines.append("};")
            widget_count += len(page.get("widgets", []))
            page_decls.append(
                f'    {{ "", {wname}, (uint8_t)(sizeof {wname} / sizeof {wname}[0]) }},'
            )
        lines.append(f"static const ui_page PG_{ci}[] = {{")
        lines.extend(page_decls)
        lines.append("};")

    for ci, ctx in enumerate(ctx_names):
        bname = f"BIND_{ci}"
        lines.append(f"static const ui_binding {bname}[] = {{")
        lines.extend(binding_line(b) for b in contexts[ctx].get("bindings", []))
        lines.append("};")

    lines.append("static const ui_binding GLOBAL_BIND[] = {")
    lines.extend(binding_line(b) for b in panel.get("global", []))
    lines.append("};")
    lines.append("")

    lines.append("static const ui_context CTX[] = {")
    for ci, ctx in enumerate(ctx_names):
        lines.append(
            f"    {{ PG_{ci}, {len(contexts[ctx].get('pages', []))}, BIND_{ci}, "
            f"{len(contexts[ctx].get('bindings', []))}, 0, 0 }},"
        )
    lines.append("};")
    lines.append("")

    home = str(ctx_ids[str(panel.get("home", "home"))])
    n_params = (
        (max(ids.values()) + 1 if ids else 0) if param_ids is not None else len(params)
    )
    lines.append("static const ui_tables PANEL = {")
    lines.append(
        f'    "{name}", {home}, CTX, {len(ctx_names)}, GLOBAL_BIND, '
        f"{len(panel.get('global', []))}, {n_params}, {widget_count},"
    )
    lines.append("};")
    return "\n".join(lines) + "\n"


def _referenced_params(
    panel: Mapping[str, Any], contexts: Mapping[str, Any]
) -> list[str]:
    """The distinct param names the panel references, in first-seen order."""
    refs: list[str] = []

    def note(pname: str) -> None:
        if pname not in refs:
            refs.append(pname)

    for ctx in contexts.values():
        for page in ctx.get("pages", []):
            for w in page.get("widgets", []):
                if w.get("param"):
                    note(str(w["param"]))
        for b in ctx.get("bindings", []):
            if b.get("target"):
                note(str(b["target"]))
    for b in panel.get("global", []):
        if b.get("target"):
            note(str(b["target"]))
    return refs
