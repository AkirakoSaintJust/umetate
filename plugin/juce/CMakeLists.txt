cmake_minimum_required(VERSION 3.22)

include(FetchContent)
FetchContent_Declare(
    JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.9
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(JUCE)

find_package(Python3 3.8 REQUIRED COMPONENTS Interpreter)

set(P1_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(P1_PARAMS_HEADER "${P1_GENERATED_DIR}/Params.h")

add_custom_command(
    OUTPUT "${P1_PARAMS_HEADER}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${P1_GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/../tools/gen_params.py"
            "${UMETATE_SYNTH_GEN}/params.json" "${P1_PARAMS_HEADER}"
    DEPENDS "${UMETATE_SYNTH_GEN}/params.json"
            "${CMAKE_CURRENT_SOURCE_DIR}/../tools/gen_params.py"
    VERBATIM
)
add_custom_target(p1_params DEPENDS "${P1_PARAMS_HEADER}")

set(P1_JUCE_DEFINITIONS
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_JACK=0
    JUCE_VST3_CAN_REPLACE_VST2=0
)

juce_add_plugin(type_p_fm1
    COMPANY_NAME "P1Onken"
    BUNDLE_ID "com.p1onken.typepfm1"
    PLUGIN_MANUFACTURER_CODE P1on
    PLUGIN_CODE Tpf1
    PRODUCT_NAME "Type P.fm1"
    FORMATS VST3 Standalone
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE
)

target_sources(type_p_fm1 PRIVATE PluginProcessor.cpp)
target_include_directories(type_p_fm1 PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${P1_GENERATED_DIR}"
)
target_link_libraries(type_p_fm1 PRIVATE
    p1_engine
    juce::juce_audio_utils
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
target_compile_definitions(type_p_fm1 PRIVATE ${P1_JUCE_DEFINITIONS})
add_dependencies(type_p_fm1 p1_params)

juce_add_console_app(p1_smoke PRODUCT_NAME "p1_smoke")
target_sources(p1_smoke PRIVATE PluginProcessor.cpp ../tests/plugin_smoke.cpp)
target_include_directories(p1_smoke PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${P1_GENERATED_DIR}"
)
target_link_libraries(p1_smoke PRIVATE
    p1_engine
    juce::juce_audio_utils
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
target_compile_definitions(p1_smoke PRIVATE ${P1_JUCE_DEFINITIONS})
add_dependencies(p1_smoke p1_params)
add_test(NAME plugin_smoke COMMAND p1_smoke)
