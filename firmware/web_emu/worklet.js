// SPDX-License-Identifier: GPL-3.0-only
// The AudioWorklet: instantiates the firmware wasm (the bytes come from the main
// thread — `fetch` is absent here), runs it pull-based (web_render advances the
// device one block at a time), and pushes the 240x240 screen + lights back.
const SYNTH = "fourop_fm";
const SCREEN = 240 * 240;

class SynthProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.e = null;
    this.outL = null;
    this.outR = null;
    this.fb = null;
    this.lastBlits = -1;
    this.port.onmessage = (e) => this.onmsg(e.data);
  }

  onmsg(m) {
    if (m.type === "load") {
      WebAssembly.instantiate(m.wasm, {}).then(({ instance }) => {
        this.e = instance.exports;
        const buf = this.e.memory.buffer;
        this.outL = new Float32Array(buf, this.e.web_out_l(), 1024);
        this.outR = new Float32Array(buf, this.e.web_out_r(), 1024);
        this.fb = new Uint16Array(buf, this.e.web_fb(), SCREEN);
        this.e.web_boot();
        this.port.postMessage({ type: "ready", synth: SYNTH });
      }).catch((err) =>
        this.port.postMessage({ type: "error", message: String(err && err.message || err) }));
      return;
    }
    if (!this.e) return;
    if (m.type === "buttons") this.e.web_buttons(m.mask);
    else if (m.type === "keys") this.e.web_keys(m.mask);
    else if (m.type === "enc") this.e.web_enc(m.role, m.n);
  }

  process(_inputs, outputs) {
    if (!this.e) return true;
    const n = outputs[0][0].length;
    this.e.web_render(n);
    const L = outputs[0][0], R = outputs[0][1];
    for (let i = 0; i < n; i++) {
      L[i] = this.outL[i];
      R[i] = this.outR[i];
    }
    const blits = this.e.web_blits();
    if (blits !== this.lastBlits) {
      this.lastBlits = blits;
      const fb = new Uint16Array(this.fb); // a copy, so the next draw may reuse this.fb
      this.port.postMessage(
        {
          type: "frame",
          fb: fb.buffer,
          buttons: this.e.web_lit_buttons(),
          keys: this.e.web_lit_keys(),
          dim: this.e.web_dim_keys(),
        },
        [fb.buffer],
      );
    }
    return true;
  }
}
registerProcessor("synth", SynthProcessor);
