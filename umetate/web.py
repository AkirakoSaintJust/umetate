# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""`umetate web-build` / `web-serve` (docs/roadmap.md §12.7.2, P4-1).

`web-build` emscripten-compiles the generated `dsp.c` to a standalone `dsp.wasm`
(no import section) + an AudioWorklet harness (`index.html`/`main.js`/`worklet.js`)
with a versioned message protocol and gesture-gated start. `web-serve` is a loopback
static server. `check_parity` proves the browser (wasm, via node) output matches the
host (gcc) output exactly.
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
from pathlib import Path

from . import runner
from ._schema import Patch, as_patch
from .generate import generate, generate_tables

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATCH = _ROOT / "examples" / "pocket-drone" / "patch.json"
OUT = _ROOT / "build" / "web"

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
<title>umetate dsp.wasm — parity lab</title>
<style>
  body { background: #101410; color: #9f9; font: 14px monospace; }
  button { margin: 2px; padding: 4px 10px; font: 13px monospace; }
  #keys button { width: 44px; height: 96px; }
</style>
<button id="start">start</button>
<button id="off" disabled>all notes off</button>
<pre id="log"></pre>
<div id="keys"></div>
<script src="main.js"></script>
"""

# the main thread: gesture-gated AudioContext, the versioned message protocol.
_MAIN_JS = """\
const log = (s) => { document.getElementById("log").textContent += s + "\\n"; };
let synth = null;

document.getElementById("start").onclick = async () => {
  try {
    const ctx = new AudioContext({ sampleRate: 44100 });  // fixed 44.1 kHz
    await ctx.audioWorklet.addModule("worklet.js");
    synth = new AudioWorkletNode(ctx, "synth",
        { numberOfOutputs: 1, outputChannelCount: [2] });
    synth.port.onmessage = (e) => log(String(e.data));
    synth.connect(ctx.destination);
    await ctx.resume();
    // fetch the wasm here, on the main thread (`fetch` is absent from the
    // AudioWorkletGlobalScope), and transfer the bytes into the worklet.
    const bytes = await (await fetch("/dsp.wasm")).arrayBuffer();
    synth.port.postMessage({ v: 1, op: "init", wasm: bytes }, [bytes]);
    document.getElementById("off").disabled = false;
    log("started (44.1 kHz)");
  } catch (err) {
    log("start error: " + (err && err.message ? err.message : err));
  }
};

const send = (op, extra = {}) =>
    synth && synth.port.postMessage({ v: 1, op, ...extra });
document.getElementById("off").onclick = () => send("all_off");

// a one-octave keyboard (C4..B4): mousedown = note on, mouseup/leave = note off.
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const keys = document.getElementById("keys");
for (let i = 0; i < 12; i++) {
  const note = 60 + i;
  const b = document.createElement("button");
  b.textContent = NOTE_NAMES[i] + "4";
  const off = () => send("note_off", { note });
  b.onmousedown = () => send("note_on", { note, vel: 100 });
  b.onmouseup = b.onmouseleave = off;
  keys.appendChild(b);
}
"""

# the AudioWorklet: instantiates the wasm (bytes come from the main thread, since
# `fetch` is absent here), block (128 -> 256) conversion, the protocol.
_WORKLET_JS = """\
const SYNTH = "__SYNTH__";
const OUT = 1024 * 1024;  // a fixed scratch offset in the (fixed) wasm memory
const BLOCK = 256;        // the DSP renders 256-frame blocks

class SynthProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.e = null;
    this.out = null;
    this.block = new Float32Array(BLOCK * 2);
    this.pos = BLOCK;  // render on the first process() call
    this.port.onmessage = (e) => this.onmsg(e.data);
  }

  onmsg(m) {
    if (m.v !== 1) return;  // the versioned protocol: v1 only
    if (m.op === "init") {
      WebAssembly.instantiate(m.wasm, {}).then(({ instance }) => {
        this.e = instance.exports;
        this.out = new Int32Array(this.e.memory.buffer, OUT, BLOCK * 2);
        this.e[SYNTH + "_dsp_reset"]();
        this.port.postMessage("ready: " + SYNTH);
      }).catch((err) =>
        this.port.postMessage("error: " + (err && err.message ? err.message : err)));
      return;
    }
    if (!this.e) return;
    const e = this.e;
    switch (m.op) {
      case "note_on": e[SYNTH + "_dsp_note_on"](m.note, m.vel); break;
      case "note_off": e[SYNTH + "_dsp_note_off"](m.note); break;
      case "all_off": e[SYNTH + "_dsp_all_notes_off"](); break;
      case "param": e[SYNTH + "_dsp_set_param"](m.id, m.value); break;
      case "bend": e[SYNTH + "_dsp_set_bend_q16"](m.value); break;
      case "reset": e[SYNTH + "_dsp_reset"](); break;
    }
  }

  process(_inputs, outputs) {
    if (!this.e) return true;
    const L = outputs[0][0];
    const R = outputs[0][1];
    for (let i = 0; i < L.length; i++) {
      if (this.pos >= BLOCK) {
        this.e[SYNTH + "_dsp_render"](OUT, BLOCK);
        for (let j = 0; j < BLOCK; j++) {
          this.block[j * 2] = this.out[j * 2] / 32768;      // Q15 -> float
          this.block[j * 2 + 1] = this.out[j * 2 + 1] / 32768;
        }
        this.pos = 0;
      }
      L[i] = this.block[this.pos * 2];
      R[i] = this.block[this.pos * 2 + 1];
      this.pos++;
    }
    return true;
  }
}
registerProcessor("synth", SynthProcessor);
"""

# the parity harnesses: the same render script, host (gcc) and wasm (node), to a file.
_HOST_HARNESS = """\
#include <stdio.h>
#include <stdint.h>
void __NAME___dsp_reset(void);
void __NAME___dsp_note_on(uint32_t note, uint32_t velocity);
void __NAME___dsp_render(int32_t *out, uint32_t frames);
int main(void) {
    static int32_t out[512];
    FILE *f = fopen("host.out", "wb");
    if (!f) return 1;
    __NAME___dsp_reset();
    __NAME___dsp_note_on(69, 100);
    __NAME___dsp_render(out, 256);
    fwrite(out, sizeof(out[0]), 512, f);
    fclose(f);
    return 0;
}
"""

_NODE_HARNESS = """\
const fs = require("fs");
WebAssembly.instantiate(fs.readFileSync("dsp.wasm"), {}).then(({ instance }) => {
  const e = instance.exports;
  const p = 1024 * 1024;
  e.__NAME___dsp_reset();
  e.__NAME___dsp_note_on(69, 100);
  e.__NAME___dsp_render(p, 256);
  const out = new Int32Array(e.memory.buffer, p, 512);
  fs.writeFileSync("node.out", Buffer.from(out.buffer, out.byteOffset, out.byteLength));
});
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


