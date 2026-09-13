cmake_minimum_required(VERSION 3.20)
project(python_filament VERSION 1.0.0 LANGUAGES CXX)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

set(FILAMENT_VERSION "1.76.1" CACHE STRING "Filament SDK version")
set(FILAMENT_ROOT "" CACHE PATH "Extracted Filament SDK root")
set(FILAMENT_ARCHIVE "" CACHE FILEPATH "Path to a prebuilt Filament SDK archive")

if(NOT FILAMENT_ROOT)
  if(NOT FILAMENT_ARCHIVE AND DEFINED ENV{FILAMENT_ARCHIVE})
    set(FILAMENT_ARCHIVE "$ENV{FILAMENT_ARCHIVE}")
  endif()
  if(NOT FILAMENT_ARCHIVE)
    message(FATAL_ERROR
      "Set FILAMENT_ROOT to an extracted Filament SDK or FILAMENT_ARCHIVE to a prebuilt SDK archive. "
      "python-filament never builds Filament from source.")
  endif()
  if(NOT IS_ABSOLUTE "${FILAMENT_ARCHIVE}")
    get_filename_component(FILAMENT_ARCHIVE "${FILAMENT_ARCHIVE}" ABSOLUTE
                           BASE_DIR "${CMAKE_SOURCE_DIR}")
  endif()
  if(NOT EXISTS "${FILAMENT_ARCHIVE}")
    message(FATAL_ERROR "Filament SDK archive does not exist: ${FILAMENT_ARCHIVE}")
  endif()
  set(_filament_extract_dir "${CMAKE_BINARY_DIR}/filament-sdk")
  if(NOT EXISTS "${_filament_extract_dir}/include/filament/Engine.h" AND
     NOT EXISTS "${_filament_extract_dir}/filament/include/filament/Engine.h")
    file(MAKE_DIRECTORY "${_filament_extract_dir}")
    file(ARCHIVE_EXTRACT INPUT "${FILAMENT_ARCHIVE}" DESTINATION "${_filament_extract_dir}")
  endif()
  if(EXISTS "${_filament_extract_dir}/include/filament/Engine.h")
    set(FILAMENT_ROOT "${_filament_extract_dir}")
  elseif(EXISTS "${_filament_extract_dir}/filament/include/filament/Engine.h")
    # The official macOS SDK has a top-level filament/ directory.
    set(FILAMENT_ROOT "${_filament_extract_dir}/filament")
  else()
    message(FATAL_ERROR
      "The Filament SDK archive does not contain include/filament/Engine.h: ${FILAMENT_ARCHIVE}")
  endif()
endif()

if(APPLE AND CMAKE_OSX_ARCHITECTURES)
  list(LENGTH CMAKE_OSX_ARCHITECTURES _filament_apple_arch_count)
  if(NOT _filament_apple_arch_count EQUAL 1)
    message(FATAL_ERROR "Filament wheels require exactly one macOS architecture per build")
  endif()
  list(GET CMAKE_OSX_ARCHITECTURES 0 _filament_arch)
else()
  set(_filament_arch "${CMAKE_SYSTEM_PROCESSOR}")
endif()
if(_filament_arch MATCHES "^(AMD64|amd64|x86_64)$")
  set(_filament_arch "x86_64")
elseif(_filament_arch MATCHES "^(ARM64|arm64|aarch64)$")
  set(_filament_arch "arm64")
endif()

set(_filament_lib_candidates
  "${FILAMENT_ROOT}/lib/${_filament_arch}"
  "${FILAMENT_ROOT}/lib/${CMAKE_SYSTEM_PROCESSOR}"
  "${FILAMENT_ROOT}/lib/universal"
  "${FILAMENT_ROOT}/lib")
if(WIN32)
  list(PREPEND _filament_lib_candidates "${FILAMENT_ROOT}/lib/${_filament_arch}/md")
endif()
if(_filament_arch STREQUAL "arm64")
  list(APPEND _filament_lib_candidates "${FILAMENT_ROOT}/lib/aarch64")
endif()

unset(_filament_core_library CACHE)
find_library(_filament_core_library NAMES filament
             PATHS ${_filament_lib_candidates} NO_DEFAULT_PATH)
if(NOT _filament_core_library)
  message(FATAL_ERROR
    "Could not find the Filament runtime library for ${CMAKE_SYSTEM_NAME}/${CMAKE_SYSTEM_PROCESSOR} "
    "under ${FILAMENT_ROOT}/lib")
endif()
get_filename_component(_filament_libdir "${_filament_core_library}" DIRECTORY)
message(STATUS "Using Filament libraries from: ${_filament_libdir}")

pybind11_add_module(_native MODULE cpp/bindings.cpp)
target_compile_features(_native PRIVATE cxx_std_20)
target_compile_definitions(_native PRIVATE PYTHON_FILAMENT_VERSION="${PROJECT_VERSION}")
target_include_directories(_native PRIVATE "${FILAMENT_ROOT}/include")
target_link_directories(_native PRIVATE "${_filament_libdir}")
target_link_libraries(_native PRIVATE filament backend bluegl bluevk filabridge filaflat utils smol-v zstd)
if(WIN32)
  target_link_libraries(_native PRIVATE opengl32)
endif()
if(UNIX AND NOT APPLE)
  target_link_libraries(_native PRIVATE dl pthread)
endif()
if(APPLE)
  target_link_libraries(_native PRIVATE
    "-framework Cocoa" "-framework Metal" "-framework QuartzCore" "-framework CoreVideo")
endif()
install(TARGETS _native LIBRARY DESTINATION filament RUNTIME DESTINATION filament)
install(FILES "${FILAMENT_ROOT}/LICENSE" DESTINATION filament/licenses
        RENAME FILAMENT-LICENSE.txt)
