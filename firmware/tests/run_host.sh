#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Run src/rib.c on this computer (tests/host.c): WAV and screen PNGs.
#   tests/run_host.sh [script]               your own script (tests/host.c says what a line can do)
#   BOARD=smk37 tests/run_host.sh [script]   the SMK-37 build
set -e
cd "$(dirname "$0")/.."
OUT="${UMETATE_TEST_BUILD:-build}/host"
mkdir -p "$OUT"
CC="${CC:-cc}"
PY="${PYTHON:-python3}"
N=rib; D=
if [ "${BOARD:-fm1}" = smk37 ]; then N=rib-smk37; D=-DBOARD_SMK37=1; fi
"$CC" -O2 -Wall -Wno-unused-function -DUMETATE_HOST $D -DAPP_VER="\"${APP_VER:-dev}\"" \
    -Ihal -Isrc -Igen -o "$OUT/$N" src/rib.c src/rib_dsp.c
"$OUT/$N" "$OUT/$N" ${1:+"$1"}
${PYTHON:-python3} - "$N" "$OUT" <<'PY'
import sys
from pathlib import Path
from PIL import Image
name, output = sys.argv[1:]
for path in sorted(Path(output).glob(name + "-*.ppm")):
    Image.open(path).resize((480, 480), Image.NEAREST).save(path.with_suffix(".png"))
    path.unlink()
    print("screen ->", path.with_suffix(".png"))
PY