def _container_path(path: Path) -> str:
    """A host path under the repo root -> its container path (repo mounted at /work)."""
    return "/work/" + path.resolve().relative_to(_ROOT.resolve()).as_posix()


class _ReusableTCPServer(socketserver.ThreadingTCPServer):
    """A ThreadingTCPServer that reuses the port (Windows TIME_WAIT) + daemon
    threads."""

    allow_reuse_address = True
    daemon_threads = True


def _emcc_args(name: str, host: bool, out: Path) -> list[str]:
    """The emcc command for a standalone, no-import dsp.wasm."""
    web = str(out) if host else _container_path(out)
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


def build(patch: Patch, out: Path, name: str) -> int:
    """Generate + emscripten-compile `dsp.c` -> `dsp.wasm`, write the harness.

    Returns 0 on success (dsp.wasm is standalone, no import section).
    """
    out.mkdir(parents=True, exist_ok=True)
    (out / "dsp.c").write_text(generate(patch))
    tables_h, tables_c = generate_tables(patch)
    (out / "tables.h").write_text(tables_h)
    (out / "tables.c").write_text(tables_c)
    (out / "index.html").write_text(_INDEX_HTML)
    (out / "main.js").write_text(_MAIN_JS)
    (out / "worklet.js").write_text(_WORKLET_JS.replace("__SYNTH__", name))

    if runner.probe().docker:
        rc = runner.run(_emcc_args(name, host=False, out=out), cwd="/work")
    elif shutil.which("emcc"):
        rc = subprocess.run(_emcc_args(name, host=True, out=out)).returncode
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


