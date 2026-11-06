# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The panel generator (docs/roadmap.md §12.6): panel.json -> the UI tables.

Emits a `panel.h` of `static const` tables (widgets, pages, contexts, bindings, and
the `PANEL` struct) that the shipped runtime (`firmware/src/ui.c`) renders. Param
names and the source, action, and behaviour strings resolve to the fixed numeric
ids in `ui.h`. An unknown name raises a GenError rather than writing a
silently-wrong table.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from ._ir import GenError, to_c_identifier
from ._ratio import ratio_detents
from ._schema import Context, PanelBinding, PanelManifest, Widget

# firmware/src/ui.h UI_PART_MAX: the header mute flags and the name slots are
# per part, so a panel cannot declare more parts than the kit tracks.
_UI_PART_MAX = 8

# ---- the fixed input-source vocabulary (ui.h) ----
_SOURCES = {
    "KEY": "UI_SRC_KEY",
    "BTN_OCT_DOWN": "UI_SRC_BTN_OCT_DOWN",
    "BTN_OCT_UP": "UI_SRC_BTN_OCT_UP",
    "ENC_PRESETS": "UI_SRC_ENC_PRESETS",
    "ENC_ALGORITHM": "UI_SRC_ENC_ALGORITHM",
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
    "BTN_FX": "UI_SRC_BTN_FX",
    "BTN_SEL": "UI_SRC_BTN_SEL",
    "BTN_ENV": "UI_SRC_BTN_ENV",
    "BTN_LFO": "UI_SRC_BTN_LFO",
    "BTN_GLO": "UI_SRC_BTN_GLO",
    "BTN_ARP": "UI_SRC_BTN_ARP",
}
# prefix sources: "cc:123" -> UI_SRC_CC_BASE + 123, etc.
_PREFIX_SOURCES = {
    "cc": "UI_SRC_CC_BASE",
    "note": "UI_SRC_NOTE_BASE",
    "pad": "UI_SRC_PAD_BASE",
    "fader": "UI_SRC_FADER_BASE",
    "wheel": "UI_SRC_WHEEL_BASE",
}

# ---- the per-board control inventory (firmware/src/platform.c BTN_*/ENC_* enums) ----
# A panel may only bind sources the target board actually has, so `KEY` and the
# MIDI prefixes (`cc:`, `note:`) are universal whilst `pad:`, `fader:`, and
# `wheel:` belong to the SMK-37 only.
_BOARD_SOURCES: dict[str, frozenset[str]] = {
    "fm1": frozenset(
        {
            "KEY",
            "FM1_ADC_MASTER",
            "BTN_OCT_DOWN",
            "BTN_OCT_UP",
            "BTN_FX",
            "BTN_SEL",
            "BTN_ENV",
            "BTN_LFO",
            "BTN_EDIT",
            "BTN_GLO",
            "BTN_HOME",
            "BTN_SAVE",
            "BTN_ARP",
            "BTN_SEQ",
            "BTN_PLAY",
            "BTN_REC",
            "ENC_SELECT",
            "ENC_ALGORITHM",
            "ENC_KNOB1",
            "ENC_KNOB2",
            "ENC_KNOB3",
            "ENC_KNOB4",
            "ENC_PRESETS",
        }
    ),
    "smk37": frozenset(
        {
            "KEY",
            "FM1_ADC_MASTER",
            "BTN_OCT_DOWN",
            "BTN_OCT_UP",
            "BTN_ARP",
            "BTN_LFO",
            "BTN_SEL",
            "BTN_ENV",
            "BTN_GLO",
            "BTN_SAVE",
            "BTN_HOME",
            "BTN_EDIT",
            "BTN_FX",
            "BTN_SEQ",
            "BTN_PLAY",
            "BTN_REC",
            "ENC_SELECT",
            "ENC_ALGORITHM",
            "ENC_PRESETS",
            "ENC_KNOB1",
            "ENC_KNOB2",
            "ENC_KNOB3",
            "ENC_KNOB4",
        }
    ),
}
_UNIVERSAL_PREFIXES = ("cc:", "note:")
_BOARD_PREFIXES: dict[str, tuple[str, ...]] = {
    "fm1": (),
    "smk37": ("pad:", "fader:", "wheel:"),
}


