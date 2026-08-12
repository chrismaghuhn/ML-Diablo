cmake_minimum_required(VERSION 3.20)
project(dxai_observation_probe LANGUAGES CXX)

set(DEVILUTIONX_SOURCE_DIR "" CACHE PATH "Pinned DevilutionX source checkout")
set(DEVILUTIONX_BINARY_DIR "" CACHE PATH "Pinned DevilutionX build directory")
set(DEVILUTIONX_SHARED_LIBRARY "" CACHE FILEPATH "libdevilutionx_so import/shared library")
set(DEVILUTIONX_CONFIG "Release" CACHE STRING "Upstream configuration used for generated headers")
set(DEVILUTIONX_DEPENDENCY_INCLUDE_DIR "${DEVILUTIONX_BINARY_DIR}/vcpkg_installed/x64-windows/include" CACHE PATH "Upstream dependency include directory")
set(DEVILUTIONX_DEPENDENCY_LIBRARY_DIR "${DEVILUTIONX_BINARY_DIR}/vcpkg_installed/x64-windows/lib" CACHE PATH "Upstream dependency library directory")

if(NOT DEVILUTIONX_SOURCE_DIR OR NOT DEVILUTIONX_BINARY_DIR OR NOT DEVILUTIONX_SHARED_LIBRARY)
  message(FATAL_ERROR "DEVILUTIONX_SOURCE_DIR, DEVILUTIONX_BINARY_DIR and DEVILUTIONX_SHARED_LIBRARY are required")
endif()

add_executable(dxai_observation_probe main.cpp)
target_compile_features(dxai_observation_probe PRIVATE cxx_std_23)
target_compile_definitions(dxai_observation_probe PRIVATE BUILD_TESTING SDL_MAIN_HANDLED)
target_include_directories(dxai_observation_probe SYSTEM PRIVATE
  "${DEVILUTIONX_SOURCE_DIR}/Source"
  "${DEVILUTIONX_BINARY_DIR}/Source"
  "${DEVILUTIONX_BINARY_DIR}/Source/${DEVILUTIONX_CONFIG}"
  "${DEVILUTIONX_BINARY_DIR}/_deps/asio-src/asio/include"
  "${DEVILUTIONX_SOURCE_DIR}/3rdParty/asio"
  "${DEVILUTIONX_BINARY_DIR}/_deps/sdl_audiolib-src/include"
  "${DEVILUTIONX_BINARY_DIR}/_deps/sdl_audiolib-src/src"
  "${DEVILUTIONX_BINARY_DIR}/_deps/sdl_audiolib-build"
  "${DEVILUTIONX_BINARY_DIR}/_deps/libzt-src/include"
  "${DEVILUTIONX_BINARY_DIR}/_deps/libzt-src/src"
  "${DEVILUTIONX_BINARY_DIR}/_deps/libzt-src/ext/lwip/src/include"
  "${DEVILUTIONX_BINARY_DIR}/_deps/libzt-src/ext/lwip-contrib/ports/win32/include"
  "${DEVILUTIONX_BINARY_DIR}/_deps/libsmackerdec-src/include"
  "${DEVILUTIONX_SOURCE_DIR}/3rdParty/tl"
  "${DEVILUTIONX_BINARY_DIR}/_deps/unordered_dense-src/include"
  "${DEVILUTIONX_BINARY_DIR}/_deps/sheenbidi-src/Headers"
  "${DEVILUTIONX_BINARY_DIR}/_deps/mpqfs-src/include"
  "${DEVILUTIONX_BINARY_DIR}/_deps/find_steam_game-src"
  "${DEVILUTIONX_DEPENDENCY_INCLUDE_DIR}"
  "${DEVILUTIONX_DEPENDENCY_INCLUDE_DIR}/SDL2"
  "${DEVILUTIONX_SOURCE_DIR}/3rdParty/sol2/sol_config"
  "${DEVILUTIONX_BINARY_DIR}/_deps/sol2-src/include"
)
target_link_libraries(dxai_observation_probe PRIVATE "${DEVILUTIONX_SHARED_LIBRARY}")
if(MSVC)
  find_library(DEVILUTIONX_SDL2_LIBRARY
    NAMES SDL2
    PATHS "${DEVILUTIONX_DEPENDENCY_LIBRARY_DIR}"
    NO_DEFAULT_PATH
    REQUIRED
  )
  target_link_libraries(dxai_observation_probe PRIVATE "${DEVILUTIONX_SDL2_LIBRARY}" bcrypt)
endif()

if(MSVC)
  target_compile_options(dxai_observation_probe PRIVATE /W4 /EHsc /permissive- /WX)
else()
  target_compile_options(dxai_observation_probe PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

set_target_properties(dxai_observation_probe PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
