cmake_minimum_required(VERSION 3.16)
project(rocket_sim_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(BUILD_PYTHON_BINDINGS "Build pybind11 Python module" ON)

add_library(rocket_sim_cpp_lib
    cpp/src/rocket_sim_cpp.cpp
    cpp/src/config_loader.cpp
)
target_include_directories(rocket_sim_cpp_lib PUBLIC cpp/include)
set_target_properties(rocket_sim_cpp_lib PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_executable(cpp_sim cpp/src/sim_main.cpp)
target_link_libraries(cpp_sim PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_validate cpp/src/validate_main.cpp)
target_link_libraries(cpp_validate PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_tests cpp/src/tests_main.cpp)
target_link_libraries(cpp_tests PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_monte_carlo cpp/src/monte_carlo_main.cpp)
target_link_libraries(cpp_monte_carlo PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_event_engine cpp/src/event_engine_main.cpp)
target_link_libraries(cpp_event_engine PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_simd_batch_rk4 cpp/src/simd_batch_rk4_main.cpp)
target_link_libraries(cpp_simd_batch_rk4 PRIVATE rocket_sim_cpp_lib)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU" AND CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|amd64|AMD64")
  target_compile_options(cpp_simd_batch_rk4 PRIVATE -mavx2 -mfma)
endif()

add_executable(rk4_reference cpp/rk4_reference.cpp)

if(BUILD_PYTHON_BINDINGS)
  if(DEFINED ENV{VIRTUAL_ENV} AND EXISTS "$ENV{VIRTUAL_ENV}/bin/python")
    set(Python3_EXECUTABLE "$ENV{VIRTUAL_ENV}/bin/python")
  endif()
  find_package(pybind11 CONFIG QUIET)
  if(NOT pybind11_FOUND)
    find_package(Python3 COMPONENTS Interpreter QUIET)
    if(Python3_Interpreter_FOUND)
      execute_process(
        COMMAND "${Python3_EXECUTABLE}" -m pybind11 --cmakedir
        OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
      )
      if(PYBIND11_CMAKE_DIR)
        list(APPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
        find_package(pybind11 CONFIG QUIET)
      endif()
    endif()
  endif()
  if(pybind11_FOUND)
    find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)
    pybind11_add_module(rocket_sim_event_bindings cpp/src/pybind_module.cpp)
    target_link_libraries(rocket_sim_event_bindings PRIVATE rocket_sim_cpp_lib)
  else()
    message(STATUS "pybind11 not found; skipping Python bindings target")
  endif()
endif()