def _iter_panel_sources(panel: PanelManifest) -> Iterator[str]:
    """Every control source the panel binds, in the global + context bindings."""
    for binding in panel.get("global", []):
        yield binding["source"]
    for context in panel["contexts"].values():
        for binding in context.get("bindings", []):
            yield binding["source"]


def check_sources(panel: PanelManifest, board: str) -> list[str]:
    """The panel's sources the target `board` does not have (empty = all valid).

    This is the source-vocabulary check (roadmap §6.11 L1), which stops a panel
    binding a control that the board lacks (e.g. `ENC_KNOB5` on the FM-1).
    """
    valid = _BOARD_SOURCES.get(board)
    if valid is None:
        return [f"unknown board {board!r} (expected {', '.join(_BOARD_SOURCES)})"]
    prefixes = _UNIVERSAL_PREFIXES + _BOARD_PREFIXES.get(board, ())
    return [
        source
        for source in _iter_panel_sources(panel)
        if source not in valid and not source.startswith(prefixes)
    ]


_ACTIONS = {
    "note_on": "UI_ACT_NOTE_ON",
    "note_off": "UI_ACT_NOTE_OFF",
    "set_step": "UI_ACT_SET_STEP",
    "push": "UI_ACT_PUSH",
    "pop": "UI_ACT_POP",
    "switch": "UI_ACT_SWITCH",
    "pop_home": "UI_ACT_POP_HOME",
    "next_page": "UI_ACT_NEXT_PAGE",
    "prev_page": "UI_ACT_PREV_PAGE",
    "page": "UI_ACT_PAGE",
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
    "op_next": "UI_ACT_OP_NEXT",
    "op_prev": "UI_ACT_OP_PREV",
    "op_mute": "UI_ACT_OP_MUTE",
    "op_mute_n": "UI_ACT_OP_MUTE_N",
    "part_next": "UI_ACT_PART_NEXT",
    "part_mute": "UI_ACT_PART_MUTE",
    "init_patch": "UI_ACT_INIT_PATCH",
    "init_part": "UI_ACT_INIT_PART",
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
    "envelope": "UI_ENVELOPE",
    "genv": "UI_GENV",
    "scope": "UI_SCOPE",
    "spectro": "UI_SPECTRO",
    "status": "UI_STATUS",
    "subheader": "UI_SUBHEADER",
    "name": "UI_NAME",
    "algo": "UI_ALGO",
    "band": "UI_BAND",
    "custom": "UI_CUSTOM",
}

# the per-param display scale (a patch `params:` `display` string -> ui.h enum)
_DISPLAY = {
    "raw": "UI_DISP_RAW",
    "ratio": "UI_DISP_RATIO",
    "pct": "UI_DISP_PCT",
    "pct_bip": "UI_DISP_PCT_BIP",
    "pct_inv": "UI_DISP_PCT_INV",
    "onoff": "UI_DISP_ONOFF",
    "onoff_inv": "UI_DISP_ONOFF_INV",
    "off_pct": "UI_DISP_OFF_PCT",
    "hz": "UI_DISP_HZ",
    "semi": "UI_DISP_SEMI",
    "semi_fine": "UI_DISP_SEMI_FINE",
    "cent": "UI_DISP_CENT",
    "wave": "UI_DISP_WAVE",
    "filter": "UI_DISP_FILTER",
    "fold": "UI_DISP_FOLD",
    "mode": "UI_DISP_MODE",
    "priority": "UI_DISP_PRIORITY",
    "note": "UI_DISP_NOTE",
    "porta": "UI_DISP_PORTA",
}


