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
set(P1_TOKENS_HEADER "${P1_GENERATED_DIR}/UiTokens.h")

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

add_custom_command(
    OUTPUT "${P1_TOKENS_HEADER}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${P1_GENERATED_DIR}"
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/../tools/gen_tokens.py"
            "${CMAKE_CURRENT_SOURCE_DIR}/../../design/tokens.json" "${P1_TOKENS_HEADER}"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../../design/tokens.json"
            "${CMAKE_CURRENT_SOURCE_DIR}/../tools/gen_tokens.py"
    VERBATIM
)
add_custom_target(p1_tokens DEPENDS "${P1_TOKENS_HEADER}")

juce_add_binary_data(p1_resources SOURCES
    resources/fonts/DotGothic16-Regular.ttf
    resources/fonts/ZenDots-Regular.ttf
)

set(P1_JUCE_DEFINITIONS
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_JACK=0
    JUCE_VST3_CAN_REPLACE_VST2=0
)

set(P1_UI_SOURCES
    PluginEditor.cpp
    Pages.cpp
    PagesOperators.cpp
    PagesFxMod.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../ui/Theme.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../ui/Widgets.cpp
)

add_library(p1_editor STATIC ${P1_UI_SOURCES})
set_target_properties(p1_editor PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(p1_editor PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/../ui"
    "${P1_GENERATED_DIR}"
    "${CMAKE_CURRENT_BINARY_DIR}"
)
target_link_libraries(p1_editor PUBLIC
    p1_engine
    p1_resources
    juce::juce_audio_utils
    juce::juce_dsp
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
target_compile_definitions(p1_editor PUBLIC ${P1_JUCE_DEFINITIONS})
add_dependencies(p1_editor p1_params p1_tokens)

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
target_link_libraries(type_p_fm1 PRIVATE
    p1_editor
    juce::juce_audio_utils
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
target_compile_definitions(type_p_fm1 PRIVATE ${P1_JUCE_DEFINITIONS})
add_dependencies(type_p_fm1 p1_params p1_tokens)

juce_add_console_app(p1_smoke PRODUCT_NAME "p1_smoke")
target_sources(p1_smoke PRIVATE PluginProcessor.cpp ../tests/plugin_smoke.cpp)
target_link_libraries(p1_smoke PRIVATE
    p1_editor
    juce::juce_audio_utils
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
target_compile_definitions(p1_smoke PRIVATE ${P1_JUCE_DEFINITIONS})
add_dependencies(p1_smoke p1_params p1_tokens)
add_test(NAME plugin_smoke COMMAND p1_smoke)

juce_add_console_app(p1_editor_snapshot PRODUCT_NAME "p1_editor_snapshot")
target_sources(p1_editor_snapshot PRIVATE PluginProcessor.cpp
                                        ../tests/editor_snapshot.cpp)
target_link_libraries(p1_editor_snapshot PRIVATE
    p1_editor
    juce::juce_audio_utils
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
)
target_compile_definitions(p1_editor_snapshot PRIVATE ${P1_JUCE_DEFINITIONS})
add_dependencies(p1_editor_snapshot p1_params p1_tokens)

find_program(XVFB_RUN xvfb-run)
if(XVFB_RUN)
    add_test(NAME plugin_editor_snapshot
             COMMAND ${XVFB_RUN} -a "$<TARGET_FILE:p1_editor_snapshot>"
                     "${CMAKE_CURRENT_BINARY_DIR}/snapshots")
else()
    add_test(NAME plugin_editor_snapshot
             COMMAND "$<TARGET_FILE:p1_editor_snapshot>"
                     "${CMAKE_CURRENT_BINARY_DIR}/snapshots")
endif()
