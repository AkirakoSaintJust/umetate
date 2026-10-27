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
from typing import Any

import umetate.cli as cli
from umetate import __version__

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
    assert "phasor" in out and "pocket-drone" in out


def _scaffold_builds() -> None:
    from . import scaffold

    with tempfile.TemporaryDirectory() as tmp:
        rc = scaffold.main(["patch", "--name", "t", "--out", tmp])
        assert rc == 0
        assert (Path(tmp) / "patch.json").exists()
        assert (Path(tmp) / "panel.json").exists()


def _lint_catches_violation() -> None:
    from . import lint

    violation = lint._FW / "src" / "_viol.c"
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

    good = {
        "layers": [
            {"layer": "source", "status": "pass", "detail": "x"},
            {"layer": "device", "status": "blocked", "detail": "x"},
        ]
    }
    assert evidence.validate(good) == []
    assert evidence.validate({"layers": [{"layer": "wobble", "status": "pass"}]})
    dup = {
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
    fm1: Any, product: str = "FM-1_900", size: int = 0x2000
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

    def __init__(self, fm1: Any, identity: str) -> None:
        self._fm1 = fm1
        self._identity = identity.encode()

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
        t = self._b._identity
        body = bytes([0, 0x59, 0x11, 0, 0, 0]) + t + bytes(28 - len(t))
        return b"\xf0" + bytes(self._b._fm1.pack7(body)) + b"\xf7"

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
    fm1 = F._load()
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


def main() -> int:
    tests: _Tests = [
        ("no import side effects", _no_import_side_effects),
        ("--help lists all commands", _help_lists_all),
        ("version prints __version__", _version_command),
        ("status parses the roadmap", _status_parses),
        ("quick-check --json emits the layer/status shape", _quick_check_json),
        ("lib list shows nodes + templates", _lib_lists),
        ("scaffold patch builds", _scaffold_builds),
        ("lint --c catches a MAXP violation", _lint_catches_violation),
        ("setup --dry-run plans the install", _setup_dry_run_plans),
        ("the fm1-emu binary paths resolve", _emu_paths),
        ("evidence validates a matrix", _evidence_validates),
        ("the wasm import parser counts imports", _wasm_import_parser),
        ("flash gates + wrong-model exit 6", _flash_gates),
        ("debrick names the routes", _debrick_routes),
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