# The coarse-ratio detents are shared with the plugin editor. They are every
# integer multiple of 0.5, 1, sqrt(2), pi/2 and sqrt(3), with sqrt(2)/2, pi/4 and
# sqrt(3)/2 added in the lower range. See `umetate/_ratio.py`.
def _ratio_landmarks(lo: int, hi: int) -> list[int]:
    """The sorted Q16 coarse-ratio landmarks in [lo, hi]."""
    return ratio_detents(lo, hi)


_Q15_OCTAVE = 32768


def _semi_landmarks(lo: int, hi: int) -> list[int]:
    """Every integer semitone in [lo, hi] (Q15, 32768 = one octave), plus the
    range endpoints. Values are rounded away from zero so the signed 2-decimal
    display is exactly `N.00` for both signs, and 32767 adds the +11.99 top."""
    if lo > hi:
        return []
    first = -((-lo * 12) // _Q15_OCTAVE)  # ceil(lo * 12 / 32768)
    last = (hi * 12) // _Q15_OCTAVE
    vals: set[int] = set()
    for k in range(first, last + 1):
        mag = (abs(k) * _Q15_OCTAVE + 11) // 12  # ceil(|k| * 32768 / 12)
        v = mag if k >= 0 else -mag
        if lo <= v <= hi:
            vals.add(v)
    vals.add(lo)
    vals.add(hi)
    return sorted(vals)


def _semi_fine_landmarks(lo: int, hi: int) -> list[int]:
    """The integer semitones plus the 0.02, 0.05, 0.10, 0.30, 0.50 and 0.75
    offsets inside each one, in Q15. The values are rounded away from zero for the
    same reason as `_semi_landmarks`: the 2-decimal display truncates, so a value
    just past the fraction is what reads as that fraction."""
    vals = set(_semi_landmarks(lo, hi))
    first = -((-lo * 12) // _Q15_OCTAVE)
    last = (hi * 12) // _Q15_OCTAVE
    for k in range(first, last + 1):
        for frac in (2, 5, 10, 30, 50, 75):  # hundredths of a semitone
            num = k * 100 + (frac if k >= 0 else -frac)  # hundredths of a semitone
            mag = (abs(num) * _Q15_OCTAVE + 1199) // 1200  # away from zero
            v = mag if num >= 0 else -mag
            if lo <= v <= hi:
                vals.add(v)
    return sorted(vals)


def generate_panel(
    panel: PanelManifest,
    param_ids: Mapping[str, int] | None = None,
    param_meta: Mapping[int, tuple[str, int, int, str]] | None = None,
) -> str:
    """Compile a panel.json dict into the generated `panel.h` C source.

    `param_ids` (optional) maps a param name to its DSP `set_param` id, and when it
    is given the panel's `P_x` enum shares that id space, so a knob writes the right
    param. `param_meta` (optional) maps a param id to `(display, min, max, curve)`,
    which is the per-param display scale the runtime uses to format and step the
    value.
    """
    name = panel["name"]
    contexts = panel["contexts"]
    ctx_names = list(contexts.keys())
    ctx_ids = {n: i for i, n in enumerate(ctx_names)}
    ids = dict(param_ids or {})
    params: dict[str, int] = {}
    operators = panel.get("operators") or []
    n_parts = panel.get("parts", 1)
    if not 1 <= n_parts <= _UI_PART_MAX:
        raise GenError(
            f"panel: parts must be 1..{_UI_PART_MAX} (the UI kit's UI_PART_MAX)"
        )
    op_names: list[str] = []  # the operator-relative param "rest" parts, first-seen
    env_names: list[str] = []  # the envelope's 7 op-relative "rest" parts
    part_names: list[str] = []  # the part-relative params (the GLO part pages)
    genv_groups: list[
        tuple[str, ...]
    ] = []  # the global-envelope 7-param groups, first-seen

    def op_rest(pname: str) -> str | None:
        """If `pname` is operator-relative (`opN.<rest>`), return the `<rest>` part."""
        for op in operators:
            if pname.startswith(op + "."):
                return pname[len(op) + 1 :]
        return None

    def param_id(pname: str) -> int:
        if param_ids is not None:
            if pname not in ids:
                raise GenError(f"unknown param {pname!r}")
            return ids[pname]
        if pname not in params:
            params[pname] = len(params)
        return params[pname]

    def part_entry(pname: str, part: int) -> int:
        """A param's id at `part`: part 0 is the unsuffixed (part-0) name, later
        parts the `.pN` name. The names exist only for a multi-part patch."""
        return param_id(pname) if part == 0 else param_id(f"{pname}.p{part}")

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
        if arg.isdigit():
            return arg
        if arg in ctx_ids:
            return str(ctx_ids[arg])
        return "0"

    def cstr(value: str | None) -> str:
        return f'"{value}"' if value else "0"

    def binding_line(b: PanelBinding) -> str:
        source = source_expr(b["source"])
        behavior = _BEHAVIORS.get(b.get("behavior", "absolute"), "UI_ABS")
        slot = b.get("slot")
        target = b.get("target")
        if slot is not None:
            kind, param, action, arg = "UI_BIND_PAGE_SLOT", "0", "0", str(slot)
        elif target:
            kind = "UI_BIND_PART_PARAM" if b.get("part") else "UI_BIND_PARAM"
            param = param_sym(target)
            action, arg = "0", "0"
        else:
            action_name = b.get("action", "")
            kind = "UI_BIND_ACTION"
            param = "0"
            action = action_expr(action_name)
            arg = arg_expr(b.get("arg"), action_name)
        return f"    {{ {kind}, {source}, {param}, {action}, {arg}, {behavior}, 0 }},"

    def subheader_mode(w: Widget) -> int:
        """The subheader prefix mode: 0 = "OP N", 1 = "PART N", 2 = "OP",
        3 = "PART", 4 = plain (no prefix), 5 = "PART n OP"."""
        if w.get("plain"):
            return 4
        if w.get("partop"):
            return 5
        if w.get("plural"):
            return 3 if w.get("part") else 2
        return 1 if w.get("part") else 0

    def widget_line(w: Widget, row_shift: int = 0) -> str:
        row = w.get("row", 0) - row_shift
        col = w.get("col", 0)
        span = w.get("span", 1)
        if w["type"] == "envelope":
            typ = "UI_ENVELOPE"
            op = w.get("op")
            param = (
                str(op) if isinstance(op, int) and 0 <= op <= 7 else "0xFFFF"
            )  # a fixed operator, or the selected operator
        elif w["type"] == "genv":
            typ = "UI_GENV"
            param = str(
                genv_groups.index(tuple(w.get("params", [])))
            )  # the group index
        elif w["type"] in ("scope", "spectro"):
            typ = _WIDGETS[w["type"]]
            # the scope source: `channel` = the op index (0..3 -> "op N of the
            # active part"), `active` = the active operator of the active part
            # (0x40), `mix_part` = the part index (0..1 -> "part N mix", encoded
            # with the high bit so the runtime can tell them apart), `final` =
            # the final post-FX mix (0xC0, ch 0).
            mix_part = w.get("mix_part")
            channel = w.get("channel", 0)
            if w.get("final"):
                param = str(0xC0)
            elif w.get("active"):
                param = str(0x40)
            elif mix_part is not None:
                if not 0 <= mix_part < n_parts:
                    raise GenError(
                        f"{w['type']} widget: mix_part {mix_part} outside "
                        f"0..{n_parts - 1}"
                    )
                param = str(0x80 | mix_part)
            else:
                if operators and not 0 <= channel < len(operators):
                    raise GenError(
                        f"{w['type']} widget: channel {channel} outside "
                        f"0..{len(operators) - 1}"
                    )
                param = str(channel)
        elif w["type"] == "band":
            typ = "UI_BAND"
            kind = w.get("kind", "env")
            if kind not in ("env", "scope"):
                raise GenError(f"band widget: kind {kind!r} is not 'env' or 'scope'")
            # param = the graph kind (0 = A-ENV, 1 = scope)
            param = "0" if kind == "env" else "1"
        elif w["type"] == "subheader":
            typ = "UI_SUBHEADER"
            # param = the prefix mode (see subheader_mode)
            param = str(subheader_mode(w))
        elif w["type"] == "name":
            typ = "UI_NAME"
            # param = a part index, or n_parts for the multi-patch name
            # text = the label
            name_ix = w.get("name", 0)
            if not 0 <= name_ix <= n_parts:
                raise GenError(
                    f"name widget: index {name_ix} outside 0..{n_parts} "
                    "(the parts, then the multi-patch)"
                )
            param = str(name_ix)
        else:
            wparam = w.get("param")
            rest = op_rest(wparam) if wparam else None
            if rest is not None:
                if rest not in op_names:
                    op_names.append(rest)
                typ = "UI_OP_ROW"
                param = str(op_names.index(rest))
            elif wparam and w.get("part"):
                # a part-relative param (the GLO part pages): resolved through the
                # active part, so the param must be the unsuffixed (part-0) name.
                if wparam not in part_names:
                    part_names.append(wparam)
                typ = "UI_PART_ROW"
                param = str(part_names.index(wparam))
            else:
                raw_typ = _WIDGETS.get(w["type"])
                if raw_typ is None:
                    raise GenError(f"unknown widget type {w['type']!r}")
                typ = raw_typ
                param = param_sym(wparam) if wparam else "UI_NO_PARAM"
        text = cstr(w.get("text"))
        unit = cstr(w.get("unit"))
        fmt = cstr(w.get("fmt"))
        items = w.get("items", [])
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
    for context in contexts.values():
        for page in context.get("pages", []):
            for w in page.get("widgets", []):
                if w["type"] == "envelope":
                    for p in w.get("params", []):
                        rest = op_rest(p)
                        if rest is None:
                            raise GenError(
                                f"envelope param {p!r} is not operator-relative"
                            )
                        if rest not in env_names:
                            env_names.append(rest)
                        for op in operators:
                            param_id(f"{op}.{rest}")
                elif w["type"] == "genv":
                    group = tuple(w.get("params", []))
                    if len(group) != 7:
                        raise GenError(
                            f"genv widget needs exactly 7 params (got {len(group)})"
                        )
                    if group not in genv_groups:
                        genv_groups.append(group)
                    for p in group:
                        param_id(p)
                else:
                    wparam = w.get("param")
                    if wparam:
                        rest = op_rest(wparam)
                        if rest is not None:
                            for op in operators:
                                param_id(f"{op}.{rest}")
                        else:
                            param_id(wparam)
        for b in context.get("bindings", []):
            target = b.get("target")
            if target:
                param_id(target)
    for b in panel.get("global", []):
        target = b.get("target")
        if target:
            param_id(target)

    lines = [
        "/* SPDX-License-Identifier: GPL-3.0-only",
        " * Copyright (C) 2026 P1Onken (umetate) */",
        "/* GENERATED by umetate from panel.json, do not edit. */",
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

    def is_description(w: Widget) -> bool:
        """The first widget of a page is its *description* (drawn in the always-
        visible header) when it is a `subheader` or a two-line `label`."""
        return w["type"] == "subheader" or (
            w["type"] == "label" and w.get("span", 1) >= 2
        )

    widget_count = 0
    for ci, ctx in enumerate(ctx_names):
        pages = contexts[ctx].get("pages", [])
        page_decls: list[str] = []
        for pi, page in enumerate(pages):
            widgets = page.get("widgets", [])
            desc = ""
            mode = 0xFF
            shift = 0
            if widgets and is_description(widgets[0]):
                desc = widgets[0].get("text") or ""
                if widgets[0]["type"] == "subheader":
                    mode = subheader_mode(widgets[0])
                widgets = widgets[1:]
                shift = 1
            wname = f"W_{ci}_{pi}"
            lines.append(f"static const ui_widget {wname}[] = {{")
            lines.extend(widget_line(w, shift) for w in widgets)
            lines.append("};")
            widget_count += len(widgets)
            page_decls.append(
                f"    {{ {cstr(desc)}, {mode}, {wname}, "
                f"(uint8_t)(sizeof {wname} / sizeof {wname}[0]) }},"
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
            f'    {{ "{ctx}", PG_{ci}, {len(contexts[ctx].get("pages", []))}, '
            f"BIND_{ci}, {len(contexts[ctx].get('bindings', []))}, 0, 0 }},"
        )
    lines.append("};")
    lines.append("")

    home = str(ctx_ids[panel.get("home", "home")])
    n_params = (
        (max(ids.values()) + 1 if ids else 0) if param_ids is not None else len(params)
    )
    if n_params > 512:
        raise GenError(
            f"panel: {n_params} params exceed the UI kit's UI_PARAM_MAX (512)"
        )
    mute = panel.get("mute") or []
    # the mute/operator/envelope/part-relative tables are per-part (part-major), and
    # the runtime indexes them by ui_selected_part, so the editor and the mutes
    # follow the active part (§13.3 item 33). part 0 = the unsuffixed name, later
    # parts = `.pN`.
    mute_ids: list[str] = []
    for part in range(n_parts):
        for p in mute[:4]:
            mute_ids.append(str(part_entry(p, part)))
        mute_ids += ["0xFFFF"] * (4 - min(4, len(mute)))
    lines.append(
        f"static const uint16_t MUTE_TBL[{4 * n_parts}] = {{ {', '.join(mute_ids)} }};"
    )
    if operators and op_names:
        flat = [
            str(part_entry(f"{op}.{n}", part))
            for part in range(n_parts)
            for op in operators
            for n in op_names
        ]
        lines.append(
            f"static const uint16_t OP_PARAM[{len(flat)}] = {{ {', '.join(flat)} }};"
        )
        op_ptr = "OP_PARAM"
    else:
        op_ptr = "0"
    if operators and env_names:
        flat = [
            str(part_entry(f"{op}.{n}", part))
            for part in range(n_parts)
            for op in operators
            for n in env_names
        ]
        lines.append(
            f"static const uint16_t ENV_PARAM[{len(flat)}] = {{ {', '.join(flat)} }};"
        )
        env_ptr = "ENV_PARAM"
    else:
        env_ptr = "0"
    if genv_groups:
        flat = [str(param_id(p)) for group in genv_groups for p in group]
        lines.append(
            f"static const uint16_t GENV_PARAM[{len(flat)}] = {{ {', '.join(flat)} }};"
        )
        genv_ptr = "GENV_PARAM"
    else:
        genv_ptr = "0"
    if part_names:
        flat = [str(part_entry(n, part)) for part in range(n_parts) for n in part_names]
        lines.append(
            f"static const uint16_t PART_PARAM[{len(flat)}] = {{ {', '.join(flat)} }};"
        )
        part_ptr = "PART_PARAM"
    else:
        part_ptr = "0"
    # the per-param display scale: one ui_param_disp per param id (raw by default).
    # Ratio and semitone params also carry a sorted landmark table, and a quantized
    # param steps landmark-to-landmark, so the sparse ratio series is never
    # skipped (§6.11.4 L11).
    landmark_tables: dict[tuple[str, int, int], str] = {}

    def landmark_ref(display: str, lo: int, hi: int) -> tuple[str, str, str]:
        """The (quantize, count, pointer) fields for a display scale's landmarks."""
        if display == "ratio":
            vals = _ratio_landmarks(lo, hi)
        elif display == "semi":
            vals = _semi_landmarks(lo, hi)
        elif display == "semi_fine":
            vals = _semi_fine_landmarks(lo, hi)
        else:
            return "0", "0", "0"
        if not vals:
            return "0", "0", "0"
        if len(vals) > 255:
            raise GenError(f"panel: {len(vals)} landmarks exceed the uint8 lm_count")
        key = (display, lo, hi)
        name = landmark_tables.get(key)
        if name is None:
            name = f"LM_{len(landmark_tables)}"
            landmark_tables[key] = name
            lines.append(f"static const int32_t {name}[{len(vals)}] = {{")
            for i in range(0, len(vals), 12):
                chunk = ", ".join(str(v) for v in vals[i : i + 12])
                lines.append(f"    {chunk},")
            lines.append("};")
        return "1", str(len(vals)), name

    if param_meta is not None and n_params:
        disp_rows: list[str] = []
        for pid in range(n_params):
            m = param_meta.get(pid)
            if m is None:
                disp_rows.append("{ UI_DISP_RAW, 0, 0, 0, 0, 0, 0 }")
            else:
                display, lo, hi, curve = m
                if display not in _DISPLAY:
                    raise GenError(f"params: unknown display {display!r}")
                quantize, lm_count, lm_ptr = landmark_ref(display, lo, hi)
                disp_rows.append(
                    f"{{ {_DISPLAY[display]}, {'1' if curve == 'log' else '0'}, "
                    f"{lo}, {hi}, {quantize}, {lm_count}, {lm_ptr} }}"
                )
        lines.append(
            f"static const ui_param_disp DISP_TBL[{n_params}] = {{ "
            + ", ".join(disp_rows)
            + " };"
        )
        disp_ptr = "DISP_TBL"
    else:
        disp_ptr = "0"
    lines.append("")
    lines.append("static const ui_tables PANEL = {")
    alg_name = panel.get("alg")
    alg_id = str(param_id(alg_name)) if alg_name else "0xFFFF"
    n_part = str(panel.get("parts", 1))
    # the per-part param stride (the id gap `.p0` -> `.p1`): the header/ENC_ALGORITHM
    # resolve the algorithm through the active part when it is a per-part param.
    part_stride = 0
    if alg_name:
        p1 = ids.get(f"{alg_name}.p1")
        if p1 is not None:
            part_stride = p1 - ids[alg_name]
    lines.append(
        f'    "{name}", {home}, CTX, {len(ctx_names)}, GLOBAL_BIND, '
        f"{len(panel.get('global', []))}, MUTE_TBL, {op_ptr}, "
        f"{len(operators)}, {len(op_names)}, {env_ptr}, {part_ptr}, "
        f"{len(part_names)}, {disp_ptr}, "
        f"{alg_id}, {part_stride}, {n_part}, {n_params}, {widget_count}, "
        f"{genv_ptr}, {len(genv_groups)},"
    )
    lines.append(f"    {cstr(panel.get('legend'))},")
    lines.append("};")
    return "\n".join(lines) + "\n"


def _referenced_params(
    panel: PanelManifest, contexts: Mapping[str, Context]
) -> list[str]:
    """The distinct param names the panel references, in first-seen order."""
    refs: list[str] = []

    def note(pname: str) -> None:
        if pname not in refs:
            refs.append(pname)

    for ctx in contexts.values():
        for page in ctx.get("pages", []):
            for w in page.get("widgets", []):
                wparam = w.get("param")
                if wparam:
                    note(wparam)
        for b in ctx.get("bindings", []):
            target = b.get("target")
            if target:
                note(target)
    for b in panel.get("global", []):
        target = b.get("target")
        if target:
            note(target)
    return refs
