# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate web-build` / `web-serve` (docs/roadmap.md §12.7.2, P3-5).

`web-build` emscripten-compiles the generated `dsp.c` to a standalone `dsp.wasm`
(no import section) + a minimal `index.html`/`app.js` harness (a manual browser
poke). `web-serve` is a loopback static server over that output. The real parity
lab (AudioWorklet + the automated host<->browser check) is P4-1.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import runner
from .generate import generate, generate_tables

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PATCH = _ROOT / "examples" / "pocket-drone" / "patch.json"
_OUT = _ROOT / "build" / "web"

# the §12.1 seam functions the harness calls (exported from dsp.wasm)
_SEAM_FUNCS = (
    "reset",
    "note_on",
    "note_off",
    "all_notes_off",
    "set_bend_q16",
    "lit",
    "quiet",
    "set_param",
    "get_param",
    "param_count",
    "render",
)

_INDEX_HTML = """\
<!doctype html>
<meta charset="utf-8">
<title>umetate dsp.wasm</title>
<button id="note">note on (A4)</button>
<button id="off">note off</button>
<pre id="log"></pre>
<script src="app.js"></script>
"""

_APP_JS = """\
(async () => {
  const log = (s) => { document.getElementById("log").textContent += s + "\\n"; };
  const bytes = await (await fetch("dsp.wasm")).arrayBuffer();
  const { instance } = await WebAssembly.instantiate(bytes, {});
  const e = instance.exports;
  const S = "__SYNTH__";
  const OUT = 1024 * 1024;  // a fixed scratch offset in the (fixed) wasm memory
  const peak = () => {
    e[S + "_dsp_render"](OUT, 256);
    const out = new Int32Array(e.memory.buffer, OUT, 512);
    let p = 0; for (const v of out) p = Math.max(p, Math.abs(v));
    return p;
  };
  document.getElementById("note").onclick = () => {
    e[S + "_dsp_note_on"](69, 100);
    log("note_on(69, 100) -> peak " + peak());
  };
  document.getElementById("off").onclick = () => {
    e[S + "_dsp_all_notes_off"]();
    log("all_notes_off -> energy " + peak());
  };
  e[S + "_dsp_reset"]();
  log("ready: " + S + " (dsp exports: " +
      Object.keys(e).filter((k) => k.includes("_dsp_")).join(", ") + ")");
})();
"""


def wasm_import_count(data: bytes) -> int:
    """The number of imported names of a .wasm module (0 = no import section)."""

    def uleb(i: int) -> tuple[int, int]:
        result = 0
        shift = 0
        while True:
            byte = data[i]
            i += 1
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return result, i
            shift += 7

    i = 8  # skip the 8-byte header
    while i < len(data):
        sec_id, i = uleb(i)
        size, i = uleb(i)
        if sec_id == 2:  # the import section
            return uleb(i)[0]
        i += size
    return 0


def _emcc_args(name: str, host: bool) -> list[str]:
    """The emcc command for a standalone, no-import dsp.wasm."""
    web = str(_OUT) if host else "/work/build/web"
    hal = str(_ROOT / "firmware" / "hal") if host else "/work/firmware/hal"
    gen = str(_ROOT / "firmware" / "gen") if host else "/work/firmware/gen"
    exports = json.dumps([f"_{name}_dsp_{s}" for s in _SEAM_FUNCS])
    return [
        "emcc",
        "-O2",
        "-std=c11",
        "-s",
        "STANDALONE_WASM=1",
        "-s",
        f"EXPORTED_FUNCTIONS={exports}",
        "-Wl,--no-entry",
        "-I",
        hal,
        "-I",
        gen,
        "-I",
        web,
        f"{web}/dsp.c",
        f"{web}/tables.c",
        "-o",
        f"{web}/dsp.wasm",
    ]


def build(patch: Mapping[str, Any], out: Path, name: str) -> int:
    """Generate + emscripten-compile `dsp.c` -> `dsp.wasm`, write the harness.

    Returns 0 on success (dsp.wasm is standalone, no import section).
    """
    out.mkdir(parents=True, exist_ok=True)
    (out / "dsp.c").write_text(generate(patch))
    tables_h, tables_c = generate_tables(patch)
    (out / "tables.h").write_text(tables_h)
    (out / "tables.c").write_text(tables_c)
    (out / "index.html").write_text(_INDEX_HTML)
    (out / "app.js").write_text(_APP_JS.replace("__SYNTH__", name))

    if runner.probe().docker:
        rc = runner.run(_emcc_args(name, host=False), cwd="/work")
    elif shutil.which("emcc"):
        rc = subprocess.run(_emcc_args(name, host=True)).returncode
    else:
        print("web-build: blocked — emcc not found (`umetate setup`)", file=sys.stderr)
        return 1

    wasm = out / "dsp.wasm"
    if rc != 0 or not wasm.is_file():
        return 1
    imports = wasm_import_count(wasm.read_bytes())
    if imports:
        print(
            f"web-build: dsp.wasm imports {imports} names (want a standalone module)",
            file=sys.stderr,
        )
        return 1
    print(f"web-build: {wasm} ({wasm.stat().st_size} bytes, no import section)")
    return 0


def build_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate web-build", description=__doc__)
    parser.add_argument(
        "--patch",
        type=Path,
        default=_DEFAULT_PATCH,
        help="a patch.json (default: examples/pocket-drone)",
    )
    parser.add_argument("--out", type=Path, default=_OUT, help="output directory")
    args = parser.parse_args(argv)

    if not args.patch.is_file():
        print(f"web-build: {args.patch} not found", file=sys.stderr)
        return 1
    try:
        patch = json.loads(args.patch.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"web-build: cannot read {args.patch}: {exc}", file=sys.stderr)
        return 1

    name = str(patch["name"]).replace("-", "_").replace(".", "_")
    print(f"web-build: {name} -> {args.out}")
    return build(patch, args.out, name)


def serve_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate web-serve", description=__doc__)
    parser.add_argument("--dir", type=Path, default=_OUT, help="the web-build output")
    parser.add_argument("--port", type=int, default=8000, help="loopback port")
    args = parser.parse_args(argv)

    if not (args.dir / "index.html").is_file():
        print(
            "web-serve: nothing built — run `umetate web-build` first",
            file=sys.stderr,
        )
        return 1

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(args.dir)
    )
    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"web-serve: http://127.0.0.1:{args.port}/  (Ctrl+C to stop)")
        with contextlib.suppress(KeyboardInterrupt):
            httpd.serve_forever()
    return 0
