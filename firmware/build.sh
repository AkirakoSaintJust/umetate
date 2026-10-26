#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
# Configure and build a target package with CMake/Ninja.
#   ./build.sh [--release X.Y[.Z][-suffix]] [--board fm1|smk37] [--model pro|elite|mke] [--profile baseline|performance]
set -eu
cd "$(dirname "$0")"
export JIELI_TOOLCHAIN="${JIELI_TOOLCHAIN:-${UMETATE_TOOLCHAIN:-/opt/jieli/toolchain}}"
export AC79_SDK="${AC79_SDK:-${UMETATE_SDK:-/opt/jieli/sdk}}"
BOARD="${BOARD:-fm1}"
MODEL="${MODEL:-pro}"
PROFILE="${UMETATE_PROFILE:-baseline}"
RELEASE=""
REPORT_CONFIG=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --release) [ "$#" -ge 2 ] || { echo "--release needs X.Y" >&2; exit 2; }; RELEASE=$2; shift 2 ;;
        --board) [ "$#" -ge 2 ] || { echo "--board needs fm1 or smk37" >&2; exit 2; }; BOARD=$2; shift 2 ;;
        --model) [ "$#" -ge 2 ] || { echo "--model needs pro, elite or mke" >&2; exit 2; }; MODEL=$2; shift 2 ;;
        --profile) [ "$#" -ge 2 ] || { echo "--profile needs baseline or performance" >&2; exit 2; }; PROFILE=$2; shift 2 ;;
        --report-config) REPORT_CONFIG=1; shift ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
case "$BOARD:$MODEL:$PROFILE" in
    fm1:pro:baseline|fm1:pro:performance|smk37:pro:baseline|smk37:pro:performance|smk37:elite:baseline|smk37:elite:performance|smk37:mke:baseline|smk37:mke:performance) ;;
    *) echo "invalid board/model/profile combination: $BOARD/$MODEL/$PROFILE" >&2; exit 2 ;;
esac
PY="${PYTHON:-python3}"
CMAKE="${CMAKE:-cmake}"
NINJA="${NINJA:-ninja}"
command -v "$PY" >/dev/null 2>&1 || { echo "Python 3.8+ is required" >&2; exit 1; }
"$PY" -c 'import sys; assert sys.version_info >= (3, 8)' || { echo "Python 3.8+ is required" >&2; exit 1; }
command -v "$CMAKE" >/dev/null 2>&1 || { echo "CMake 3.20+ is required" >&2; exit 1; }
command -v "$NINJA" >/dev/null 2>&1 || { echo "Ninja is required" >&2; exit 1; }
BUILD_DIR="${UMETATE_BUILD_DIR:-build/cmake-${BOARD}-${MODEL}-${PROFILE}}"
set -- -S . -B "$BUILD_DIR" -G Ninja \
    -DUMETATE_BOARD="$BOARD" -DUMETATE_MODEL="$MODEL" -DUMETATE_PROFILE="$PROFILE" \
    -DJIELI_TOOLCHAIN="$JIELI_TOOLCHAIN" -DAC79_SDK="$AC79_SDK" \
    -DUMETATE_DEFS="${UMETATE_DEFS:-}"
[ -z "$RELEASE" ] || set -- "$@" "-DUMETATE_RELEASE=$RELEASE"
"$CMAKE" "$@"
if [ "$REPORT_CONFIG" = 1 ]; then
    "$PY" tools/build.py --board "$BOARD" --model "$MODEL" --profile "$PROFILE" --report-config
    exit 0
fi
[ -x "$JIELI_TOOLCHAIN/pi32v2/bin/clang" ] || { echo "no JieLi toolchain in $JIELI_TOOLCHAIN" >&2; exit 1; }
for asset in uboot.boot cfg_tool.bin cfg/eq_cfg_hw.bin; do
    [ -f "$AC79_SDK/cpu/wl82/tools/$asset" ] || { echo "missing AC79 SDK asset $asset in $AC79_SDK" >&2; exit 1; }
done
"$CMAKE" --build "$BUILD_DIR" --target target_package
