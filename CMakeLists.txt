cmake_minimum_required(VERSION 3.21)
project(poker LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(POKER_BUILD_TESTS "Build the GoogleTest unit test suite" ON)
option(POKER_BUILD_PYTHON_BINDINGS "Build the pybind11 module exposing the engine to Python (AI layer)" OFF)

add_subdirectory(engine)

if(POKER_BUILD_PYTHON_BINDINGS)
    add_subdirectory(bindings)
endif()
