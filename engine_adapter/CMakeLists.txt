cmake_minimum_required(VERSION 3.20)
project(dxai_bridge_contract LANGUAGES CXX)

add_library(dxai_bridge_contract STATIC src/validation.cpp)
target_include_directories(dxai_bridge_contract PUBLIC include)
target_compile_features(dxai_bridge_contract PUBLIC cxx_std_20)
set_target_properties(dxai_bridge_contract PROPERTIES CXX_EXTENSIONS OFF)

if(MSVC)
  target_compile_options(dxai_bridge_contract PRIVATE /W4 /permissive- /WX)
else()
  target_compile_options(dxai_bridge_contract PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

enable_testing()
add_executable(dxai_bridge_contract_test tests/contract_test.cpp)
target_link_libraries(dxai_bridge_contract_test PRIVATE dxai_bridge_contract)
add_test(NAME dxai_bridge_contract_test COMMAND dxai_bridge_contract_test)
