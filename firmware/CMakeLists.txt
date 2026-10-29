cmake_minimum_required(VERSION 3.20)

project(umetate LANGUAGES C)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(UMETATE_BOARD "fm1" CACHE STRING "Target board: fm1 or smk37")
set_property(CACHE UMETATE_BOARD PROPERTY STRINGS fm1 smk37)
set(UMETATE_MODEL "pro" CACHE STRING "SMK-37 model: pro, elite or mke")
set_property(CACHE UMETATE_MODEL PROPERTY STRINGS pro elite mke)
set(UMETATE_PROFILE "baseline" CACHE STRING "DSP optimization profile: baseline or performance")
set_property(CACHE UMETATE_PROFILE PROPERTY STRINGS baseline performance)
set(UMETATE_RELEASE "" CACHE STRING "Optional release version, e.g. 1.2")
set(UMETATE_DEFS "" CACHE STRING "Additional preprocessor definitions for app builds")
set(JIELI_TOOLCHAIN "$ENV{JIELI_TOOLCHAIN}" CACHE PATH "JieLi Linux toolchain root")
set(AC79_SDK "$ENV{AC79_SDK}" CACHE PATH "AC79 SDK root")
set(JIELI_DOCKER "$ENV{JIELI_DOCKER}" CACHE STRING "Run target tools in Docker (0 or 1)")
set(JIELI_DOCKER_IMAGE "$ENV{JIELI_DOCKER_IMAGE}" CACHE STRING "Container image used for target tools")

if(NOT UMETATE_BOARD MATCHES "^(fm1|smk37)$")
    message(FATAL_ERROR "UMETATE_BOARD must be fm1 or smk37")
endif()
if(NOT UMETATE_MODEL MATCHES "^(pro|elite|mke)$" OR (NOT UMETATE_BOARD STREQUAL "smk37" AND NOT UMETATE_MODEL STREQUAL "pro"))
    message(FATAL_ERROR "UMETATE_MODEL must be pro, elite or mke, and non-pro models require UMETATE_BOARD=smk37")
endif()
if(NOT UMETATE_PROFILE MATCHES "^(baseline|performance)$")
    message(FATAL_ERROR "UMETATE_PROFILE must be baseline or performance")
endif()
if(NOT JIELI_DOCKER MATCHES "^(|0|1)$")
    message(FATAL_ERROR "JIELI_DOCKER must be 0 or 1")
endif()

find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)
find_program(UMETATE_HOST_CC NAMES cc gcc clang)
if(NOT UMETATE_HOST_CC)
    message(FATAL_ERROR "A host C compiler (cc, gcc, or clang) is required for host targets")
endif()

# Keep existing app/package consumers and test scripts working without artifact migration.
set(UMETATE_ARTIFACT_DIR "${CMAKE_SOURCE_DIR}/build")
set(UMETATE_HOST_DIR "${UMETATE_ARTIFACT_DIR}/host")
file(MAKE_DIRECTORY "${UMETATE_HOST_DIR}")
set(UMETATE_PACKAGE_NAME "umetate-${UMETATE_BOARD}-${UMETATE_MODEL}")
if(UMETATE_RELEASE)
    string(APPEND UMETATE_PACKAGE_NAME "-${UMETATE_RELEASE}")
endif()
string(APPEND UMETATE_PACKAGE_NAME ".fwsc")

set(UMETATE_HOST_FLAGS -O2 -Wall -Wno-unused-function -DUMETATE_HOST "-DAPP_VER=\"dev\""
    -Ihal -Isrc -Igen)
if(UMETATE_BOARD STREQUAL "smk37")
    list(APPEND UMETATE_HOST_FLAGS -DBOARD_SMK37=1)
    set(UMETATE_HOST_NAME rib-smk37)
else()
    set(UMETATE_HOST_NAME rib)
endif()

