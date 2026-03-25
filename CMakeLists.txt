cmake_minimum_required(VERSION 3.16)
project(rocket_sim_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(rocket_sim_cpp_lib
    cpp/src/rocket_sim_cpp.cpp
    cpp/src/config_loader.cpp
)
target_include_directories(rocket_sim_cpp_lib PUBLIC cpp/include)

add_executable(cpp_sim cpp/src/sim_main.cpp)
target_link_libraries(cpp_sim PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_validate cpp/src/validate_main.cpp)
target_link_libraries(cpp_validate PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_tests cpp/src/tests_main.cpp)
target_link_libraries(cpp_tests PRIVATE rocket_sim_cpp_lib)

add_executable(cpp_monte_carlo cpp/src/monte_carlo_main.cpp)
target_link_libraries(cpp_monte_carlo PRIVATE rocket_sim_cpp_lib)

add_executable(rk4_reference cpp/rk4_reference.cpp)
