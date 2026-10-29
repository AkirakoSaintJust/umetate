#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
set -eu
cd "$(dirname "$0")/.."
BUILD_DIR="${UMETATE_CMAKE_BUILD:-build/cmake-host}"
CMAKE="${CMAKE:-cmake}"
"$CMAKE" -S . -B "$BUILD_DIR" -G Ninja -DUMETATE_BOARD=fm1 -DUMETATE_MODEL=pro -DUMETATE_PROFILE=baseline
"$CMAKE" --build "$BUILD_DIR" --target test-host
"$CMAKE" --build "$BUILD_DIR" --target dsp_test
"$CMAKE" --build "$BUILD_DIR" --target uac_test
"$CMAKE" --build "$BUILD_DIR" --target bootguard_test
"$CMAKE" --build "$BUILD_DIR" --target presets_test
"$CMAKE" --build "$BUILD_DIR" --target sysex_test
"$CMAKE" --build "$BUILD_DIR" --target midi_test
"$CMAKE" --build "$BUILD_DIR" --target runtime_test
"$CMAKE" -E env "UMETATE_TEST_BUILD=${BUILD_DIR}/test-artifacts" "CC=${CC:-cc}" BOARD=smk37 \
    sh tests/run_host.sh tests/scripts/smk37.txt
