# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The CLI's own contract tests (docs/roadmap.md §12.8).

Run: python3 -m umetate.test_cli
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import umetate.cli as cli
from umetate import __version__
from umetate._schema import EvidenceMatrix

_Tests = list[tuple[str, Callable[[], None]]]


def _no_import_side_effects() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        importlib.reload(cli)
    assert buf.getvalue() == "", "importing umetate.cli printed output"


def _help_lists_all() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(["--help"])
    assert rc == 0
    out = buf.getvalue()
    for name in cli.COMMANDS:
        assert name in out, f"--help is missing {name!r}"


def _version_command() -> None:
    from . import version

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = version.main([])
    assert rc == 0
    assert buf.getvalue().strip() == __version__


def _status_parses() -> None:
    from . import status

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = status.main([])
    assert rc == 0
    assert "Phase 0" in buf.getvalue() and "Phase 2" in buf.getvalue()


def _quick_check_json() -> None:
    from . import quick_check

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = quick_check.main(["--json"])
    assert rc in (0, 1)
    data = json.loads(buf.getvalue())
    assert "layers" in data
    for layer in data["layers"]:
        assert set(layer) == {"layer", "status", "detail"}


def _lib_lists() -> None:
    from . import lib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = lib.main(["list"])
    assert rc == 0
    out = buf.getvalue()
    assert "phasor" in out and "type-p-fm1" in out


def _scaffold_builds() -> None:
    from . import scaffold

    with tempfile.TemporaryDirectory() as tmp:
        rc = scaffold.main(["patch", "--name", "t", "--out", tmp])
        assert rc == 0
        assert (Path(tmp) / "patch.json").exists()
        assert (Path(tmp) / "panel.json").exists()


def _scaffold_synth() -> None:
    from . import scaffold

    with tempfile.TemporaryDirectory() as tmp:
        rc = scaffold.main(["synth", "--name", "my-synth", "--out", tmp])
        assert rc == 0
        assert (Path(tmp) / "patch.json").exists()
        assert (Path(tmp) / "panel.json").exists()
        app = (Path(tmp) / "app.c").read_text(encoding="utf-8")
        assert "my_synth_glue_note_on" in app  # the name -> its C identifier
        assert "app_audio" not in app  # the transport is generated glue.h
        assert "synth_midi_ctx" in app  # the framework service contexts are wired


def _lint_catches_violation() -> None:
    from . import lint

    violation = lint.FW / "src" / "_viol.c"
    violation.write_text(
        "void f(void){ int b[MAXP]; b[MAXP] = 1; }\n", encoding="utf-8"
    )
    try:
        rc = lint.main(["--c"])
    finally:
        violation.unlink(missing_ok=True)
    assert rc == 1, "a MAXP-bounds violation must fail lint --c"


def _setup_dry_run_plans() -> None:
    from . import setup

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = setup.main(["--dry-run"])
    assert rc == 0
    out = buf.getvalue()
    assert "extract to /opt/jieli/toolchain" in out
    assert "verify SDK asset" in out
    assert "cargo build --release -p fm1-emu -p fm1-live" in out

    data_buf = io.StringIO()
    with contextlib.redirect_stdout(data_buf):
        assert setup.main(["--dry-run", "--json"]) == 0
    assert "steps" in json.loads(data_buf.getvalue())


def _emu_paths() -> None:
    from . import _emu

    assert _emu.EMU_BIN.name.startswith("fm1-emu")
    assert _emu.LIVE_BIN.name.startswith("fm1-live")
    if sys.platform == "win32":
        assert _emu.EMU_BIN.suffix == ".exe"
    assert isinstance(_emu.emulator_built(), bool)


def _evidence_validates() -> None:
    from . import evidence

    good: EvidenceMatrix = {
        "layers": [
            {"layer": "source", "status": "pass", "detail": "x"},
            {"layer": "device", "status": "blocked", "detail": "x"},
        ]
    }
    assert evidence.validate(good) == []
    assert evidence.validate({"layers": [{"layer": "wobble", "status": "pass"}]})
    dup: EvidenceMatrix = {
        "layers": [
            {"layer": "source", "status": "pass", "detail": "x"},
            {"layer": "source", "status": "blocked", "detail": "x"},
        ]
    }
    assert evidence.validate(dup)


def _wasm_import_parser() -> None:
    from . import web

    header = b"\x00\x61\x73\x6d\x01\x00\x00\x00"
    assert web.wasm_import_count(header) == 0  # no import section
    assert web.wasm_import_count(header + b"\x02\x01\x00") == 0  # empty import section
    one_import = header + b"\x02\x07\x01\x01\x6d\x01\x66\x00\x00"
    assert web.wasm_import_count(one_import) == 1


