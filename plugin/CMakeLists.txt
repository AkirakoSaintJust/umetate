cmake_minimum_required(VERSION 3.22)
project(p1onken_plugin_host VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(APPLE)
    enable_language(OBJCXX)
endif()

option(P1_BUILD_JUCE "Build the JUCE VST3 and standalone host" OFF)

set(UMETATE_FIRMWARE "${CMAKE_CURRENT_SOURCE_DIR}/../firmware" CACHE PATH "firmware root")
set(UMETATE_SYNTH_GEN "${UMETATE_FIRMWARE}/gen" CACHE PATH "generated synth directory")

if(MSVC)
    set(UMETATE_STATE_PTR "__declspec(thread)")
else()
    set(UMETATE_STATE_PTR "_Thread_local")
endif()

enable_testing()

add_library(p1_engine STATIC
    engine/Engine.cpp
    engine/MidiBridge.cpp
    engine/RateBridge.cpp
    ${UMETATE_SYNTH_GEN}/type_p_fm1_dsp.c
    ${UMETATE_SYNTH_GEN}/tables.c
    ${UMETATE_FIRMWARE}/src/synth_midi.c
)
set_target_properties(p1_engine PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_include_directories(p1_engine PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/engine
    ${UMETATE_SYNTH_GEN}
    ${UMETATE_FIRMWARE}/hal
    ${UMETATE_FIRMWARE}/src
)

target_compile_definitions(p1_engine PRIVATE
    UMETATE_MIDI_EXTERNAL
    "UMETATE_STATE_PTR=${UMETATE_STATE_PTR}"
)

add_executable(engine_parity tests/engine_parity.cpp)
target_link_libraries(engine_parity PRIVATE p1_engine)
add_test(NAME engine_parity COMMAND engine_parity)

if(P1_BUILD_JUCE)
    add_subdirectory(juce)
endif()
