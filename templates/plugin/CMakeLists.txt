cmake_minimum_required(VERSION 3.22)
project(@P1_PLUGIN_TARGET@_plugin LANGUAGES C CXX)

# The reusable plugin host. plugin-generate wrote this path.
set(P1_PLUGIN_SOURCE "@P1_PLUGIN_SOURCE@")

enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/P1Project.cmake")
add_subdirectory("${P1_PLUGIN_SOURCE}" p1plugin)