def _synthetic_package(
    fm1: ModuleType, product: str = "FM-1_900", size: int = 0x2000
) -> bytes:
    """A valid 20-block .fwsc (as fm1_install's own test builds it)."""
    img = bytearray((i * 7) & 0xFF for i in range(size))
    img[0x1800:0x1810] = fm1.LOADER_MARK
    data = bytes(img[0x400:])
    entry = bytearray(0x50)
    entry[0:16] = (
        (0).to_bytes(2, "little")
        + (0).to_bytes(2, "little")
        + fm1._crc16(data).to_bytes(2, "little")
        + bytes(2)
        + (0x400).to_bytes(4, "little")
        + len(data).to_bytes(4, "little")
    )
    entry[0x40:0x49] = b"flash.bin"
    lst = fm1._dec(bytes(entry))
    hdr = bytearray(0x40)
    hdr[4:8] = size.to_bytes(4, "little")
    hdr[8:10] = (1).to_bytes(2, "little")
    hdr[2:4] = fm1._crc16(lst).to_bytes(2, "little")
    hdr[0:2] = fm1._crc16(bytes(hdr[2:0x40])).to_bytes(2, "little")
    img[0:0x40] = fm1._dec(bytes(hdr))
    img[0x40:0x90] = lst
    raw = bytearray()
    for i in range(20):
        m = (ord(product[i]) + i + 1) & 0xFF if i < len(product) else 0x7D
        raw += img[i * fm1.KEEP : (i + 1) * fm1.KEEP] + bytes([m])
    raw += img[20 * fm1.KEEP :]
    return bytes(raw)


class _WrongBackend:
    """A MIDI backend whose one device answers with a wrong identity."""

    def __init__(self, fm1: ModuleType, identity: str) -> None:
        self.fm1 = fm1
        self.identity = identity.encode()

    def input_names(self) -> list[str]:
        return ["FM-1"]

    output_names = input_names

    def open(self, in_name: str, out_name: str) -> _WrongLink:
        return _WrongLink(self)