file(GLOB_RECURSE UMETATE_HOST_INPUTS CONFIGURE_DEPENDS
    src/*.c src/*.h gen/* hal/*.h tests/host.c)
add_custom_command(
    OUTPUT "${UMETATE_HOST_DIR}/${UMETATE_HOST_NAME}"
    COMMAND "${UMETATE_HOST_CC}" ${UMETATE_HOST_FLAGS} -o "${UMETATE_HOST_DIR}/${UMETATE_HOST_NAME}"
        "${CMAKE_SOURCE_DIR}/src/rib.c" "${CMAKE_SOURCE_DIR}/src/rib_dsp.c"
    DEPENDS ${UMETATE_HOST_INPUTS}
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    VERBATIM)
add_custom_target(host_app DEPENDS "${UMETATE_HOST_DIR}/${UMETATE_HOST_NAME}")

add_custom_target(host_test
    COMMAND "${CMAKE_COMMAND}" -E env "UMETATE_TEST_BUILD=${CMAKE_BINARY_DIR}/test-artifacts" "CC=${UMETATE_HOST_CC}"
        "${CMAKE_SOURCE_DIR}/tests/run_host.sh"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    USES_TERMINAL VERBATIM)
add_custom_target(dsp_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Ihal -Isrc -Igen
        -o "${UMETATE_HOST_DIR}/dsp_test" "${CMAKE_SOURCE_DIR}/tests/dsp_test.c" "${CMAKE_SOURCE_DIR}/src/rib_dsp.c" "${CMAKE_SOURCE_DIR}/src/dsp_ipc.c"
    COMMAND "${UMETATE_HOST_DIR}/dsp_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/rib_dsp.c src/rib_dsp.h src/dsp_ipc.c tests/dsp_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(ipc_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Ihal -Isrc
        -o "${UMETATE_HOST_DIR}/ipc_test" "${CMAKE_SOURCE_DIR}/tests/ipc_test.c"
    COMMAND "${UMETATE_HOST_DIR}/ipc_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS hal/fm1_ipc.h tests/ipc_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(math_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wno-comment -Ivendor
        -c "${CMAKE_SOURCE_DIR}/vendor/kiss_fft/kiss_fft.c" -o "${UMETATE_HOST_DIR}/kiss_fft.o"
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -DFM1_MATH_FFT -Ihal -Igen -Ivendor
        -c "${CMAKE_SOURCE_DIR}/tests/math_test.c" -o "${UMETATE_HOST_DIR}/math_test.o"
    COMMAND "${UMETATE_HOST_CC}" -o "${UMETATE_HOST_DIR}/math_test" "${UMETATE_HOST_DIR}/math_test.o" "${UMETATE_HOST_DIR}/kiss_fft.o" -lm
    COMMAND "${UMETATE_HOST_DIR}/math_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS hal/fm1_math.h gen/math_tables.h tests/math_test.c vendor/kiss_fft/kiss_fft.c vendor/kiss_fft/kiss_fft.h
    USES_TERMINAL VERBATIM)
add_custom_target(kernel_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Ihal
        -o "${UMETATE_HOST_DIR}/kernel_test" "${CMAKE_SOURCE_DIR}/tests/kernel_test.c"
    COMMAND "${UMETATE_HOST_DIR}/kernel_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS hal/fm1_dsp_kernels.h tests/kernel_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(scope_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Ihal -Igen -Isrc
        -o "${UMETATE_HOST_DIR}/scope_test" "${CMAKE_SOURCE_DIR}/tests/scope_test.c" "${CMAKE_SOURCE_DIR}/src/scope.c"
    COMMAND "${UMETATE_HOST_DIR}/scope_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/scope.c src/scope.h hal/fm1_math.h gen/math_tables.h tests/scope_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(uac_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Isrc
        -o "${UMETATE_HOST_DIR}/uac_test" "${CMAKE_SOURCE_DIR}/tests/uac_test.c"
    COMMAND "${UMETATE_HOST_DIR}/uac_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/uac_fir.h src/uac_tap.h tests/uac_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(bootguard_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror
        -o "${UMETATE_HOST_DIR}/bootguard_test" "${CMAKE_SOURCE_DIR}/tests/bootguard_test.c"
    COMMAND "${UMETATE_HOST_DIR}/bootguard_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/bootguard.h tests/bootguard_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(ui_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function
        -Ihal -Isrc -Igen -Itests
        -o "${UMETATE_HOST_DIR}/ui_test" "${CMAKE_SOURCE_DIR}/tests/ui_test.c"
    COMMAND "${UMETATE_HOST_DIR}/ui_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/ui.c src/ui.h src/gfx.c gen/felucca_font.h tests/ui_test.c tests/accept.h
    USES_TERMINAL VERBATIM)
add_custom_target(presets_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Isrc
        -o "${UMETATE_HOST_DIR}/presets_test" "${CMAKE_SOURCE_DIR}/tests/presets_test.c"
    COMMAND "${UMETATE_HOST_DIR}/presets_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/presets.c src/presets.h tests/presets_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(sysex_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Isrc
        -o "${UMETATE_HOST_DIR}/sysex_test" "${CMAKE_SOURCE_DIR}/tests/sysex_test.c"
    COMMAND "${UMETATE_HOST_DIR}/sysex_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/presets.c src/presets.h src/synth_sysex.c src/synth_sysex.h tests/sysex_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(midi_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Isrc
        -o "${UMETATE_HOST_DIR}/midi_test" "${CMAKE_SOURCE_DIR}/tests/midi_test.c"
    COMMAND "${UMETATE_HOST_DIR}/midi_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/synth_midi.c src/synth_midi.h tests/midi_test.c
    USES_TERMINAL VERBATIM)
add_custom_target(runtime_test
    COMMAND "${UMETATE_HOST_CC}" -std=c11 -Wall -Wextra -Werror -Isrc
        -o "${UMETATE_HOST_DIR}/runtime_test" "${CMAKE_SOURCE_DIR}/tests/runtime_test.c"
    COMMAND "${UMETATE_HOST_DIR}/runtime_test"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS src/presets.c src/presets.h src/synth_runtime.c src/synth_runtime.h tests/runtime_test.c
    USES_TERMINAL VERBATIM)

if(UMETATE_BOARD STREQUAL "smk37")
    add_custom_target(test-host
        COMMAND "${CMAKE_COMMAND}" -E env "UMETATE_TEST_BUILD=${CMAKE_BINARY_DIR}/test-artifacts" "CC=${UMETATE_HOST_CC}" "BOARD=smk37"
            "${CMAKE_SOURCE_DIR}/tests/run_host.sh"
        COMMAND "${CMAKE_COMMAND}" -E env "UMETATE_TEST_BUILD=${CMAKE_BINARY_DIR}/test-artifacts" "CC=${UMETATE_HOST_CC}" "BOARD=smk37"
            "${CMAKE_SOURCE_DIR}/tests/run_host.sh" "${CMAKE_SOURCE_DIR}/tests/scripts/smk37.txt"
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        USES_TERMINAL VERBATIM)
else()
    add_custom_target(test-host
        COMMAND "${CMAKE_COMMAND}" -E env "UMETATE_TEST_BUILD=${CMAKE_BINARY_DIR}/test-artifacts" "CC=${UMETATE_HOST_CC}"
            "${CMAKE_SOURCE_DIR}/tests/run_host.sh"
        COMMAND "${CMAKE_COMMAND}" -E env "UMETATE_TEST_BUILD=${CMAKE_BINARY_DIR}/test-artifacts" "CC=${UMETATE_HOST_CC}"
            "${CMAKE_SOURCE_DIR}/tests/run_host.sh" "${CMAKE_SOURCE_DIR}/tests/scripts/midi.txt"
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        USES_TERMINAL VERBATIM)
endif()

add_custom_target(test_all
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target test-host
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target dsp_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target ipc_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target math_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target kernel_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target scope_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target uac_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target bootguard_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target ui_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target presets_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target sysex_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target midi_test
    COMMAND "${CMAKE_COMMAND}" --build "${CMAKE_BINARY_DIR}" --target runtime_test
    COMMAND "${CMAKE_COMMAND}" -E env "UMETATE_TEST_BUILD=${CMAKE_BINARY_DIR}/test-artifacts" "CC=${UMETATE_HOST_CC}" "BOARD=smk37"
        "${CMAKE_SOURCE_DIR}/tests/run_host.sh" "${CMAKE_SOURCE_DIR}/tests/scripts/smk37.txt"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    USES_TERMINAL VERBATIM)

# Only advertise target packaging on a supported native Linux host or an explicitly requested Docker route.
set(UMETATE_TARGETS_AVAILABLE OFF)
if(CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux" AND CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$")
    set(UMETATE_TARGETS_AVAILABLE ON)
elseif(JIELI_DOCKER STREQUAL "1")
    set(UMETATE_TARGETS_AVAILABLE ON)
endif()

if(UMETATE_TARGETS_AVAILABLE)
    if(NOT JIELI_TOOLCHAIN)
        set(JIELI_TOOLCHAIN "/opt/jieli/toolchain")
    endif()
    if(NOT AC79_SDK)
        set(AC79_SDK "/opt/jieli/sdk")
    endif()
    if(NOT JIELI_DOCKER_IMAGE)
        set(JIELI_DOCKER_IMAGE "debian:bookworm-slim")
    endif()
    set(UMETATE_TARGET_PREREQUISITES ON)
    set(AC79_SDK_ASSETS "${AC79_SDK}/cpu/wl82/tools")
    foreach(required IN ITEMS "${JIELI_TOOLCHAIN}/pi32v2/bin/clang" "${JIELI_TOOLCHAIN}/pi32v2/bin/ld"
        "${JIELI_TOOLCHAIN}/common/bin/objcopy" "${JIELI_TOOLCHAIN}/common/bin/objdump"
        "${AC79_SDK_ASSETS}/uboot.boot" "${AC79_SDK_ASSETS}/cfg_tool.bin"
        "${AC79_SDK_ASSETS}/cfg/eq_cfg_hw.bin")
        if(NOT EXISTS "${required}")
            set(UMETATE_TARGET_PREREQUISITES OFF)
            message(STATUS "Target package blocked; missing prerequisite: ${required}")
        endif()
    endforeach()
    if(UMETATE_TARGET_PREREQUISITES AND (JIELI_DOCKER STREQUAL "1" OR NOT CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux"))
        find_program(DOCKER_EXECUTABLE docker)
        if(NOT DOCKER_EXECUTABLE)
            set(UMETATE_TARGET_PREREQUISITES OFF)
            message(STATUS "Target package blocked; Docker is unavailable")
        else()
            execute_process(COMMAND "${DOCKER_EXECUTABLE}" info RESULT_VARIABLE docker_rc OUTPUT_QUIET ERROR_QUIET)
            if(NOT docker_rc EQUAL 0)
                set(UMETATE_TARGET_PREREQUISITES OFF)
                message(STATUS "Target package blocked; Docker daemon is not running")
            endif()
        endif()
    endif()

    if(UMETATE_TARGET_PREREQUISITES)
        set(UMETATE_TARGET_ARGS --toolchain "${JIELI_TOOLCHAIN}" --sdk "${AC79_SDK}" --out "${UMETATE_ARTIFACT_DIR}"
            --board "${UMETATE_BOARD}" --model "${UMETATE_MODEL}" --profile "${UMETATE_PROFILE}"
            --sdk-assets "${AC79_SDK_ASSETS}")
        if(UMETATE_RELEASE)
            list(APPEND UMETATE_TARGET_ARGS --release "${UMETATE_RELEASE}")
        endif()
        if(UMETATE_DEFS)
            list(APPEND UMETATE_TARGET_ARGS --defs "${UMETATE_DEFS}")
        endif()
        if(JIELI_DOCKER STREQUAL "1" OR NOT CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux")
            list(APPEND UMETATE_TARGET_ARGS --docker --docker-image "${JIELI_DOCKER_IMAGE}")
        endif()
        set(_target_deps tools/cmake_target.py tools/build.py tools/fm1pkg_make.py tools/lz4blk.py
            app.ld crt0.S hal/fm1_vec.S hal/fm1_isr.S)
        file(GLOB_RECURSE _firmware_inputs CONFIGURE_DEPENDS hal/*.h src/*.c src/*.h
            loader/*.c loader/*.h loader/*.S loader/*.ld gen/*
            tools/*.py)
        list(APPEND _target_deps ${_firmware_inputs})
        list(APPEND _target_deps "${AC79_SDK_ASSETS}/uboot.boot"
            "${AC79_SDK_ASSETS}/cfg_tool.bin" "${AC79_SDK_ASSETS}/cfg/eq_cfg_hw.bin")
        set(_target_config_file "${CMAKE_BINARY_DIR}/target-build-config.txt")
        file(CONFIGURE OUTPUT "${_target_config_file}" CONTENT
            "board=${UMETATE_BOARD}\nmodel=${UMETATE_MODEL}\nprofile=${UMETATE_PROFILE}\nrelease=${UMETATE_RELEASE}\ndefs=${UMETATE_DEFS}\ntoolchain=${JIELI_TOOLCHAIN}\nsdk=${AC79_SDK}\nsdk_assets=${AC79_SDK_ASSETS}\ndocker=${JIELI_DOCKER}\ndocker_image=${JIELI_DOCKER_IMAGE}\n")
        add_custom_command(
            OUTPUT "${CMAKE_BINARY_DIR}/target.stamp"
            BYPRODUCTS "${UMETATE_ARTIFACT_DIR}/rib.bin" "${UMETATE_ARTIFACT_DIR}/rib.elf"
                "${UMETATE_ARTIFACT_DIR}/rib.map" "${UMETATE_ARTIFACT_DIR}/rib.link.map"
                "${UMETATE_ARTIFACT_DIR}/rib.dis" "${UMETATE_ARTIFACT_DIR}/symbols.txt"
                "${UMETATE_ARTIFACT_DIR}/ramtext.dis" "${UMETATE_ARTIFACT_DIR}/dsp.bin"
                "${UMETATE_ARTIFACT_DIR}/loader/ota.bin" "${UMETATE_ARTIFACT_DIR}/loader/loader.elf"
                "${UMETATE_ARTIFACT_DIR}/loader/loader.bin" "${UMETATE_ARTIFACT_DIR}/loader/loader.dis"
                "${UMETATE_ARTIFACT_DIR}/target-config.txt" "${UMETATE_ARTIFACT_DIR}/${UMETATE_PACKAGE_NAME}"
            COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/cmake_target.py" build ${UMETATE_TARGET_ARGS}
            COMMAND "${CMAKE_COMMAND}" -E touch "${CMAKE_BINARY_DIR}/target.stamp"
            DEPENDS ${_target_deps} "${_target_config_file}"
            WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
            USES_TERMINAL VERBATIM)
        add_custom_target(target_package DEPENDS "${CMAKE_BINARY_DIR}/target.stamp")
        add_custom_target(package DEPENDS target_package)
        add_custom_target(target_check
            COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tools/cmake_target.py" check ${UMETATE_TARGET_ARGS}
            DEPENDS target_package
            WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
            USES_TERMINAL VERBATIM)
    else()
        set(UMETATE_TARGETS_AVAILABLE OFF)
    endif()
endif()

if(NOT UMETATE_TARGETS_AVAILABLE)
    add_custom_target(target_package
        COMMAND "${CMAKE_COMMAND}" -E echo "Target package blocked: supported Linux x86-64/macOS Docker route, JieLi toolchain and matching AC79 SDK assets are required"
        COMMAND "${CMAKE_COMMAND}" -E false
        USES_TERMINAL)
    add_custom_target(package DEPENDS target_package)
    add_custom_target(target_check DEPENDS target_package)
    message(STATUS "Host targets enabled. Target package prerequisites are unavailable or platform-blocked.")
endif()