def check_parity(out: Path, name: str) -> tuple[bool, str]:
    """Run the same render script on host (gcc) + wasm (node) and compare exactly."""
    (out / "harness.c").write_text(_HOST_HARNESS.replace("__NAME__", name))
    (out / "render.js").write_text(_NODE_HARNESS.replace("__NAME__", name))

    if shutil.which("cc") is not None:
        cc = [
            "cc",
            "-std=c11",
            "-I",
            str(_ROOT / "firmware" / "hal"),
            "-I",
            str(_ROOT / "firmware" / "gen"),
            "-I",
            str(out),
            "-o",
            str(out / "harness"),
            str(out / "dsp.c"),
            str(out / "tables.c"),
            str(out / "harness.c"),
        ]
        if subprocess.run(cc, cwd=out).returncode != 0:
            return False, "the host harness did not compile"
        if subprocess.run([str(out / "harness")], cwd=out).returncode != 0:
            return False, "the host harness failed"
        if subprocess.run(["node", "render.js"], cwd=out).returncode != 0:
            return False, "the node harness failed"
    elif runner.probe().docker:
        web = _container_path(out)
        cc = [
            "cc",
            "-std=c11",
            "-I",
            "/work/firmware/hal",
            "-I",
            "/work/firmware/gen",
            "-I",
            web,
            "-o",
            f"{web}/harness",
            f"{web}/dsp.c",
            f"{web}/tables.c",
            f"{web}/harness.c",
        ]
        if runner.run(cc, cwd="/work") != 0:
            return False, "the host harness did not compile"
        if runner.run([f"{web}/harness"], cwd=web) != 0:
            return False, "the host harness failed"
        if runner.run(["node", "render.js"], cwd=web) != 0:
            return False, "the node harness failed"
    else:
        return False, "no C compiler or docker"

    host_bytes = (out / "host.out").read_bytes()
    node_bytes = (out / "node.out").read_bytes()
    if host_bytes != node_bytes:
        return False, "host and wasm outputs differ"
    return True, "host == wasm (exact, 512 int32 samples)"


def build_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate web-build", description=__doc__)
    parser.add_argument(
        "--patch",
        type=Path,
        default=DEFAULT_PATCH,
        help="a patch.json (default: examples/pocket-drone)",
    )
    parser.add_argument("--out", type=Path, default=OUT, help="output directory")
    args = parser.parse_args(argv)

    patch_path: Path = args.patch
    out: Path = args.out
    if not patch_path.is_file():
        print(f"web-build: {patch_path} not found", file=sys.stderr)
        return 1
    try:
        patch = as_patch(json.loads(patch_path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"web-build: cannot read {patch_path}: {exc}", file=sys.stderr)
        return 1

    name = patch["name"].replace("-", "_").replace(".", "_")
    print(f"web-build: {name} -> {out}")
    return build(patch, out, name)


def serve_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umetate web-serve", description=__doc__)
    parser.add_argument("--dir", type=Path, default=OUT, help="the web-build output")
    parser.add_argument("--port", type=int, default=8000, help="loopback port")
    args = parser.parse_args(argv)

    directory: Path = args.dir
    port: int = args.port
    if not (directory / "index.html").is_file():
        print(
            "web-serve: nothing built — run `umetate web-build` first",
            file=sys.stderr,
        )
        return 1

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(directory)
    )
    try:
        with _ReusableTCPServer(("127.0.0.1", port), handler) as httpd:
            print(f"web-serve: http://127.0.0.1:{port}/  (Ctrl+C to stop)")
            with contextlib.suppress(KeyboardInterrupt):
                httpd.serve_forever()
    except OSError as exc:
        print(
            f"web-serve: cannot bind 127.0.0.1:{port} ({exc}) — is another "
            "web-serve running?",
            file=sys.stderr,
        )
        return 1
    return 0