class _WrongLink:
    def __init__(self, backend: _WrongBackend) -> None:
        self._b = backend

    def send(self, pkt: bytes) -> bool:
        return True

    def read(self, timeout: float) -> bytes:
        t = self._b.identity
        body = bytes([0, 0x59, 0x11, 0, 0, 0]) + t + bytes(28 - len(t))
        return b"\xf0" + bytes(self._b.fm1.pack7(body)) + b"\xf7"

    def drain(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def lost(self) -> bool:
        return False


def _flash_gates() -> None:
    from . import flash as F

    # no --device: refused, nothing sent
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = F.flash(["x.fwsc"])
    assert rc == 1 and "--device" in buf.getvalue()

    # a missing package
    assert F.flash(["missing.fwsc", "--device", "--yes"]) == 2

    # a damaged/garbage package
    from ._installer import load_installer_module

    fm1 = load_installer_module()
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.fwsc"
        bad.write_bytes(b"\x00" * 100)
        assert F.flash([str(bad), "--device", "--yes"]) == 2

        # wrong model -> exit 6 (the fake-device seam, delegated)
        ok = Path(tmp) / "ok.fwsc"
        ok.write_bytes(_synthetic_package(fm1))
        backend = _WrongBackend(fm1, "SMK-37 Pro_016")
        rc = F.flash([str(ok), "--device", "--yes"], backend=backend, out=io.StringIO())
        assert rc == 6


def _flash_confirms() -> None:
    """The interactive path: a custom `ask` that says no cancels (no crash)."""
    from . import flash as F
    from ._installer import load_installer_module

    fm1 = load_installer_module()
    with tempfile.TemporaryDirectory() as tmp:
        ok = Path(tmp) / "ok.fwsc"
        ok.write_bytes(_synthetic_package(fm1))
        # a matching identity: find() succeeds, then the confirmation is asked
        backend = _WrongBackend(fm1, "FM-1_900")
        rc = F.flash(
            [str(ok), "--device"],
            backend=backend,
            out=io.StringIO(),
            ask=lambda _p: False,
        )
        assert rc == 1  # cancelled (the ask was threaded, not None)


def _debrick_routes() -> None:
    from . import debrick

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = debrick.main([])
    out = buf.getvalue()
    assert rc == 0 and "app-rescue" in out and "mask-rom" in out

    with contextlib.redirect_stderr(io.StringIO()):
        rc = debrick.main(["--route", "mask-rom"])
    assert rc == 1  # blocked


def _skill_check() -> None:
    from . import _skill

    assert _skill.check() == [], (
        "the skill bundles drifted; run `python -m umetate._skill generate`"
    )


def _links_check() -> None:
    from . import _links

    assert _links.check() == [], "the canonical docs have dead cross-references"


def _records_roundtrip() -> None:
    """The preset record formats pack/unpack + CRCs round-trip (§6.11.4 layouts)."""
    from . import _records

    assert _records.crc32(b"123456789") == 0xCBF43926, "crc32 mismatch"
    assert _records.crc16(b"123456789") == 0x29B1, "crc16-ccitt mismatch"

    part: _records.PartPatch = {"name": "EPiano", "params": [100, -5, 65536, 0]}
    raw = _records.pack_part_patch(part, 4)
    part_back = _records.unpack_part_patch(raw, 4)
    assert part_back is not None and part_back == part, "part patch round-trip"
    corrupt = bytearray(raw)
    corrupt[2] ^= 0x01
    assert _records.unpack_part_patch(bytes(corrupt), 4) is None, (
        "corruption undetected"
    )
    assert _records.unpack_part_patch(raw[:-1], 4) is None, "truncation undetected"
    assert (
        _records.unpack_part_patch(b"\xff" * _records.part_patch_size(4), 4) is None
    ), "empty slot not None"

    multi: _records.MultiPatch = {
        "name": "Layers",
        "part_slot": [0, 1],
        "level": [99, 99],
        "delay": [0, 40],
        "channel": [0, 1],
        "low": [0, 60],
        "high": [127, 127],
    }
    raw = _records.pack_multi_patch(multi, 2)
    multi_back = _records.unpack_multi_patch(raw, 2)
    assert multi_back is not None and multi_back == multi, "multi patch round-trip"

    settings: _records.Settings = {"base_channel": -1, "master_tune": 12}
    raw = _records.pack_settings(settings)
    settings_back = _records.unpack_settings(raw)
    assert settings_back is not None and settings_back == settings, (
        "settings round-trip"
    )


def _sysex_roundtrip() -> None:
    """The SysEx envelope frames + CRC-16 + 7-bit packing round-trip (§6.11.4)."""
    from . import _records, _sysex

    # 7-bit packing round-trips; every packed byte stays a MIDI data byte
    for n in (0, 1, 6, 7, 8, 100):
        data = bytes((i * 37 + 11) % 256 for i in range(n))
        packed = _sysex.pack7(data)
        assert all(b <= 0x7F for b in packed), "packed byte > 0x7F"
        assert _sysex.unpack7(packed, n) == data, f"pack7 round-trip n={n}"

    # frame round-trip + parse
    payload = _records.pack_part_patch({"name": "EPiano", "params": [1, -2, 3, -4]}, 4)
    frame = _sysex.encode(0x42, _sysex.CMD_PART_DUMP, payload)
    got = _sysex.decode(frame)
    assert got is not None and got == (
        0x42,
        _sysex.CMD_PART_DUMP,
        _sysex.VERSION,
        _sysex.pack7(payload),
    ), "frame round-trip"
    assert _sysex.unpack7(got[3], len(payload)) == payload, "payload unpack"

    # CRC + framing failures are rejected
    bad = bytearray(frame)
    bad[8] ^= 0x01
    assert _sysex.decode(bytes(bad)) is None, "CRC failure undetected"
    assert _sysex.decode(frame[:-1]) is None, "missing F7 undetected"
    assert _sysex.decode(b"\x00" + frame[1:]) is None, "bad F0 undetected"

    # the response bit echoes the command; unknown-cmd classification
    assert _sysex.known(_sysex.CMD_IDENTITY | _sysex.RESPONSE), "response cmd"
    assert not _sysex.known(0x7F), "unknown cmd classified as known"


def _bank_roundtrip() -> None:
    """The preset bank <-> .syx export/import round-trip (§6.11.4)."""
    from . import _presets, _records
    from ._schema import as_patch
    from .generate import generate_sysex_layout

    patch = as_patch(
        {
            "name": "t",
            "voices": 2,
            "voice": {
                "nodes": [
                    {"id": "ph", "type": "phasor"},
                    {"id": "osc", "type": "osc"},
                ],
                "wires": [{"from": "ph.phase", "to": "osc.phase"}],
                "voice_out": "osc.audio",
            },
            "global": {"nodes": [], "wires": []},
        }
    )
    layout = generate_sysex_layout(patch)

    bank: _presets.Bank = {
        "part_patches": [None] * _records.PART_SLOTS,
        "multi_patches": [None] * _records.MULTI_SLOTS,
    }
    bank["part_patches"][0] = {"name": "EPiano", "params": [100, 0, -5]}
    bank["part_patches"][_records.PART_SLOTS - 1] = {
        "name": "Glass",
        "params": [0, 0, 65536],
    }
    bank["multi_patches"][3] = {
        "name": "Layers",
        "part_slot": [0],
        "level": [99],
        "delay": [40],
        "channel": [0],
        "low": [0],
        "high": [127],
    }

    stream = _presets.export_bank(layout, bank, 0x42)
    back = _presets.import_bank(stream, layout, 0x42)
    assert back is not None and back == bank, "bank round-trip"

    bad = bytearray(stream)
    bad[len(bad) // 2] ^= 0x01
    assert _presets.import_bank(bytes(bad), layout, 0x42) is None, (
        "corruption undetected"
    )
    assert _presets.import_bank(stream[:-1], layout, 0x42) is None, (
        "truncation undetected"
    )
    assert _presets.import_bank(stream, layout, 0x41) is None, "wrong model undetected"


def _preset_export_import() -> None:
    """`umetate preset export` -> `import` round-trips a bank through a .syx file."""
    import json

    from . import _presets, _records

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "patch.json").write_text(
            json.dumps(
                {
                    "name": "t",
                    "voices": 2,
                    "voice": {
                        "nodes": [
                            {"id": "ph", "type": "phasor"},
                            {"id": "osc", "type": "osc"},
                        ],
                        "wires": [{"from": "ph.phase", "to": "osc.phase"}],
                        "voice_out": "osc.audio",
                    },
                    "global": {"nodes": [], "wires": []},
                }
            ),
            encoding="utf-8",
        )
        bank: _presets.Bank = {
            "part_patches": [None] * _records.PART_SLOTS,
            "multi_patches": [None] * _records.MULTI_SLOTS,
        }
        bank["part_patches"][1] = {"name": "EPiano", "params": [100, 0, -5]}
        (d / "bank.json").write_text(json.dumps(bank), encoding="utf-8")

        rc = cli.main(
            [
                "preset",
                "export",
                str(d / "patch.json"),
                "--bank",
                str(d / "bank.json"),
                "--model",
                "0x42",
                "--out",
                str(d / "bank.syx"),
            ]
        )
        assert rc == 0, "export failed"
        assert (d / "bank.syx").exists() and (d / "bank.syx").stat().st_size > 0

        rc = cli.main(
            [
                "preset",
                "import",
                str(d / "patch.json"),
                "--from",
                str(d / "bank.syx"),
                "--model",
                "0x42",
                "--out",
                str(d / "bank2.json"),
            ]
        )
        assert rc == 0, "import failed"
        back = json.loads((d / "bank2.json").read_text(encoding="utf-8"))
        assert back == bank, "bank round-trip mismatch"

        rc = cli.main(
            [
                "preset",
                "import",
                str(d / "patch.json"),
                "--from",
                str(d / "bank.syx"),
                "--model",
                "0x41",
                "--out",
                str(d / "bank3.json"),
            ]
        )
        assert rc == 1, "wrong-model import not rejected"


def _preset_c_parity() -> None:
    """The C preset store's record bytes equal `_records.pack_*` (parity)."""
    import subprocess

    from . import _records

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(root / "firmware" / "src"),
                "-o",
                str(d / "t"),
                str(root / "firmware" / "tests" / "presets_test.c"),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"presets_test.c does not compile: {proc.stderr}"
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        assert run.returncode == 0, f"presets_test.c failed: {run.stdout}"

        hexes: dict[str, str] = {}
        for line in run.stdout.splitlines():
            tag, sep, value = line.partition(":")
            if sep and tag.strip() in ("part-hex", "multi-hex", "settings-hex"):
                hexes[tag.strip()] = value.strip()

        assert (
            hexes.get("part-hex")
            == _records.pack_part_patch(
                {"name": "EPiano", "params": [100, -5, 65536, 0]}, 4
            ).hex()
        ), "part record parity"
        assert (
            hexes.get("multi-hex")
            == _records.pack_multi_patch(
                {
                    "name": "Layers",
                    "part_slot": [0, 1],
                    "level": [99, 99],
                    "delay": [0, 40],
                    "channel": [0, 1],
                    "low": [0, 60],
                    "high": [127, 127],
                },
                2,
            ).hex()
        ), "multi record parity"
        assert (
            hexes.get("settings-hex")
            == _records.pack_settings({"base_channel": -1, "master_tune": 12}).hex()
        ), "settings record parity"


def _sysex_c_parity() -> None:
    """The C SysEx handler's responses byte-match `_sysex.encode` (parity)."""
    import subprocess

    from . import _records, _sysex

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        proc = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(root / "firmware" / "src"),
                "-o",
                str(d / "t"),
                str(root / "firmware" / "tests" / "sysex_test.c"),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"sysex_test.c does not compile: {proc.stderr}"
        run = subprocess.run([str(d / "t")], capture_output=True, text=True)
        assert run.returncode == 0, f"sysex_test.c failed: {run.stdout}"

        hexes: dict[str, str] = {}
        for line in run.stdout.splitlines():
            tag, sep, value = line.partition(":")
            if sep and tag.strip() in ("identity-hex", "partread-hex"):
                hexes[tag.strip()] = value.strip()

        assert (
            hexes.get("identity-hex")
            == _sysex.encode(
                0x42,
                _sysex.CMD_IDENTITY | _sysex.RESPONSE,
                bytes([0x42, 1, 4, 0, 2]),
            ).hex()
        ), "identity response parity"
        assert (
            hexes.get("partread-hex")
            == _sysex.encode(
                0x42,
                _sysex.CMD_PART_DUMP | _sysex.RESPONSE,
                bytes([3])
                + _records.pack_part_patch(
                    {"name": "Slot3", "params": [7, 8, 9, 10]}, 4
                ),
            ).hex()
        ), "part-patch read parity"


def _budget_measures() -> None:
    """`umetate budget` measures the host polyphony scaling (a measured claim)."""
    import json

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "patch.json").write_text(
            json.dumps(
                {
                    "name": "t",
                    "voices": 8,
                    "voice": {
                        "nodes": [
                            {"id": "ph", "type": "phasor"},
                            {"id": "osc", "type": "osc"},
                            {"id": "env", "type": "env"},
                            {"id": "vca", "type": "vca"},
                        ],
                        "wires": [
                            {"from": "ph.phase", "to": "osc.phase"},
                            {"from": "osc.audio", "to": "vca.audio"},
                            {"from": "env.cv", "to": "vca.cv"},
                        ],
                        "voice_out": "vca.audio",
                    },
                    "global": {"nodes": [], "wires": []},
                }
            ),
            encoding="utf-8",
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(["budget", str(d / "patch.json"), "--voices", "4,8"])
        assert rc == 0, "budget failed"
        out = buf.getvalue()
        rows = [
            line.split()
            for line in out.splitlines()
            if line.strip() and line.split()[0].isdigit()
        ]
        assert len(rows) == 2, f"expected two measured rows, got {out}"
        t4, t8 = float(rows[0][1]), float(rows[1][1])
        assert t4 > 0 and t8 >= t4, "the 8-voice render is not >= the 4-voice"
        assert "emulator" in out, "the device fit does not point at the emulator"


def _budget_measures_tabled() -> None:
    """`umetate budget` generates + compiles the patch's `tables:` (a regression:
    the dogfood's `routing` table once left `table_routing` undefined)."""
    root = Path(__file__).resolve().parents[1]
    patch = root / "examples" / "type-p-fm1" / "patch.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(["budget", str(patch), "--voices", "8"])
    assert rc == 0, f"budget on a tabled patch failed:\n{buf.getvalue()}"
    out = buf.getvalue()
    rows = [
        line.split()
        for line in out.splitlines()
        if line.strip() and line.split()[0].isdigit()
    ]
    assert len(rows) == 1 and float(rows[0][1]) > 0, f"no measured row: {out}"


def _synth_build_composes() -> None:
    """`umetate build --synth examples/type-p-fm1` composes the dogfood firmware:
    the generated engine/panel/CC/layout files, a sounding host run, and — with
    the toolchain — the target package."""
    import struct
    import wave

    root = Path(__file__).resolve().parents[1]
    ffm = root / "examples" / "type-p-fm1"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = cli.main(["build", "--synth", str(ffm)])
    assert rc == 0, f"build --synth failed:\n{buf.getvalue()}"
    out = buf.getvalue()
    gen = root / "firmware" / "gen"
    for filename in (
        "type_p_fm1_dsp.c",
        "dsp.h",
        "cc_map.h",
        "synth_layout.h",
        "panel.h",
        "app.c",
    ):
        assert (gen / filename).is_file(), f"build --synth did not write gen/{filename}"
    wav_path = root / "firmware" / "build" / "host" / "type_p_fm1.wav"
    assert wav_path.is_file(), "build --synth produced no host WAV"
    with wave.open(str(wav_path), "rb") as w:
        frames = w.readframes(w.getnframes())
    peak = max(abs(v) for (v,) in struct.iter_unpack("<h", frames))
    assert peak > 1000, f"the dogfood host run is silent (peak {peak})"
    pkg = root / "firmware" / "build" / "umetate-fm1-pro-type_p_fm1.fwsc"
    if "target package blocked" not in out:
        assert pkg.is_file(), "with the toolchain, the synth package must exist"


def _emu_package_preference() -> None:
    """`emu` boots the newest composed synth package, falling back to the demo."""
    import os

    from . import emu

    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        demo = build / "umetate-fm1-pro.fwsc"
        demo.write_bytes(b"demo")
        assert emu._default_fwsc("fm1", build) == demo, "no synth package -> the demo"  # pyright: ignore[reportPrivateUsage]
        synth_a = build / "umetate-fm1-pro-a.fwsc"
        synth_b = build / "umetate-fm1-pro-b.fwsc"
        synth_a.write_bytes(b"a")
        synth_b.write_bytes(b"b")
        old = synth_b.stat().st_mtime - 10.0
        os.utime(synth_a, (old, old))
        assert emu._default_fwsc("fm1", build) == synth_b, (  # pyright: ignore[reportPrivateUsage]
            "the newest synth package wins"
        )


def _publish_includes_plugin_source() -> None:
    from . import publish

    framework_paths = publish._FRAMEWORK_PATHS  # pyright: ignore[reportPrivateUsage]
    assert "plugin" in framework_paths, "publish omits the plugin source"
    assert "design" in framework_paths, "publish omits design/tokens.json"
    assert "skills" in framework_paths, "publish omits the design/skill references"
    assert "templates" in framework_paths, "publish omits the control-map template"
    assert (
        "plugin.json" in publish._SRC_FILES  # pyright: ignore[reportPrivateUsage]
    ), "publish omits the plugin identity"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert publish._project_title(root, "fallback") == "fallback"  # pyright: ignore[reportPrivateUsage]
        synth = root / "synth"
        synth.mkdir()
        (synth / "plugin.json").write_text(
            '{"product_name": "Type X"}\n', encoding="utf-8"
        )
        assert publish._project_title(synth, "fallback") == "Type X"  # pyright: ignore[reportPrivateUsage]

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build = root / "build"
        vst3 = (
            build
            / "juce"
            / "type_p_fm1_artefacts"
            / "Release"
            / "VST3"
            / "Type P.fm1.vst3"
        )
        (vst3 / "Contents" / "x86_64-linux").mkdir(parents=True)
        (vst3 / "Contents" / "x86_64-linux" / "Type P.fm1.so").write_bytes(b"vst3")
        clap = build / "juce" / "type_p_fm1_artefacts" / "Release" / "CLAP"
        clap.mkdir(parents=True)
        (clap / "Type P.fm1.clap").write_bytes(b"clap")

        # the Linux DAW test copies the bundle into an isolated HOME. Publish must
        # not stage that copy or the hidden .vst3 folder as a second artefact.
        decoy = build / "juce" / "linux-daws" / "home" / ".vst3" / "Type P.fm1.vst3"
        (decoy / "Contents" / "x86_64-linux").mkdir(parents=True)
        (decoy / "Contents" / "x86_64-linux" / "Type P.fm1.so").write_bytes(b"x")
        decoy_clap = build / "juce" / "linux-daws" / "home" / ".clap"
        decoy_clap.mkdir(parents=True)
        (decoy_clap / "Type P.fm1.clap").write_bytes(b"x")

        out = root / "out"
        out.mkdir()
        stage_plugins = publish._stage_plugins  # pyright: ignore[reportPrivateUsage]
        write_dependencies = publish._write_dependencies  # pyright: ignore[reportPrivateUsage]
        readme_template = publish._README  # pyright: ignore[reportPrivateUsage]
        plugins_section = publish._PLUGINS_SECTION  # pyright: ignore[reportPrivateUsage]
        source_section = publish._PLUGIN_SOURCE_SECTION  # pyright: ignore[reportPrivateUsage]

        staged = stage_plugins(out, build, "linux-x86_64")
        assert len(staged) == 2, staged
        assert (out / "plugins" / "linux-x86_64" / staged[0]).is_file()
        readme = (out / "plugins" / "README.md").read_text(encoding="utf-8")
        assert "AGPL-3.0-only" in readme, "plugin readme omits the JUCE licence"

        win_build = root / "build-win"
        win_vst3 = (
            win_build
            / "juce"
            / "type_p_fm1_artefacts"
            / "Release"
            / "VST3"
            / "Type P.fm1.vst3"
        )
        (win_vst3 / "Contents" / "x86_64-win").mkdir(parents=True)
        (win_vst3 / "Contents" / "x86_64-win" / "Type P.fm1.vst3").write_bytes(b"vst3")
        staged_win = stage_plugins(out, win_build, "windows-x86_64")
        assert len(staged_win) == 1, staged_win
        readme = (out / "plugins" / "README.md").read_text(encoding="utf-8")
        assert "linux-x86_64/Type-P.fm1-VST3-linux-x86_64.zip" in readme
        assert "windows-x86_64/Type-P.fm1-VST3-windows-x86_64.zip" in readme

        write_dependencies(out, vendored=True)
        deps = (out / "DEPENDENCIES.md").read_text(encoding="utf-8")
        assert "8.0.9" in deps and "7adee3a" in deps, "dependency pins are missing"
        assert "vendor/deps" in deps, "vendored source note is missing"

        plain = readme_template.format(
            title="X", repo_url="u", fwsc="x.fwsc", plugins="", plugin_source=""
        )
        assert "plugins/README.md" not in plain, "no-plugin README has a dead link"
        with_plugins = readme_template.format(
            title="X",
            repo_url="u",
            fwsc="x.fwsc",
            plugins=plugins_section,
            plugin_source=source_section,
        )
        assert "## Plugins" in with_plugins and "AGPL" not in with_plugins


def _plugin_generate_roundtrip() -> None:
    """`plugin-generate` renders the project and `--check` notices drift."""
    from . import plugin_cli

    root = Path(__file__).resolve().parents[1]
    synth = root / "examples" / "type-p-fm1"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "project"
        args = ["--synth", str(synth), "--out", str(out)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = plugin_cli.generate_main(args)
        assert rc == 0, buf.getvalue()

        project = (out / "P1Project.cmake").read_text(encoding="utf-8")
        assert 'set(P1_PRODUCT_NAME "Type P.fm1")' in project
        assert 'set(P1_PLUGIN_TARGET "type_p_fm1")' in project
        assert 'set(P1_SYNTH_GEN "${CMAKE_CURRENT_LIST_DIR}/gen")' in project
        assert (out / "gen" / "type_p_fm1_dsp.c").is_file()
        assert (out / "gen" / "params.json").is_file()
        assert (out / "CMakeLists.txt").is_file()
        assert (out / "README.md").is_file()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = plugin_cli.generate_main([*args, "--check"])
        assert rc == 0, buf.getvalue()
        assert "is current" in buf.getvalue()

        (out / "gen" / "params.json").write_text("{}\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = plugin_cli.generate_main([*args, "--check"])
        assert rc == 1, "a stale generated file must fail the check"
        assert "stale gen/params.json" in buf.getvalue()

        (out / "gen" / "stray.c").write_text("x\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = plugin_cli.generate_main(args)
        assert rc == 0, buf.getvalue()
        assert not (out / "gen" / "stray.c").exists(), (
            "regeneration leaves a stray file"
        )


def _plugin_identity_rules() -> None:
    """The plugin identity comes from plugin.json and is validated."""
    from . import plugin_cli
    from ._ir import GenError

    with tempfile.TemporaryDirectory() as tmp:
        synth = Path(tmp)
        (synth / "plugin.json").write_text(
            json.dumps(
                {
                    "product_name": "Test.fm",
                    "bundle_id": "com.example.testfm",
                    "manufacturer_code": "Tst1",
                    "plugin_code": "Tfm1",
                }
            ),
            encoding="utf-8",
        )
        meta = plugin_cli.load_meta(synth, "test_fm")
        assert meta.product_name == "Test.fm"
        assert meta.plugin_code == "Tfm1"

        override = plugin_cli.load_meta(
            synth, "test_fm", product_name="Override", plugin_code="Ovr1"
        )
        assert override.product_name == "Override"
        assert override.plugin_code == "Ovr1"

        (synth / "plugin.json").write_text(
            json.dumps({"plugin_code": "TOOLONG"}), encoding="utf-8"
        )
        try:
            plugin_cli.load_meta(synth, "test_fm")
        except GenError:
            pass
        else:
            raise AssertionError("a five-character plugin code must be rejected")

        (synth / "plugin.json").write_text(
            json.dumps({"product_name": 'Bad "quoted" name'}), encoding="utf-8"
        )
        try:
            plugin_cli.load_meta(synth, "test_fm")
        except GenError:
            pass
        else:
            raise AssertionError("a quoted product name must be rejected")


def _publish_release_manifest() -> None:
    """The release page, checksums, and manifest cover the firmware and plugins."""
    from . import publish

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "release"
        out.mkdir()
        (out / "type-p-fm1.fwsc").write_bytes(b"fw")
        plugin = out / "plugins" / "linux-x86_64" / "Type-P.fm1-VST3-linux-x86_64.zip"
        plugin.parent.mkdir(parents=True)
        plugin.write_bytes(b"vst3")
        (out / "vendor" / "deps").mkdir(parents=True)

        synth = Path(tmp) / "synth"
        (synth / "docs").mkdir(parents=True)
        (synth / "docs" / "release-notes.md").write_text(
            "# Notes\n\n## 1.2.3\n\n- x\n", encoding="utf-8"
        )
        version = publish._version_of(synth)  # pyright: ignore[reportPrivateUsage]
        assert version == "1.2.3", version

        artifacts = publish._release_artifacts(  # pyright: ignore[reportPrivateUsage]
            out, "type-p-fm1"
        )
        assert [artifact["format"] for artifact in artifacts] == [
            "firmware",
            "VST3",
        ], artifacts
        publish._write_release(  # pyright: ignore[reportPrivateUsage]
            out,
            "Type P.fm1",
            version,
            "abc1234",
            artifacts,
            released="2026-11-04",
        )

        sums = (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        assert len(sums) == 2, sums
        assert all(len(line.split()[0]) == 64 for line in sums), sums

        page = (out / "RELEASES.md").read_text(encoding="utf-8")
        assert "# Type P.fm1 1.2.3" in page
        assert "abc1234" in page
        assert "type-p-fm1.fwsc" in page and "Type-P.fm1-VST3" in page
        assert "src/" in page and "framework/" in page and "vendor/deps/" in page

        manifest = json.loads((out / "release.json").read_text(encoding="utf-8"))
        assert manifest["version"] == "1.2.3"
        assert manifest["commit"] == "abc1234"
        assert len(manifest["artifacts"]) == 2


def _publish_vendor_copy() -> None:
    """Vendored deps keep the source and drop .git and build trees."""
    from . import publish

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "_deps"
        (src / "juce-src" / "modules").mkdir(parents=True)
        (src / "juce-src" / "modules" / "juce.cpp").write_text("x", encoding="utf-8")
        (src / "juce-src" / ".git").mkdir()
        (src / "juce-src" / ".git" / "config").write_text("x", encoding="utf-8")
        (src / "juce-build").mkdir()
        (src / "juce-build" / "CMakeCache.txt").write_text("x", encoding="utf-8")
        (src / "juce-subbuild").mkdir()
        (src / "juce-subbuild" / "build.ninja").write_text("x", encoding="utf-8")
        (src / "clap-juce-extensions-src").mkdir()
        (src / "clap-juce-extensions-src" / "clap.cpp").write_text(
            "x", encoding="utf-8"
        )

        dest = Path(tmp) / "vendor" / "deps"
        publish._copy_vendor(src, dest)  # pyright: ignore[reportPrivateUsage]
        assert (dest / "juce-src" / "modules" / "juce.cpp").is_file()
        assert (dest / "clap-juce-extensions-src" / "clap.cpp").is_file()
        assert not (dest / "juce-src" / ".git").exists()
        assert not (dest / "juce-build").exists()
        assert not (dest / "juce-subbuild").exists()


def _interview_roundtrip() -> None:
    """The design interview form writes, reports gaps, and round-trips."""
    from . import interview

    with tempfile.TemporaryDirectory() as tmp:
        synth = Path(tmp)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = interview.main(["--synth", str(synth), "--write"])
        assert rc == 0, buf.getvalue()

        form = synth / "design-interview.md"
        assert form.is_file(), "interview --write did not create the form"
        text = form.read_text(encoding="utf-8")
        assert "Type P.fm1" not in text, "the generic form leaked a Type P.fm1 name"
        assert "Yamaha" not in text, "the generic form leaked an FM-specific term"
        assert "{{" not in text, "a template placeholder was left in the form"
        questions = interview.parse_questions(text)
        assert len(questions) >= 20, len(questions)
        assert not any(question.answered for question in questions)
        assert any(
            "Which instruments, chips, or algorithms" in question.prompt
            and "take from each?" in question.prompt
            for question in questions
        ), "a multi-line question was truncated"

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = interview.main(["--synth", str(synth), "--check"])
        assert rc == 1, "a fresh form must have gaps"
        assert "questions still open" in buf.getvalue()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = interview.main(["--synth", str(synth), "--next", "1"])
        assert rc == 0
        assert "The first sound" in buf.getvalue()

        form.write_text(text.replace("**A:**", "**A:** answered"), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = interview.main(["--synth", str(synth), "--check"])
        assert rc == 0, buf.getvalue()
        assert "all" in buf.getvalue()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = interview.main(["--synth", str(synth), "--write"])
        assert rc == 1, "an existing form needs --force"
        assert "exists" in buf.getvalue()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = interview.main(["--synth", str(synth), "--write", "--force"])
        assert rc == 0, buf.getvalue()
        assert "answered" not in form.read_text(encoding="utf-8")


def _interview_project_specific() -> None:
    """The generated form uses the project's own architecture and brief."""
    from . import interview

    root = Path(__file__).resolve().parents[1]
    form = interview.generate_form(root / "examples" / "type-p-fm1")
    assert "Type P.fm1" in form
    assert "fm_op x4" in form, "the voice zone nodes are missing"
    assert "DX7" in form, "the brief references are missing"
    assert "ALGORITHM" in form, "the panel pages are missing"
    assert "{{" not in form, "a template placeholder was left in the form"


def main() -> int:
    tests: _Tests = [
        ("no import side effects", _no_import_side_effects),
        ("--help lists all commands", _help_lists_all),
        ("version prints __version__", _version_command),
        ("status parses the roadmap", _status_parses),
        ("quick-check --json emits the layer/status shape", _quick_check_json),
        ("lib list shows nodes + templates", _lib_lists),
        ("scaffold patch builds", _scaffold_builds),
        ("scaffold synth emits a full firmware", _scaffold_synth),
        ("lint --c catches a MAXP violation", _lint_catches_violation),
        ("setup --dry-run plans the install", _setup_dry_run_plans),
        ("the fm1-emu binary paths resolve", _emu_paths),
        ("emu prefers the newest synth package", _emu_package_preference),
        ("evidence validates a matrix", _evidence_validates),
        ("the wasm import parser counts imports", _wasm_import_parser),
        ("flash gates + wrong-model exit 6", _flash_gates),
        ("flash asks before writing", _flash_confirms),
        ("debrick names the routes", _debrick_routes),
        ("the skill bundles are in sync", _skill_check),
        ("the docs cross-references resolve", _links_check),
        ("the preset records round-trip", _records_roundtrip),
        ("the SysEx envelope round-trips", _sysex_roundtrip),
        ("the preset bank exports + imports", _bank_roundtrip),
        ("preset export/import round-trips via the CLI", _preset_export_import),
        ("the C preset store matches the Python records", _preset_c_parity),
        ("the C SysEx handler matches the Python envelope", _sysex_c_parity),
        ("umetate budget measures the polyphony scaling", _budget_measures),
        ("umetate budget compiles the patch's tables", _budget_measures_tabled),
        ("build --synth composes the dogfood firmware", _synth_build_composes),
        (
            "publish carries the plugin source + bundles",
            _publish_includes_plugin_source,
        ),
        (
            "publish writes the release page, checksums + manifest",
            _publish_release_manifest,
        ),
        ("publish copies only the vendored source", _publish_vendor_copy),
        ("the design interview form round-trips", _interview_roundtrip),
        (
            "the design interview reads the project",
            _interview_project_specific,
        ),
        (
            "plugin-generate renders the project and catches drift",
            _plugin_generate_roundtrip,
        ),
        ("the plugin identity is validated", _plugin_identity_rules),
    ]
    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"ok: {name}")
        except AssertionError as exc:
            print(f"FAIL: {name}: {exc}")
            failures += 1
    print("cli tests " + ("FAILED" if failures else "passed"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
